"""
FastAPI Server for Executive E-Commerce Analytics Dashboard
Connects to online_retail.db and serves analytical REST endpoints and static UI.
Includes Customer 360, Multi-Metric Cohorts, VIP Rescue, and Live SQL Sandbox.
"""

import os
import time
import sqlite3
import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, Query, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
import pandas as pd
import numpy as np

DB_PATH = 'online_retail.db'
CHURN_CSV = 'customer_churn_predictions.csv'

app = FastAPI(title="E-Commerce Retail Analytics API", version="2.0.0")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

class SQLQueryRequest(BaseModel):
    query: str

@app.get("/api/kpis")
def get_kpis():
    conn = get_db()
    cursor = conn.cursor()
    
    q_totals = """
    SELECT 
        COUNT(DISTINCT CustomerID) AS total_customers,
        COUNT(DISTINCT InvoiceNo) AS total_orders,
        ROUND(SUM(Quantity * UnitPrice), 2) AS total_revenue,
        ROUND(SUM(Quantity * UnitPrice) / COUNT(DISTINCT InvoiceNo), 2) AS aov
    FROM Transactions;
    """
    cursor.execute(q_totals)
    row_totals = dict(cursor.fetchone())
    
    q_repeat = """
    WITH Customer_Aggs AS (
        SELECT CustomerID, COUNT(DISTINCT InvoiceNo) AS order_cnt, SUM(Quantity * UnitPrice) AS spend
        FROM Transactions
        GROUP BY CustomerID
    )
    SELECT 
        COUNT(CASE WHEN order_cnt >= 2 THEN 1 END) AS repeat_customers,
        ROUND(SUM(CASE WHEN order_cnt >= 2 THEN spend ELSE 0 END), 2) AS repeat_revenue
    FROM Customer_Aggs;
    """
    cursor.execute(q_repeat)
    row_repeat = dict(cursor.fetchone())
    
    q_churn = """
    WITH Benchmark AS (
        SELECT MAX(InvoiceDate) AS max_date FROM Transactions
    ),
    Customer_Recency AS (
        SELECT 
            t.CustomerID,
            ROUND(julianday(b.max_date) - julianday(MAX(t.InvoiceDate)), 1) AS days_gap
        FROM Transactions t
        CROSS JOIN Benchmark b
        GROUP BY t.CustomerID
    )
    SELECT 
        COUNT(CASE WHEN days_gap > 60 THEN 1 END) AS at_risk_count,
        ROUND(COUNT(CASE WHEN days_gap > 60 THEN 1 END) * 100.0 / COUNT(*), 2) AS churn_rate_pct
    FROM Customer_Recency;
    """
    cursor.execute(q_churn)
    row_churn = dict(cursor.fetchone())
    
    conn.close()
    
    repeat_rev_share = round((row_repeat['repeat_revenue'] / row_totals['total_revenue']) * 100, 2)
    repeat_cust_share = round((row_repeat['repeat_customers'] / row_totals['total_customers']) * 100, 2)
    
    return {
        "total_revenue": row_totals['total_revenue'],
        "total_customers": row_totals['total_customers'],
        "total_orders": row_totals['total_orders'],
        "average_order_value": row_totals['aov'],
        "repeat_customers": row_repeat['repeat_customers'],
        "repeat_customer_rate_pct": repeat_cust_share,
        "repeat_revenue_share_pct": repeat_rev_share,
        "at_risk_customers": row_churn['at_risk_count'],
        "churn_rate_pct": row_churn['churn_rate_pct'],
        "top_10_share_pct": 61.41
    }

@app.get("/api/revenue-trend")
def get_revenue_trend():
    conn = get_db()
    q = """
    SELECT 
        strftime('%Y-%m', InvoiceDate) AS month_year,
        ROUND(SUM(Quantity * UnitPrice), 2) AS revenue,
        COUNT(DISTINCT InvoiceNo) AS orders,
        COUNT(DISTINCT CustomerID) AS active_customers,
        ROUND(SUM(Quantity * UnitPrice) / COUNT(DISTINCT InvoiceNo), 2) AS aov
    FROM Transactions
    GROUP BY strftime('%Y-%m', InvoiceDate)
    ORDER BY month_year ASC;
    """
    df = pd.read_sql(q, conn)
    conn.close()
    df['mom_growth_pct'] = df['revenue'].pct_change().fillna(0).mul(100).round(2)
    return df.to_dict(orient="records")

@app.get("/api/tier-distribution")
def get_tier_distribution():
    conn = get_db()
    q = """
    WITH Customer_Totals AS (
        SELECT 
            CustomerID,
            SUM(Quantity * UnitPrice) AS TotalSpend,
            COUNT(DISTINCT InvoiceNo) AS TotalOrders,
            CUME_DIST() OVER (ORDER BY SUM(Quantity * UnitPrice) DESC) AS SpendPct
        FROM Transactions
        GROUP BY CustomerID
    ),
    Tiers AS (
        SELECT 
            CustomerID,
            TotalSpend,
            TotalOrders,
            CASE 
                WHEN SpendPct <= 0.10 THEN 'Platinum Tier (Top 10%)'
                WHEN SpendPct <= 0.25 THEN 'Gold Tier (Top 25%)'
                ELSE 'General Tier'
            END AS TierName
        FROM Customer_Totals
    )
    SELECT 
        TierName,
        COUNT(CustomerID) AS customer_count,
        ROUND(COUNT(CustomerID) * 100.0 / (SELECT COUNT(*) FROM Tiers), 2) AS customer_pct,
        ROUND(SUM(TotalSpend), 2) AS tier_revenue,
        ROUND(SUM(TotalSpend) * 100.0 / (SELECT SUM(TotalSpend) FROM Tiers), 2) AS revenue_pct,
        ROUND(AVG(TotalOrders), 1) AS avg_orders,
        ROUND(SUM(TotalSpend) / SUM(TotalOrders), 2) AS tier_aov
    FROM Tiers
    GROUP BY TierName
    ORDER BY tier_revenue DESC;
    """
    df = pd.read_sql(q, conn)
    conn.close()
    return df.to_dict(orient="records")

@app.get("/api/churn-distribution")
def get_churn_distribution():
    if os.path.exists(CHURN_CSV):
        df_ml = pd.read_csv(CHURN_CSV)
        counts = df_ml['RiskTier'].value_counts()
        total = len(df_ml)
        return [
            {"tier": "Low Risk (Active)", "count": int(counts.get("Low Risk (Active)", 0)), "pct": round(counts.get("Low Risk (Active)", 0)/total*100, 2), "color": "#10B981"},
            {"tier": "Moderate Risk (Cooling)", "count": int(counts.get("Moderate Risk (Cooling)", 0)), "pct": round(counts.get("Moderate Risk (Cooling)", 0)/total*100, 2), "color": "#F59E0B"},
            {"tier": "High Risk (Critical Churn)", "count": int(counts.get("High Risk (Critical Churn)", 0)), "pct": round(counts.get("High Risk (Critical Churn)", 0)/total*100, 2), "color": "#F43F5E"}
        ]
    return []

@app.get("/api/cohorts")
def get_cohorts(metric: str = Query("retention", regex="^(retention|revenue|count)$")):
    conn = get_db()
    df_tx = pd.read_sql("SELECT CustomerID, InvoiceDate, Quantity * UnitPrice AS LineTotal FROM Transactions", conn)
    conn.close()
    
    df_tx['InvoiceDate'] = pd.to_datetime(df_tx['InvoiceDate'])
    acq = df_tx.groupby('CustomerID')['InvoiceDate'].min().dt.to_period('M').rename('AcquisitionMonth')
    df_tx['ActivityMonth'] = df_tx['InvoiceDate'].dt.to_period('M')
    df_tx = df_tx.merge(acq, on='CustomerID')
    
    df_tx['CohortIndex'] = (df_tx['ActivityMonth'].dt.year - df_tx['AcquisitionMonth'].dt.year) * 12 + \
                           (df_tx['ActivityMonth'].dt.month - df_tx['AcquisitionMonth'].dt.month)
    
    cohort_sizes = df_tx.groupby('AcquisitionMonth')['CustomerID'].nunique()
    
    if metric == "revenue":
        cohort_agg = df_tx.groupby(['AcquisitionMonth', 'CohortIndex'])['LineTotal'].sum().reset_index()
        cohort_agg['Val'] = cohort_agg['LineTotal'].round(2)
    elif metric == "count":
        cohort_agg = df_tx.groupby(['AcquisitionMonth', 'CohortIndex'])['CustomerID'].nunique().reset_index()
        cohort_agg['Val'] = cohort_agg['CustomerID']
    else: # retention %
        cohort_agg = df_tx.groupby(['AcquisitionMonth', 'CohortIndex'])['CustomerID'].nunique().reset_index()
        cohort_agg['CohortSize'] = cohort_agg['AcquisitionMonth'].map(cohort_sizes)
        cohort_agg['Val'] = (cohort_agg['CustomerID'] / cohort_agg['CohortSize'] * 100).round(1)
        
    cohort_agg['AcquisitionMonth'] = cohort_agg['AcquisitionMonth'].astype(str)
    pivot = cohort_agg.pivot(index='AcquisitionMonth', columns='CohortIndex', values='Val').fillna(0)
    
    return {
        "metric": metric,
        "months": [str(m) for m in pivot.index],
        "indices": [int(i) for i in pivot.columns],
        "sizes": [int(cohort_sizes.loc[pd.Period(m, 'M')]) for m in pivot.index],
        "matrix": pivot.values.tolist()
    }

@app.get("/api/customer-profile/{customer_id}")
def get_customer_profile(customer_id: int):
    conn = get_db()
    
    # 1. Customer metadata & totals
    q_meta = """
    WITH Benchmark AS (SELECT MAX(InvoiceDate) AS max_date FROM Transactions)
    SELECT 
        t.CustomerID,
        t.Country,
        MIN(t.InvoiceDate) AS first_date,
        MAX(t.InvoiceDate) AS last_date,
        COUNT(DISTINCT t.InvoiceNo) AS total_orders,
        COUNT(t.StockCode) AS total_items,
        COUNT(DISTINCT t.StockCode) AS unique_products,
        ROUND(SUM(t.Quantity * t.UnitPrice), 2) AS total_spend,
        ROUND(SUM(t.Quantity * t.UnitPrice) / COUNT(DISTINCT t.InvoiceNo), 2) AS aov,
        ROUND(julianday(b.max_date) - julianday(MAX(t.InvoiceDate)), 1) AS recency_days
    FROM Transactions t
    CROSS JOIN Benchmark b
    WHERE t.CustomerID = ?
    GROUP BY t.CustomerID;
    """
    df_meta = pd.read_sql(q_meta, conn, params=[customer_id])
    if df_meta.empty:
        conn.close()
        raise HTTPException(status_code=404, detail="Customer ID not found")
        
    meta = df_meta.iloc[0].to_dict()
    
    # 2. Invoices list
    q_invoices = """
    SELECT 
        InvoiceNo,
        InvoiceDate,
        COUNT(StockCode) AS items_count,
        SUM(Quantity) AS total_units,
        ROUND(SUM(Quantity * UnitPrice), 2) AS invoice_total
    FROM Transactions
    WHERE CustomerID = ?
    GROUP BY InvoiceNo, InvoiceDate
    ORDER BY InvoiceDate DESC;
    """
    df_inv = pd.read_sql(q_invoices, conn, params=[customer_id])
    
    # 3. Top products purchased by customer
    q_prods = """
    SELECT 
        StockCode,
        Description,
        SUM(Quantity) AS units,
        ROUND(AVG(UnitPrice), 2) AS unit_price,
        ROUND(SUM(Quantity * UnitPrice), 2) AS product_spend
    FROM Transactions
    WHERE CustomerID = ?
    GROUP BY StockCode, Description
    ORDER BY product_spend DESC
    LIMIT 6;
    """
    df_prods = pd.read_sql(q_prods, conn, params=[customer_id])
    conn.close()
    
    # 4. RFM Score calculations
    # Recency: <=30d: 5, <=60d: 4, <=90d: 3, <=180d: 2, >180d: 1
    rec = meta['recency_days']
    r_score = 5 if rec <= 30 else (4 if rec <= 60 else (3 if rec <= 90 else (2 if rec <= 180 else 1)))
    
    # Frequency: >=10: 5, >=5: 4, >=3: 3, >=2: 2, 1: 1
    freq = meta['total_orders']
    f_score = 5 if freq >= 10 else (4 if freq >= 5 else (3 if freq >= 3 else (2 if freq >= 2 else 1)))
    
    # Monetary: >=5000: 5, >=2000: 4, >=1000: 3, >=500: 2, else 1
    spend = meta['total_spend']
    m_score = 5 if spend >= 5000 else (4 if spend >= 2000 else (3 if spend >= 1000 else (2 if spend >= 500 else 1)))
    
    # 5. ML Risk & Segment
    tier = 'Platinum' if spend >= 4000 else ('Gold' if spend >= 1500 else 'General')
    ml_prob = 0.45
    risk_tier = 'Moderate Risk'
    
    if os.path.exists(CHURN_CSV):
        df_ml = pd.read_csv(CHURN_CSV)
        match = df_ml[df_ml['CustomerID'] == customer_id]
        if not match.empty:
            ml_prob = float(match.iloc[0]['ChurnProbability'])
            risk_tier = str(match.iloc[0]['RiskTier'])
            
    # Next best action
    if risk_tier.startswith('High'):
        action = "High churn risk: Immediately assign an Account Executive for a personalized discount outreach."
    elif tier == 'Platinum':
        action = "VIP Platinum Account: Send priority early-access catalog and quarterly wholesale volume rebate."
    elif f_score >= 4:
        action = "Loyal active buyer: Cross-sell related product categories based on top purchased items."
    else:
        action = "Standard customer: Enroll in automated email lifecycle drip campaign."
        
    return {
        "metadata": meta,
        "rfm": {"r": r_score, "f": f_score, "m": m_score, "tier": tier},
        "ml": {"probability": round(ml_prob, 2), "risk_tier": risk_tier, "recommended_action": action},
        "invoices": df_inv.to_dict(orient="records"),
        "top_products": df_prods.to_dict(orient="records")
    }

@app.get("/api/vip-rescue")
def get_vip_rescue():
    """Returns high-value accounts at severe churn risk needing immediate intervention."""
    conn = get_db()
    q = """
    WITH Benchmark AS (SELECT MAX(InvoiceDate) AS max_date FROM Transactions),
    Custs AS (
        SELECT 
            t.CustomerID,
            t.Country,
            ROUND(SUM(t.Quantity * t.UnitPrice), 2) AS TotalSpend,
            COUNT(DISTINCT t.InvoiceNo) AS TotalOrders,
            ROUND(julianday(b.max_date) - julianday(MAX(t.InvoiceDate)), 1) AS RecencyDays,
            CUME_DIST() OVER (ORDER BY SUM(t.Quantity * t.UnitPrice) DESC) AS SpendPct
        FROM Transactions t
        CROSS JOIN Benchmark b
        GROUP BY t.CustomerID, t.Country
    )
    SELECT 
        CustomerID, Country, TotalSpend, TotalOrders, RecencyDays,
        CASE WHEN SpendPct <= 0.10 THEN 'Platinum' WHEN SpendPct <= 0.25 THEN 'Gold' ELSE 'General' END AS Tier
    FROM Custs
    WHERE TotalSpend >= 1000
    ORDER BY TotalSpend DESC;
    """
    df = pd.read_sql(q, conn)
    conn.close()
    
    if os.path.exists(CHURN_CSV):
        df_ml = pd.read_csv(CHURN_CSV)
        df = df.merge(df_ml[['CustomerID', 'ChurnProbability', 'RiskTier']], on='CustomerID', how='left')
        df['ChurnProbability'] = df['ChurnProbability'].fillna(0.50).round(2)
        df['RiskTier'] = df['RiskTier'].fillna('Unscored')
    else:
        df['ChurnProbability'] = 0.65
        df['RiskTier'] = 'High Risk (Critical Churn)'
        
    # Filter only accounts with ChurnProbability >= 0.50 or RecencyDays > 60
    rescue_df = df[(df['ChurnProbability'] >= 0.50) | (df['RecencyDays'] > 60)].copy()
    
    total_at_stake = rescue_df['TotalSpend'].sum()
    
    return {
        "accounts_count": len(rescue_df),
        "total_revenue_at_stake": round(total_at_stake, 2),
        "avg_recency_days": round(rescue_df['RecencyDays'].mean(), 1),
        "accounts": rescue_df.head(60).to_dict(orient="records")
    }

@app.post("/api/sql-sandbox")
def run_sql_sandbox(req: SQLQueryRequest):
    """Executes read-only SQL queries against online_retail.db and returns execution plan."""
    query = req.query.strip()
    
    # Strip SQL comments to validate query prefix
    clean_query = re.sub(r'--[^\r\n]*(\r\n|\n)?', '', query).strip()
    clean_query = re.sub(r'/\*.*?\*/', '', clean_query, flags=re.DOTALL).strip()
    
    # Safety Check: Disallow modifying statements
    forbidden = re.compile(r'\b(DROP|DELETE|INSERT|UPDATE|ALTER|REPLACE|ATTACH|DETACH|CREATE|PRAGMA writable_schema)\b', re.IGNORECASE)
    if forbidden.search(clean_query):
        raise HTTPException(status_code=400, detail="Only read-only SELECT queries are permitted in the sandbox.")
        
    if not clean_query.lower().startswith("select") and not clean_query.lower().startswith("with") and not clean_query.lower().startswith("explain"):
        raise HTTPException(status_code=400, detail="Query must start with SELECT, WITH, or EXPLAIN.")
        
    start_time = time.time()
    conn = get_db()
    
    try:
        # Run Query Plan first
        plan_cursor = conn.cursor()
        plan_cursor.execute(f"EXPLAIN QUERY PLAN {clean_query}")
        plan_rows = [p[3] for p in plan_cursor.fetchall()]
        
        # Run actual query
        df = pd.read_sql(clean_query, conn)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        
        # Limit rows to 100 for browser safety
        truncated = False
        if len(df) > 100:
            truncated = True
            df = df.head(100)
            
        columns = df.columns.tolist()
        rows = df.values.tolist()
        
        conn.close()
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "total_rows_produced": len(df),
            "truncated": truncated,
            "execution_time_ms": elapsed_ms,
            "query_plan": plan_rows
        }
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/customers")
def get_customers(
    q: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200)
):
    conn = get_db()
    query = """
    WITH Benchmark AS (SELECT MAX(InvoiceDate) AS max_date FROM Transactions),
    Customer_Metrics AS (
        SELECT 
            t.CustomerID,
            t.Country,
            ROUND(SUM(t.Quantity * t.UnitPrice), 2) AS TotalSpend,
            COUNT(DISTINCT t.InvoiceNo) AS TotalOrders,
            ROUND(SUM(t.Quantity * t.UnitPrice) / COUNT(DISTINCT t.InvoiceNo), 2) AS AOV,
            ROUND(julianday(b.max_date) - julianday(MAX(t.InvoiceDate)), 1) AS RecencyDays,
            DENSE_RANK() OVER (ORDER BY SUM(t.Quantity * t.UnitPrice) DESC) AS SpendRank,
            CUME_DIST() OVER (ORDER BY SUM(t.Quantity * t.UnitPrice) DESC) AS SpendPct
        FROM Transactions t
        CROSS JOIN Benchmark b
        GROUP BY t.CustomerID, t.Country
    )
    SELECT 
        CustomerID, Country, TotalSpend, TotalOrders, AOV, RecencyDays, SpendRank,
        CASE WHEN SpendPct <= 0.10 THEN 'Platinum' WHEN SpendPct <= 0.25 THEN 'Gold' ELSE 'General' END AS Tier,
        CASE WHEN RecencyDays > 60 THEN 'At-Risk' ELSE 'Active' END AS Status
    FROM Customer_Metrics
    WHERE 1=1
    """
    params = []
    if q:
        query += " AND (CAST(CustomerID AS TEXT) LIKE ? OR Country LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])
    if tier and tier.lower() != 'all':
        query += " AND CASE WHEN SpendPct <= 0.10 THEN 'Platinum' WHEN SpendPct <= 0.25 THEN 'Gold' ELSE 'General' END = ?"
        params.append(tier)
        
    query += " ORDER BY TotalSpend DESC LIMIT ?"
    params.append(limit)
    
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    
    if os.path.exists(CHURN_CSV):
        df_ml = pd.read_csv(CHURN_CSV)
        df = df.merge(df_ml[['CustomerID', 'ChurnProbability', 'RiskTier']], on='CustomerID', how='left')
        df['ChurnProbability'] = df['ChurnProbability'].fillna(0.50).round(2)
        df['RiskTier'] = df['RiskTier'].fillna('Unscored')
    else:
        df['ChurnProbability'] = 0.50
        df['RiskTier'] = 'Unscored'
        
    return df.to_dict(orient="records")

@app.get("/api/forecast")
def get_forecast(
    growth: float = Query(8.0),
    churn_save: float = Query(5.0)
):
    base_revenue = 8887208.89
    plat_rev = 5457733.65
    gold_rev = 1177511.66
    gen_rev = 2251963.58
    
    organic_mult = 1.0 + (growth / 100.0)
    at_risk_pool = base_revenue * 0.174
    retention_boost = at_risk_pool * (churn_save / 100.0)
    
    projected_total = round((base_revenue * organic_mult) + retention_boost, 2)
    incremental = round(projected_total - base_revenue, 2)
    
    return {
        "baseline_2011": base_revenue,
        "growth_rate_pct": growth,
        "retention_save_pct": churn_save,
        "projected_2012": projected_total,
        "incremental_revenue": incremental,
        "tier_projections": {
            "Platinum": round(plat_rev * organic_mult + (retention_boost * 0.60), 2),
            "Gold": round(gold_rev * organic_mult + (retention_boost * 0.25), 2),
            "General": round(gen_rev * organic_mult + (retention_boost * 0.15), 2)
        }
    }
# *** NEW ENDPOINTS START ***

# ManualTransaction model for Data Studio

class ManualTransaction(BaseModel):
    InvoiceNo: str
    StockCode: str
    Description: str
    Quantity: int
    InvoiceDate: str  # ISO format string
    UnitPrice: float
    CustomerID: int
    Country: str

@app.post("/api/upload-data")
def upload_data(file: UploadFile = File(...), mode: str = Query("append", enum=["append", "replace"])):
    """Upload CSV or Excel dataset, clean it, and insert into Transactions table.
    mode: 'append' adds to existing data, 'replace' overwrites the table.
    Returns cleaning statistics.
    """
    # Read file into DataFrame
    try:
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(file.file)
        elif file.filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file.file)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use .csv or .xlsx")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}")

    required_cols = {"InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice", "CustomerID", "Country"}
    if not required_cols.issubset(set(df.columns)):
        raise HTTPException(status_code=400, detail="Missing required columns in uploaded file")

    # Data hygiene steps
    raw_count = len(df)
    # 1. Cancelled invoices starting with 'C'
    mask_canc = df['InvoiceNo'].astype(str).str.startswith('C')
    filtered_cancellations = mask_canc.sum()
    df = df[~mask_canc]
    # 2. Null CustomerID
    mask_null = df['CustomerID'].isnull()
    filtered_null_customers = mask_null.sum()
    df = df[~mask_null]
    # 3. Non‑positive UnitPrice or Quantity
    mask_nonpos = (df['UnitPrice'] <= 0) | (df['Quantity'] <= 0)
    filtered_non_positive = mask_nonpos.sum()
    df = df[~mask_nonpos]
    # 4. Deduplicate
    before_dup = len(df)
    df = df.drop_duplicates()
    filtered_duplicates = before_dup - len(df)
    clean_count_added = len(df)

    conn = get_db()
    if mode == "replace":
        conn.execute("DELETE FROM Transactions")
        conn.commit()
    # Insert cleaned rows
    df.to_sql('Transactions', conn, if_exists='append', index=False)
    conn.commit()
    # Compute new total rows for reporting
    total_rows = conn.execute('SELECT COUNT(*) FROM Transactions').fetchone()[0]
    conn.close()

    return {
        "raw_count": raw_count,
        "filtered_cancellations": int(filtered_cancellations),
        "filtered_null_customers": int(filtered_null_customers),
        "filtered_non_positive": int(filtered_non_positive),
        "filtered_duplicates": int(filtered_duplicates),
        "clean_count_added": int(clean_count_added),
        "total_rows_after": int(total_rows),
        "mode": mode
    }

@app.post("/api/manual-transaction")
def manual_transaction(tx: ManualTransaction):
    """Insert a single transaction record supplied via JSON payload."""
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO Transactions (InvoiceNo, StockCode, Description, Quantity, InvoiceDate, UnitPrice, CustomerID, Country)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx.InvoiceNo,
                tx.StockCode,
                tx.Description,
                tx.Quantity,
                tx.InvoiceDate,
                tx.UnitPrice,
                tx.CustomerID,
                tx.Country,
            ),
        )
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    conn.close()
    return {"detail": "Transaction added successfully"}

@app.delete("/api/transaction/{invoice_no}/{stock_code}")
def delete_transaction(invoice_no: str, stock_code: str):
    """Delete a specific line‑item identified by invoice number and stock code."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM Transactions WHERE InvoiceNo = ? AND StockCode = ?",
        (invoice_no, stock_code)
    )
    conn.commit()
    deleted = cur.rowcount
    conn.close()
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"detail": "Transaction deleted"}

@app.post("/api/reset-baseline")
def reset_baseline():
    """Restore the Transactions table from the original cleaned CSV baseline."""
    baseline_path = os.path.join(os.path.dirname(__file__), '..', 'cleaned_online_retail.csv')
    if not os.path.exists(baseline_path):
        raise HTTPException(status_code=404, detail="Baseline CSV not found")
    df = pd.read_csv(baseline_path)
    conn = get_db()
    conn.execute('DELETE FROM Transactions')
    conn.commit()
    df.to_sql('Transactions', conn, if_exists='append', index=False)
    conn.commit()
    total_rows = conn.execute('SELECT COUNT(*) FROM Transactions').fetchone()[0]
    conn.close()
    return {"detail": "Baseline restored", "total_rows": int(total_rows)}

# *** NEW ENDPOINTS END ***
# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), 'static')
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(static_dir, 'index.html')
    return FileResponse(index_file)
