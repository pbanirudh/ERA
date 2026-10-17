"""
Load Real Kaggle / UCI Online Retail Dataset
Downloads the official Online Retail dataset from UCI Machine Learning Repository,
saves raw_online_retail.csv, executes the 4-step cleaning pipeline,
saves cleaned_online_retail.csv, and loads into indexed SQLite table 'Transactions'.
"""

import os
import sys
import time
import ssl
import zipfile
import urllib.request
import sqlite3
import pandas as pd
import numpy as np

UCI_ZIP_URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"
ZIP_FILE = "online_retail_uci.zip"
EXCEL_FILE = "Online Retail.xlsx"
RAW_CSV = "raw_online_retail.csv"
CLEANED_CSV = "cleaned_online_retail.csv"
DB_PATH = "online_retail.db"
TABLE_NAME = "Transactions"

def download_uci_dataset():
    """Download the official dataset zip from UCI if not already present."""
    if os.path.exists(EXCEL_FILE):
        print(f"Found existing {EXCEL_FILE}, skipping download.")
        return
        
    print(f"Downloading official dataset from {UCI_ZIP_URL}...")
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(UCI_ZIP_URL, headers={'User-Agent': 'Mozilla/5.0'})
    
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp, open(ZIP_FILE, 'wb') as out_f:
        data = resp.read()
        out_f.write(data)
    print(f"Downloaded {len(data):,} bytes to {ZIP_FILE}.")
    
    print(f"Extracting {ZIP_FILE}...")
    with zipfile.ZipFile(ZIP_FILE, 'r') as z:
        z.extractall('.')
    print(f"Extracted {EXCEL_FILE}.")
    
    # Clean up zip
    if os.path.exists(ZIP_FILE):
        os.remove(ZIP_FILE)


def process_dataset():
    start_time = time.time()
    download_uci_dataset()
    
    print(f"\nReading {EXCEL_FILE} with pandas (this may take 20-30 seconds for ~541k rows)...")
    read_start = time.time()
    raw_df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
    print(f"Loaded {len(raw_df):,} raw rows in {time.time() - read_start:.2f}s.")
    
    # Standardize column types
    raw_df['InvoiceNo'] = raw_df['InvoiceNo'].astype(str).str.strip()
    raw_df['StockCode'] = raw_df['StockCode'].astype(str).str.strip()
    raw_df['Description'] = raw_df['Description'].astype(str).str.strip()
    raw_df['InvoiceDate'] = pd.to_datetime(raw_df['InvoiceDate']).dt.strftime('%Y-%m-%d %H:%M:%S')
    raw_df['Country'] = raw_df['Country'].astype(str).str.strip()
    
    # Save raw CSV
    print(f"\nExporting raw dataset to {RAW_CSV}...")
    raw_df.to_csv(RAW_CSV, index=False)
    raw_size_mb = os.path.getsize(RAW_CSV) / (1024 * 1024)
    print(f"Raw CSV exported: {RAW_CSV} ({raw_size_mb:.2f} MB, {len(raw_df):,} rows)")
    
    # Execute Cleaning Pipeline
    print("\n" + "="*70)
    print("EXECUTING MULTI-STEP DATA CLEANING PIPELINE ON REAL DATASET")
    print("="*70)
    
    initial_count = len(raw_df)
    current_df = raw_df.copy()
    metrics = []
    
    # Step 1: Remove cancellations (InvoiceNo starting with 'C' or Quantity < 0)
    step1_mask = current_df['InvoiceNo'].str.startswith('C') | (current_df['Quantity'] < 0)
    cancellations_count = int(step1_mask.sum())
    current_df = current_df[~step1_mask].copy()
    count_after_step1 = len(current_df)
    metrics.append({
        'Step': '1. Remove Cancellations (InvoiceNo like "C%" or Quantity < 0)',
        'Rows Before': initial_count,
        'Rows Removed': cancellations_count,
        'Rows Remaining': count_after_step1,
        'Pct of Raw Removed': (cancellations_count / initial_count) * 100
    })
    print(f"Step 1 Complete: Removed {cancellations_count:,} cancellations. Remaining: {count_after_step1:,}")
    
    # Step 2: Remove rows with null CustomerID
    step2_mask = current_df['CustomerID'].isna() | (current_df['CustomerID'].astype(str).str.lower().isin(['nan', 'none', 'null', '']))
    null_cust_count = int(step2_mask.sum())
    current_df = current_df[~step2_mask].copy()
    count_after_step2 = len(current_df)
    metrics.append({
        'Step': '2. Remove Missing CustomerID (Null/Guest checkouts)',
        'Rows Before': count_after_step1,
        'Rows Removed': null_cust_count,
        'Rows Remaining': count_after_step2,
        'Pct of Raw Removed': (null_cust_count / initial_count) * 100
    })
    print(f"Step 2 Complete: Removed {null_cust_count:,} rows with null CustomerID. Remaining: {count_after_step2:,}")
    
    # Step 3: Remove rows with UnitPrice <= 0
    step3_mask = current_df['UnitPrice'] <= 0
    bad_price_count = int(step3_mask.sum())
    current_df = current_df[~step3_mask].copy()
    count_after_step3 = len(current_df)
    metrics.append({
        'Step': '3. Remove Non-Positive UnitPrice (UnitPrice <= 0.00)',
        'Rows Before': count_after_step2,
        'Rows Removed': bad_price_count,
        'Rows Remaining': count_after_step3,
        'Pct of Raw Removed': (bad_price_count / initial_count) * 100
    })
    print(f"Step 3 Complete: Removed {bad_price_count:,} rows with UnitPrice <= 0. Remaining: {count_after_step3:,}")
    
    # Step 4: Remove exact duplicate rows
    dupes_mask = current_df.duplicated()
    dupes_count = int(dupes_mask.sum())
    current_df = current_df.drop_duplicates().copy()
    final_count = len(current_df)
    metrics.append({
        'Step': '4. Remove Exact Duplicate Rows',
        'Rows Before': count_after_step3,
        'Rows Removed': dupes_count,
        'Rows Remaining': final_count,
        'Pct of Raw Removed': (dupes_count / initial_count) * 100
    })
    print(f"Step 4 Complete: Removed {dupes_count:,} duplicate rows. Final Clean Rows: {final_count:,}")
    
    # Format CustomerID as integer
    current_df['CustomerID'] = current_df['CustomerID'].astype(int)
    
    total_removed = initial_count - final_count
    print("\n" + "="*85)
    print("BEFORE / AFTER DATA CLEANING SUMMARY (REAL DATASET)")
    print("="*85)
    print(f"{'Cleaning Step':<55} | {'Removed':>10} | {'Remaining':>12}")
    print("-" * 85)
    for m in metrics:
        print(f"{m['Step']:<55} | {m['Rows Removed']:>10,} | {m['Rows Remaining']:>12,}")
    print("-" * 85)
    print(f"{'TOTAL ROWS FILTERED':<55} | {total_removed:>10,} | {final_count:>12,}")
    print(f"Overall Retention Rate: {(final_count / initial_count)*100:.2f}% | Total Removed: {(total_removed / initial_count)*100:.2f}%\n")
    
    # Export cleaned CSV
    print(f"Exporting cleaned dataset to {CLEANED_CSV}...")
    current_df.to_csv(CLEANED_CSV, index=False)
    clean_size_mb = os.path.getsize(CLEANED_CSV) / (1024 * 1024)
    print(f"Cleaned CSV exported: {CLEANED_CSV} ({clean_size_mb:.2f} MB, {len(current_df):,} rows)")
    
    # Load into SQLite database
    print("\n" + "="*70)
    print(f"INGESTING CLEANED DATA INTO SQLITE: {DB_PATH} -> Table: [{TABLE_NAME}]")
    print("="*70)
    
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(f"""
    CREATE TABLE {TABLE_NAME} (
        InvoiceNo TEXT NOT NULL,
        StockCode TEXT NOT NULL,
        Description TEXT NOT NULL,
        Quantity INTEGER NOT NULL,
        InvoiceDate TEXT NOT NULL,
        UnitPrice REAL NOT NULL,
        CustomerID INTEGER NOT NULL,
        Country TEXT NOT NULL
    );
    """)
    conn.commit()
    
    print(f"Inserting {len(current_df):,} rows into [{TABLE_NAME}]...")
    current_df[['InvoiceNo', 'StockCode', 'Description', 'Quantity',
                'InvoiceDate', 'UnitPrice', 'CustomerID', 'Country']].to_sql(
        name=TABLE_NAME,
        con=conn,
        if_exists='append',
        index=False,
        chunksize=50000
    )
    print(f"Successfully loaded all {len(current_df):,} rows into [{TABLE_NAME}].")
    
    # Create Indexes
    print("\nCreating performance indexes...")
    index_statements = [
        f"CREATE INDEX idx_transactions_customer_id ON {TABLE_NAME}(CustomerID);",
        f"CREATE INDEX idx_transactions_invoice_date ON {TABLE_NAME}(InvoiceDate);",
        f"CREATE INDEX idx_transactions_invoice_no ON {TABLE_NAME}(InvoiceNo);"
    ]
    for stmt in index_statements:
        print(f"  Executing: {stmt}")
        cursor.execute(stmt)
    conn.commit()
    
    # Verify index query plans
    print("\nValidating SQLite Index Query Plans (EXPLAIN QUERY PLAN):")
    sample_queries = [
        f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE CustomerID = 12346;",
        f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE InvoiceDate >= '2011-06-01';",
        f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE InvoiceNo = '540001';"
    ]
    for q in sample_queries:
        cursor.execute(f"EXPLAIN QUERY PLAN {q}")
        plan = cursor.fetchall()
        print(f"  Query: {q}")
        for p in plan:
            print(f"    -> Plan detail: {p[3]}")
            
    conn.close()
    
    # Analytics on Real Data
    print("\n" + "="*70)
    print("REAL DATASET CHARACTERISTICS & PARETO REVENUE ANALYSIS")
    print("="*70)
    current_df['LineTotal'] = current_df['Quantity'] * current_df['UnitPrice']
    total_rev = current_df['LineTotal'].sum()
    
    cust_stats = current_df.groupby('CustomerID').agg(
        TotalSpend=('LineTotal', 'sum'),
        OrderCount=('InvoiceNo', 'nunique')
    ).sort_values(by='TotalSpend', ascending=False).reset_index()
    
    n_cust = len(cust_stats)
    top_10_count = int(n_cust * 0.10)
    top_10_rev = cust_stats.iloc[:top_10_count]['TotalSpend'].sum()
    top_10_pct = (top_10_rev / total_rev) * 100
    
    top_20_count = int(n_cust * 0.20)
    top_20_rev = cust_stats.iloc[:top_20_count]['TotalSpend'].sum()
    top_20_pct = (top_20_rev / total_rev) * 100
    
    repeat_custs = cust_stats[cust_stats['OrderCount'] >= 2]
    repeat_rev = repeat_custs['TotalSpend'].sum()
    repeat_share = (repeat_rev / total_rev) * 100
    
    print(f"Unique Clean Customers: {n_cust:,}")
    print(f"Total Revenue Generated: GBP {total_rev:,.2f}")
    print(f"Top 10% Customers ({top_10_count:,} accounts): GBP {top_10_rev:,.2f} ({top_10_pct:.2f}% of total revenue)")
    print(f"Top 20% Customers ({top_20_count:,} accounts): GBP {top_20_rev:,.2f} ({top_20_pct:.2f}% of total revenue)")
    print(f"Repeat Customers (>= 2 orders): {len(repeat_custs):,} accounts ({len(repeat_custs)/n_cust*100:.2f}%)")
    print(f"Revenue driven by Repeat Customers: GBP {repeat_rev:,.2f} ({repeat_share:.2f}% of total revenue)")
    
    uk_rows = (current_df['Country'] == 'United Kingdom').sum()
    print(f"\nCountry Breakdown:")
    print(f"  United Kingdom: {uk_rows:,} ({uk_rows/len(current_df)*100:.2f}%)")
    print(f"  Other Countries: {len(current_df)-uk_rows:,} ({(len(current_df)-uk_rows)/len(current_df)*100:.2f}%)")
    print(f"Date Range: {current_df['InvoiceDate'].min()} to {current_df['InvoiceDate'].max()}")
    
    print(f"\nDatabase file: {os.path.abspath(DB_PATH)} ({os.path.getsize(DB_PATH)/(1024*1024):.2f} MB)")
    print(f"Processing finished in {time.time() - start_time:.2f}s!")

if __name__ == '__main__':
    process_dataset()
