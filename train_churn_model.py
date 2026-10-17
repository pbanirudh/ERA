"""
Machine Learning Customer Churn & Repurchase Prediction Model
Dataset: online_retail.db (Transactions table)
Algorithm: XGBoost Classifier with Temporal Validation & Feature Engineering
"""

import os
import sqlite3
import datetime
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, average_precision_score, accuracy_score,
    precision_score, recall_score, f1_score, confusion_matrix, classification_report
)
from xgboost import XGBClassifier

DB_PATH = 'online_retail.db'
OUTPUT_CSV = 'customer_churn_predictions.csv'

def load_and_engineer_features():
    print("="*70)
    print("1. EXTRACTING TRANSACTIONS & ENGINEERING BEHAVIORAL FEATURES")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT CustomerID, InvoiceNo, StockCode, Quantity, InvoiceDate, UnitPrice, Country FROM Transactions", conn)
    conn.close()
    
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['LineTotal'] = df['Quantity'] * df['UnitPrice']
    
    # ----------------------------------------------------
    # TEMPORAL SPLIT (To strictly avoid future data leakage)
    # Observation Window: 2010-12-01 to 2011-09-30 (10 months)
    # Prediction Target Window: 2011-10-01 to 2011-12-09 (70 days)
    # ----------------------------------------------------
    CUTOFF_DATE = pd.to_datetime("2011-09-30 23:59:59")
    T30_DATE = CUTOFF_DATE - pd.Timedelta(days=30)
    T90_DATE = CUTOFF_DATE - pd.Timedelta(days=90)
    
    print(f"Dataset total records: {len(df):,}")
    print(f"Observation Cutoff Date: {CUTOFF_DATE.strftime('%Y-%m-%d')}")
    print(f"Prediction Window: Oct 01, 2011 to Dec 09, 2011")
    
    # Slice observation vs target
    obs_df = df[df['InvoiceDate'] <= CUTOFF_DATE].copy()
    pred_df = df[df['InvoiceDate'] > CUTOFF_DATE].copy()
    
    # Target definition: Did the customer return in Q4 prediction window?
    active_in_pred = set(pred_df['CustomerID'].unique())
    print(f"Unique customers active in observation window: {obs_df['CustomerID'].nunique():,}")
    print(f"Unique customers who made a purchase in prediction window: {len(active_in_pred):,}")
    
    # ----------------------------------------------------
    # Feature 1: Lifetime RFM & Basket Aggregations
    # ----------------------------------------------------
    print("Computing customer RFM & basket metrics...")
    cust_base = obs_df.groupby('CustomerID').agg(
        FirstOrder=('InvoiceDate', 'min'),
        LastOrder=('InvoiceDate', 'max'),
        TotalInvoices=('InvoiceNo', 'nunique'),
        TotalItems=('Quantity', 'sum'),
        TotalSpend=('LineTotal', 'sum'),
        UniqueProducts=('StockCode', 'nunique'),
        Country=('Country', 'first')
    ).reset_index()
    
    # Recency (days since last purchase relative to cutoff)
    cust_base['RecencyDays'] = (CUTOFF_DATE - cust_base['LastOrder']).dt.total_seconds() / 86400.0
    # Customer Tenure (days from first observed order to cutoff)
    cust_base['TenureDays'] = (CUTOFF_DATE - cust_base['FirstOrder']).dt.total_seconds() / 86400.0
    # Average Order Value (AOV)
    cust_base['AvgOrderValue'] = cust_base['TotalSpend'] / cust_base['TotalInvoices']
    # Average Items per Order
    cust_base['AvgUnitsPerOrder'] = cust_base['TotalItems'] / cust_base['TotalInvoices']
    
    # ----------------------------------------------------
    # Feature 2: Velocity & Trend Metrics (Momentum)
    # ----------------------------------------------------
    print("Computing velocity momentum (30-day vs 90-day spend ratio)...")
    # Spend in last 30 days
    s30 = obs_df[obs_df['InvoiceDate'] >= T30_DATE].groupby('CustomerID')['LineTotal'].sum().rename('SpendLast30D')
    # Spend in last 90 days
    s90 = obs_df[obs_df['InvoiceDate'] >= T90_DATE].groupby('CustomerID')['LineTotal'].sum().rename('SpendLast90D')
    
    cust_base = cust_base.merge(s30, on='CustomerID', how='left').merge(s90, on='CustomerID', how='left')
    cust_base['SpendLast30D'] = cust_base['SpendLast30D'].fillna(0)
    cust_base['SpendLast90D'] = cust_base['SpendLast90D'].fillna(0)
    
    # Momentum ratio: Spend in 30D / (Spend in 90D + 1)
    cust_base['SpendVelocityRatio'] = cust_base['SpendLast30D'] / (cust_base['SpendLast90D'] + 1.0)
    
    # ----------------------------------------------------
    # Feature 3: Inter-Purchase Timing & Cadence Regularity
    # ----------------------------------------------------
    print("Calculating order cadence regularity...")
    order_dates = obs_df[['CustomerID', 'InvoiceNo', 'InvoiceDate']].drop_duplicates().sort_values(by=['CustomerID', 'InvoiceDate'])
    order_dates['PrevDate'] = order_dates.groupby('CustomerID')['InvoiceDate'].shift(1)
    order_dates['DayGap'] = (order_dates['InvoiceDate'] - order_dates['PrevDate']).dt.total_seconds() / 86400.0
    
    cadence = order_dates.dropna(subset=['DayGap']).groupby('CustomerID')['DayGap'].agg(
        AvgCadenceDays='mean',
        StdCadenceDays='std'
    ).reset_index()
    
    cust_base = cust_base.merge(cadence, on='CustomerID', how='left')
    # For 1-time buyers, impute cadence with median tenure
    cust_base['AvgCadenceDays'] = cust_base['AvgCadenceDays'].fillna(cust_base['TenureDays'])
    cust_base['StdCadenceDays'] = cust_base['StdCadenceDays'].fillna(0.0)
    
    # ----------------------------------------------------
    # Feature 4: Categoricals & Binary Target
    # ----------------------------------------------------
    cust_base['Is_UK'] = (cust_base['Country'] == 'United Kingdom').astype(int)
    
    # Ground Truth Target: 1 if customer CHURNED (did not purchase in prediction window), 0 if RETURNING
    cust_base['Churned'] = cust_base['CustomerID'].apply(lambda cid: 0 if cid in active_in_pred else 1)
    
    print(f"Target Distribution: {cust_base['Churned'].value_counts().to_dict()} (Churn rate: {cust_base['Churned'].mean()*100:.1f}%)")
    
    return cust_base


def train_and_evaluate(data_df):
    print("\n" + "="*70)
    print("2. TRAINING XGBOOST CHURN PREDICTION MODEL")
    print("="*70)
    
    feature_cols = [
        'RecencyDays', 'TotalInvoices', 'TotalSpend', 'TotalItems',
        'UniqueProducts', 'TenureDays', 'AvgOrderValue', 'AvgUnitsPerOrder',
        'SpendLast30D', 'SpendLast90D', 'SpendVelocityRatio',
        'AvgCadenceDays', 'StdCadenceDays', 'Is_UK'
    ]
    
    X = data_df[feature_cols]
    y = data_df['Churned']
    
    # Train / Test split (80% train, 20% holdout test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    
    # Class imbalance compensation
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos = neg_count / pos_count
    
    print(f"Training on {len(X_train):,} accounts | Evaluating on {len(X_test):,} accounts")
    print(f"Class imbalance ratio (scale_pos_weight): {scale_pos:.3f}")
    
    # Initialize optimized XGBoost model
    xgb = XGBClassifier(
        n_estimators=250,
        learning_rate=0.03,
        max_depth=5,
        subsample=0.85,
        colsample_bytree=0.85,
        scale_pos_weight=scale_pos,
        eval_metric='logloss',
        random_state=42
    )
    
    xgb.fit(X_train, y_train)
    
    # Predictions
    y_pred = xgb.predict(X_test)
    y_prob = xgb.predict_proba(X_test)[:, 1]
    
    # Metrics
    auc = roc_auc_score(y_test, y_prob)
    pr_auc = average_precision_score(y_test, y_prob)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    cm = confusion_matrix(y_test, y_pred)
    
    print("\n" + "="*70)
    print("3. MODEL EVALUATION METRICS (HOLDOUT TEST SET)")
    print("="*70)
    print(f"ROC-AUC Score:             {auc:.4f}  (High discrimination power)")
    print(f"PR-AUC (Avg Precision):     {pr_auc:.4f}")
    print(f"Overall Accuracy:          {acc*100:.2f}%")
    print(f"Precision (Churn Class):   {prec*100:.2f}%")
    print(f"Recall (Churn Catch Rate): {rec*100:.2f}%")
    print(f"F1-Score:                  {f1:.4f}")
    
    print("\nConfusion Matrix:")
    print(f"  [TN={cm[0,0]:<4}  FP={cm[0,1]:<4}]  (Actual Retained)")
    print(f"  [FN={cm[1,0]:<4}  TP={cm[1,1]:<4}]  (Actual Churned)")
    
    print("\nDetailed Classification Report:\n")
    print(classification_report(y_test, y_pred, target_names=['Retained (0)', 'Churned (1)']))
    
    # ----------------------------------------------------
    # Feature Importance
    # ----------------------------------------------------
    importances = xgb.feature_importances_
    feat_imp = pd.DataFrame({
        'Feature': feature_cols,
        'Importance': importances
    }).sort_values(by='Importance', ascending=False).reset_index(drop=True)
    
    print("="*70)
    print("4. TOP PREDICTIVE DRIVERS OF CHURN (FEATURE IMPORTANCE)")
    print("="*70)
    for idx, row in feat_imp.iterrows():
        bar = "#" * int(row['Importance'] * 40)
        print(f"  {row['Feature']:<20} | {row['Importance']:.4f} | {bar}")
        
    # ----------------------------------------------------
    # Score Full Customer Base & Export Predictions
    # ----------------------------------------------------
    print("\n" + "="*70)
    print(f"5. SCORING ALL CUSTOMERS & EXPORTING TO {OUTPUT_CSV}")
    print("="*70)
    data_df['ChurnProbability'] = xgb.predict_proba(data_df[feature_cols])[:, 1]
    data_df['PredictedStatus'] = np.where(data_df['ChurnProbability'] >= 0.50, 'At-Risk Churn', 'Active / Retained')
    data_df['RiskTier'] = pd.cut(
        data_df['ChurnProbability'],
        bins=[0.0, 0.35, 0.65, 1.0],
        labels=['Low Risk (Active)', 'Moderate Risk (Cooling)', 'High Risk (Critical Churn)']
    )
    
    export_cols = [
        'CustomerID', 'Country', 'TotalSpend', 'TotalInvoices', 'RecencyDays',
        'SpendLast30D', 'AvgCadenceDays', 'ChurnProbability', 'RiskTier', 'PredictedStatus'
    ]
    data_df[export_cols].sort_values(by='ChurnProbability', ascending=False).to_csv(OUTPUT_CSV, index=False)
    print(f"Exported {len(data_df):,} customer risk scores to {OUTPUT_CSV}.")
    
    print("\nCustomer Risk Tier Breakdown:")
    print(data_df['RiskTier'].value_counts(normalize=True).mul(100).round(2).to_string())
    
    return xgb, feat_imp

def main():
    data_df = load_and_engineer_features()
    train_and_evaluate(data_df)

if __name__ == '__main__':
    main()
