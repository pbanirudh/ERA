"""
Export Optimized Star Schema Tables for Power BI
Reads from online_retail.db and customer_churn_predictions.csv,
and generates standardized dimension and fact tables in the power_bi/ folder.
"""

import os
import sqlite3
import pandas as pd
import numpy as np

DB_PATH = 'online_retail.db'
CHURN_CSV = 'customer_churn_predictions.csv'
POWER_BI_DIR = 'power_bi'

def export_star_schema():
    print("="*70)
    print("GENERATING POWER BI STAR SCHEMA DATA MODEL TABLES")
    print("="*70)
    
    os.makedirs(POWER_BI_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    # ----------------------------------------------------
    # 1. Fact_Transactions
    # ----------------------------------------------------
    print("1. Generating Fact_Transactions...")
    q_fact = """
    SELECT 
        InvoiceNo,
        StockCode,
        CustomerID,
        InvoiceDate,
        Quantity,
        UnitPrice,
        ROUND(Quantity * UnitPrice, 2) AS TotalAmount
    FROM Transactions;
    """
    df_fact = pd.read_sql(q_fact, conn)
    fact_csv = os.path.join(POWER_BI_DIR, 'Fact_Transactions.csv')
    df_fact.to_csv(fact_csv, index=False)
    print(f"  Exported {len(df_fact):,} rows to {fact_csv} ({os.path.getsize(fact_csv)/(1024*1024):.2f} MB)")
    
    # ----------------------------------------------------
    # 2. Dim_Customers (with SQL RFM + ML Churn Predictions)
    # ----------------------------------------------------
    print("\n2. Generating Dim_Customers...")
    q_cust = """
    WITH Benchmark AS (
        SELECT MAX(InvoiceDate) AS MaxDatasetDate FROM Transactions
    ),
    Customer_Aggs AS (
        SELECT 
            t.CustomerID,
            t.Country,
            MIN(t.InvoiceDate) AS FirstPurchaseDate,
            MAX(t.InvoiceDate) AS LastPurchaseDate,
            COUNT(DISTINCT t.InvoiceNo) AS LifetimeOrders,
            ROUND(SUM(t.Quantity * t.UnitPrice), 2) AS LifetimeSpend,
            ROUND(SUM(t.Quantity * t.UnitPrice) / COUNT(DISTINCT t.InvoiceNo), 2) AS CustomerAOV,
            ROUND(julianday(b.MaxDatasetDate) - julianday(MAX(t.InvoiceDate)), 1) AS DaysSinceLastPurchase
        FROM 
            Transactions t
        CROSS JOIN 
            Benchmark b
        GROUP BY 
            t.CustomerID, t.Country
    )
    SELECT 
        CustomerID,
        Country,
        FirstPurchaseDate,
        LastPurchaseDate,
        strftime('%Y-%m', FirstPurchaseDate) AS AcquisitionCohort,
        LifetimeOrders,
        LifetimeSpend,
        CustomerAOV,
        DaysSinceLastPurchase,
        DENSE_RANK() OVER (ORDER BY LifetimeSpend DESC) AS CustomerRank,
        ROUND(CUME_DIST() OVER (ORDER BY LifetimeSpend DESC), 4) AS SpendPercentile,
        CASE 
            WHEN CUME_DIST() OVER (ORDER BY LifetimeSpend DESC) <= 0.10 THEN 'Platinum Tier (Top 10%)'
            WHEN CUME_DIST() OVER (ORDER BY LifetimeSpend DESC) <= 0.25 THEN 'Gold Tier (Top 25%)'
            ELSE 'General Tier'
        END AS CustomerSegment,
        CASE 
            WHEN DaysSinceLastPurchase > 60 THEN 'At-Risk Churn'
            ELSE 'Active'
        END AS ChurnRiskStatus
    FROM 
        Customer_Aggs
    ORDER BY 
        LifetimeSpend DESC;
    """
    df_cust = pd.read_sql(q_cust, conn)
    
    # Merge ML Churn predictions if available
    if os.path.exists(CHURN_CSV):
        print("  Merging ML XGBoost Churn Risk Scores...")
        df_ml = pd.read_csv(CHURN_CSV)
        df_cust = df_cust.merge(
            df_ml[['CustomerID', 'ChurnProbability', 'RiskTier']],
            on='CustomerID',
            how='left'
        )
        df_cust['ChurnProbability'] = df_cust['ChurnProbability'].fillna(0.50).round(4)
        df_cust['RiskTier'] = df_cust['RiskTier'].fillna('Unscored')
        
    cust_csv = os.path.join(POWER_BI_DIR, 'Dim_Customers.csv')
    df_cust.to_csv(cust_csv, index=False)
    print(f"  Exported {len(df_cust):,} rows to {cust_csv} ({os.path.getsize(cust_csv)/(1024*1024):.2f} MB)")
    
    # ----------------------------------------------------
    # 3. Dim_Products
    # ----------------------------------------------------
    print("\n3. Generating Dim_Products...")
    q_prod = """
    SELECT 
        StockCode,
        Description,
        COUNT(DISTINCT InvoiceNo) AS OrderAppearances,
        SUM(Quantity) AS TotalUnitsSold,
        ROUND(AVG(UnitPrice), 2) AS AvgUnitPrice,
        ROUND(SUM(Quantity * UnitPrice), 2) AS TotalProductRevenue
    FROM 
        Transactions
    GROUP BY 
        StockCode
    ORDER BY 
        TotalProductRevenue DESC;
    """
    df_prod = pd.read_sql(q_prod, conn)
    prod_csv = os.path.join(POWER_BI_DIR, 'Dim_Products.csv')
    df_prod.to_csv(prod_csv, index=False)
    print(f"  Exported {len(df_prod):,} rows to {prod_csv} ({os.path.getsize(prod_csv)/(1024*1024):.2f} MB)")
    
    # ----------------------------------------------------
    # 4. Dim_Calendar (Date Dimension)
    # ----------------------------------------------------
    print("\n4. Generating Dim_Calendar...")
    min_date = pd.to_datetime('2010-12-01')
    max_date = pd.to_datetime('2011-12-31')
    dates = pd.date_range(min_date, max_date, freq='D')
    
    df_calendar = pd.DataFrame({'Date': dates})
    df_calendar['DateKey'] = df_calendar['Date'].dt.strftime('%Y%m%d').astype(int)
    df_calendar['Year'] = df_calendar['Date'].dt.year
    df_calendar['Quarter'] = 'Q' + df_calendar['Date'].dt.quarter.astype(str)
    df_calendar['QuarterYear'] = df_calendar['Year'].astype(str) + ' ' + df_calendar['Quarter']
    df_calendar['Month'] = df_calendar['Date'].dt.month
    df_calendar['MonthName'] = df_calendar['Date'].dt.strftime('%B')
    df_calendar['MonthShort'] = df_calendar['Date'].dt.strftime('%b')
    df_calendar['MonthYear'] = df_calendar['Date'].dt.strftime('%Y-%m')
    df_calendar['DayOfMonth'] = df_calendar['Date'].dt.day
    df_calendar['DayOfWeek'] = df_calendar['Date'].dt.day_name()
    df_calendar['DayOfWeekNum'] = df_calendar['Date'].dt.dayofweek + 1
    df_calendar['IsWeekend'] = df_calendar['DayOfWeekNum'].isin([6, 7]).astype(int)
    
    cal_csv = os.path.join(POWER_BI_DIR, 'Dim_Calendar.csv')
    df_calendar.to_csv(cal_csv, index=False)
    print(f"  Exported {len(df_calendar):,} date rows to {cal_csv}")
    
    # ----------------------------------------------------
    # 5. Dim_Cohorts (Cohort Retention Matrix Table)
    # ----------------------------------------------------
    print("\n5. Generating Dim_Cohorts...")
    df_tx = pd.read_sql("SELECT CustomerID, InvoiceDate, Quantity * UnitPrice AS LineTotal FROM Transactions", conn)
    conn.close()
    
    df_tx['InvoiceDate'] = pd.to_datetime(df_tx['InvoiceDate'])
    acq = df_tx.groupby('CustomerID')['InvoiceDate'].min().dt.to_period('M').rename('AcquisitionMonth')
    df_tx['ActivityMonth'] = df_tx['InvoiceDate'].dt.to_period('M')
    df_tx = df_tx.merge(acq, on='CustomerID')
    
    df_tx['CohortIndex'] = (df_tx['ActivityMonth'].dt.year - df_tx['AcquisitionMonth'].dt.year) * 12 + \
                           (df_tx['ActivityMonth'].dt.month - df_tx['AcquisitionMonth'].dt.month)
    
    cohort_sizes = df_tx.groupby('AcquisitionMonth')['CustomerID'].nunique().rename('CohortSize')
    cohort_agg = df_tx.groupby(['AcquisitionMonth', 'CohortIndex']).agg(
        RetainedCustomers=('CustomerID', 'nunique'),
        CohortRevenue=('LineTotal', 'sum')
    ).reset_index()
    
    cohort_agg = cohort_agg.merge(cohort_sizes, on='AcquisitionMonth')
    cohort_agg['RetentionRatePct'] = (cohort_agg['RetainedCustomers'] / cohort_agg['CohortSize'] * 100).round(2)
    cohort_agg['CohortRevenue'] = cohort_agg['CohortRevenue'].round(2)
    cohort_agg['AcquisitionMonth'] = cohort_agg['AcquisitionMonth'].astype(str)
    
    cohort_csv = os.path.join(POWER_BI_DIR, 'Dim_Cohorts.csv')
    cohort_agg.to_csv(cohort_csv, index=False)
    print(f"  Exported {len(cohort_agg):,} cohort rows to {cohort_csv}")
    
    print("\n" + "="*70)
    print("STAR SCHEMA EXPORT COMPLETED SUCCESSFULLY!")
    print("="*70)

if __name__ == '__main__':
    export_star_schema()
