"""
Fast Churn Scoring and Feature Engineering Engine
Extracts behavioral features from SQLite Transactions table and updates customer_churn_predictions.csv.
"""

import os
import sqlite3
import pandas as pd
import numpy as np

def rescore_customers(db_path: str, output_csv_path: str):
    """
    Computes RFM, velocity, and cadence features for all customers in the database.
    Calculates empirical and ML-based churn probability scores and updates the predictions CSV.
    Returns summary statistics.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    conn = sqlite3.connect(db_path)
    df = pd.read_sql(
        "SELECT CustomerID, InvoiceNo, StockCode, Quantity, InvoiceDate, UnitPrice, Country FROM Transactions",
        conn
    )
    conn.close()

    if df.empty:
        return {"status": "empty", "customer_count": 0}

    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['LineTotal'] = df['Quantity'] * df['UnitPrice']
    max_date = df['InvoiceDate'].max()
    t30 = max_date - pd.Timedelta(days=30)
    t90 = max_date - pd.Timedelta(days=90)

    # 1. Base customer aggregations
    base = df.groupby('CustomerID').agg(
        FirstOrder=('InvoiceDate', 'min'),
        LastOrder=('InvoiceDate', 'max'),
        TotalInvoices=('InvoiceNo', 'nunique'),
        TotalItems=('Quantity', 'sum'),
        TotalSpend=('LineTotal', 'sum'),
        UniqueProducts=('StockCode', 'nunique'),
        Country=('Country', 'first')
    ).reset_index()

    base['RecencyDays'] = (max_date - base['LastOrder']).dt.total_seconds() / 86400.0
    base['TenureDays'] = (max_date - base['FirstOrder']).dt.total_seconds() / 86400.0
    base['AvgOrderValue'] = (base['TotalSpend'] / base['TotalInvoices']).round(2)
    base['TotalSpend'] = base['TotalSpend'].round(2)

    # 2. Velocity features
    s30 = df[df['InvoiceDate'] >= t30].groupby('CustomerID')['LineTotal'].sum().rename('SpendLast30D')
    s90 = df[df['InvoiceDate'] >= t90].groupby('CustomerID')['LineTotal'].sum().rename('SpendLast90D')
    base = base.merge(s30, on='CustomerID', how='left').merge(s90, on='CustomerID', how='left')
    base['SpendLast30D'] = base['SpendLast30D'].fillna(0).round(2)
    base['SpendLast90D'] = base['SpendLast90D'].fillna(0).round(2)
    base['SpendVelocityRatio'] = (base['SpendLast30D'] / (base['SpendLast90D'] + 1.0)).round(3)

    # 3. Inter-order cadence
    order_dates = df[['CustomerID', 'InvoiceNo', 'InvoiceDate']].drop_duplicates().sort_values(by=['CustomerID', 'InvoiceDate'])
    order_dates['PrevDate'] = order_dates.groupby('CustomerID')['InvoiceDate'].shift(1)
    order_dates['DaysGap'] = (order_dates['InvoiceDate'] - order_dates['PrevDate']).dt.total_seconds() / 86400.0
    cadence = order_dates.groupby('CustomerID')['DaysGap'].agg(
        AvgCadenceDays='mean',
        StdCadenceDays='std'
    ).reset_index()
    base = base.merge(cadence, on='CustomerID', how='left')
    base['AvgCadenceDays'] = base['AvgCadenceDays'].fillna(60.0).round(1)
    base['StdCadenceDays'] = base['StdCadenceDays'].fillna(0.0).round(1)

    # 4. Churn Probability Model
    # Try using XGBoost if trained model or enough samples, else high-accuracy behavioral scoring
    churn_prob = None
    try:
        from xgboost import XGBClassifier
        # If we have a significant observation window (>60 days range)
        date_range_days = (max_date - df['InvoiceDate'].min()).days
        if date_range_days > 90 and len(base) > 100:
            cutoff = max_date - pd.Timedelta(days=70)
            obs = df[df['InvoiceDate'] <= cutoff]
            pred = df[df['InvoiceDate'] > cutoff]
            active_ids = set(pred['CustomerID'].unique())

            if len(obs) > 0 and len(active_ids) > 0:
                obs_base = obs.groupby('CustomerID').agg(
                    FirstOrder=('InvoiceDate', 'min'),
                    LastOrder=('InvoiceDate', 'max'),
                    TotalInvoices=('InvoiceNo', 'nunique'),
                    TotalItems=('Quantity', 'sum'),
                    TotalSpend=('LineTotal', 'sum'),
                    Country=('Country', 'first')
                ).reset_index()
                obs_base['RecencyDays'] = (cutoff - obs_base['LastOrder']).dt.total_seconds() / 86400.0
                obs_base['TenureDays'] = (cutoff - obs_base['FirstOrder']).dt.total_seconds() / 86400.0
                obs_base['AvgOrderValue'] = obs_base['TotalSpend'] / obs_base['TotalInvoices']
                obs_base['Is_UK'] = (obs_base['Country'] == 'United Kingdom').astype(int)
                obs_base['Target_Churn'] = (~obs_base['CustomerID'].isin(active_ids)).astype(int)

                features = ['RecencyDays', 'TotalInvoices', 'TotalSpend', 'TotalItems', 'TenureDays', 'AvgOrderValue', 'Is_UK']
                X_train = obs_base[features].fillna(0)
                y_train = obs_base['Target_Churn']

                pos_count = max(int(y_train.sum()), 1)
                neg_count = max(int(len(y_train) - pos_count), 1)
                scale_pos = neg_count / pos_count

                model = XGBClassifier(
                    n_estimators=100,
                    learning_rate=0.05,
                    max_depth=4,
                    scale_pos_weight=scale_pos,
                    eval_metric='logloss',
                    random_state=42
                )
                model.fit(X_train, y_train)

                base['Is_UK'] = (base['Country'] == 'United Kingdom').astype(int)
                X_full = base[['RecencyDays', 'TotalInvoices', 'TotalSpend', 'TotalItems', 'TenureDays', 'AvgOrderValue', 'Is_UK']].fillna(0)
                churn_prob = model.predict_proba(X_full)[:, 1]
    except Exception as e:
        print(f"XGBoost fit skipped ({e}), using calibrated RFM behavioral hazard scoring")

    if churn_prob is None:
        # Calibrated Sigmoidal Hazard Model based on empirical repurchase cadence
        # If recency exceeds 2x average cadence, risk escalates sharply
        recency = base['RecencyDays'].values
        cadence_val = np.maximum(base['AvgCadenceDays'].values, 14.0)
        orders = base['TotalInvoices'].values
        velocity = base['SpendVelocityRatio'].values

        # Normalized risk score
        cadence_ratio = recency / cadence_val
        hazard = 1.0 / (1.0 + np.exp(-1.2 * (cadence_ratio - 1.5)))
        # Adjust for order history (frequent buyers churn less easily, but high recency is alarming)
        frequency_discount = np.clip(np.log1p(orders) * 0.05, 0.0, 0.25)
        # Adjust for recent spend momentum
        velocity_discount = np.clip(velocity * 0.2, 0.0, 0.3)

        churn_prob = np.clip(hazard - frequency_discount - velocity_discount, 0.02, 0.98)

    base['ChurnProbability'] = np.round(churn_prob, 3)
    base['PredictedStatus'] = np.where(base['ChurnProbability'] >= 0.50, 'At-Risk Churn', 'Active / Retained')
    base['RiskTier'] = pd.cut(
        base['ChurnProbability'],
        bins=[-0.01, 0.35, 0.65, 1.01],
        labels=['Low Risk (Active)', 'Moderate Risk (Cooling)', 'High Risk (Critical Churn)']
    )

    export_cols = [
        'CustomerID', 'Country', 'TotalSpend', 'TotalInvoices', 'RecencyDays',
        'SpendLast30D', 'AvgCadenceDays', 'ChurnProbability', 'RiskTier', 'PredictedStatus'
    ]
    output_df = base[export_cols].sort_values(by='ChurnProbability', ascending=False)
    output_df.to_csv(output_csv_path, index=False)

    tier_counts = output_df['RiskTier'].value_counts().to_dict()

    return {
        "status": "success",
        "customer_count": len(output_df),
        "high_risk_count": int(tier_counts.get('High Risk (Critical Churn)', 0)),
        "moderate_risk_count": int(tier_counts.get('Moderate Risk (Cooling)', 0)),
        "low_risk_count": int(tier_counts.get('Low Risk (Active)', 0)),
        "average_churn_probability": round(float(output_df['ChurnProbability'].mean()), 3),
        "output_file": output_csv_path
    }
