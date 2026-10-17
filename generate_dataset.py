"""
Synthetic E-Commerce Transaction Dataset Generator & SQL Pipeline
Mirrors the UCI/Kaggle Online Retail Dataset (Dec 2010 - Dec 2011)
"""

import os
import sys
import time
import sqlite3
import random
import datetime
import numpy as np
import pandas as pd
from faker import Faker

# Fix random seeds for reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker('en_GB')
Faker.seed(SEED)

def generate_product_catalog(n_products=3200):
    """
    Generate realistic giftware and homeware product catalog.
    Mirrors UCI Online Retail item descriptions and 5-digit alphanumeric stock codes.
    """
    print(f"Generating product catalog ({n_products} items)...")
    
    adjectives = [
        "VINTAGE", "RETRO", "ANTIQUE", "CLASSIC", "VICTORIAN", "REGENCY",
        "HEART", "WHITE", "RED", "BLUE", "PINK", "GREEN", "CREAM", "BLACK",
        "JUMBO", "MINI", "SMALL", "LARGE", "DELUXE", "CHARLOTTE", "FRENCH",
        "RUSTIC", "LUXURY", "WOODEN", "CERAMIC", "ENAMEL", "METAL", "GLASS",
        "POLKADOT", "STRIPED", "FLORAL", "HANGING", "EMBOSSED", "DECORATIVE"
    ]
    
    nouns = [
        "T-LIGHT HOLDER", "CAKESTAND 3 TIER", "CAKE TINS SET", "LUNCH BAG",
        "COFFEE MUG", "TEA TOWEL", "BUNTING", "CUSHION COVER", "PHOTO FRAME",
        "WALL CLOCK", "TRINKET BOX", "DOORMAT", "WATER BOTTLE", "SCENTED CANDLE",
        "NOTEBOOK", "STORAGE JAR", "WALL ART", "BIRD ORNAMENT", "COASTER SET",
        "KEY RING", "APRON", "TIN BOX", "VASE", "MIRROR", "SERVING BOWL",
        "POPCORN HOLDER", "NIGHT LIGHT", "DRAWER KNOB", "JEWELLERY BOX", "WASH BAG"
    ]
    
    themes = [
        "RED RETROSPOT", "PANTRY DESIGN", "SUKI DESIGN", "FAIRY CAKE",
        "VINTAGE UNION JACK", "WOODLAND", "GARDEN PATH", "SWEETHEART",
        "IVORY EMBOSSED", "BLUE CHINTZ", "PEACE WOODEN", "LOVE HEART"
    ]
    
    products = []
    stock_code_set = set()
    
    # Predefined famous UCI products
    uci_anchors = [
        ('85123A', 'WHITE HANGING HEART T-LIGHT HOLDER', 2.55),
        ('22423', 'REGENCY CAKESTAND 3 TIER', 12.75),
        ('84879', 'ASSORTED COLOUR BIRD ORNAMENT', 1.69),
        ('47566', 'PARTY BUNTING', 4.95),
        ('22720', 'SET OF 3 CAKE TINS PANTRY DESIGN', 4.95),
        ('20725', 'LUNCH BAG RED RETROSPOT', 1.65),
        ('23084', 'RABBIT NIGHT LIGHT', 2.08),
        ('22197', 'POPCORN HOLDER', 0.85),
        ('22383', 'LUNCH BAG SUKI DESIGN', 1.65),
        ('85099B', 'JUMBO BAG RED RETROSPOT', 2.08),
        ('22960', 'JAM MAKING SET WITH JARS', 4.25),
        ('21212', 'PACK OF 72 RETROSPOT CAKE CASES', 0.55),
        ('22666', 'RECIPE BOX PANTRY DESIGN', 2.95),
        ('84997D', 'CHILDRENS CUTLERY POLKADOT PINK', 4.15),
        ('21931', 'JUMBO STORAGE BAG SUKI', 1.95),
    ]
    
    for code, desc, price in uci_anchors:
        products.append({'StockCode': code, 'Description': desc, 'BaseUnitPrice': price})
        stock_code_set.add(code)
        
    while len(products) < n_products:
        # Stock code format: 5 digit integer, optionally with letter suffix ('A'-'F')
        base_num = random.randint(10000, 99999)
        suffix = random.choice(['', '', '', '', 'A', 'B', 'C', 'D', 'E'])
        code = f"{base_num}{suffix}"
        if code in stock_code_set:
            continue
        stock_code_set.add(code)
        
        # Build description
        style = random.choice(adjectives)
        noun = random.choice(nouns)
        theme = random.choice(themes) if random.random() < 0.45 else ""
        
        if theme:
            desc = f"{style} {noun} {theme}".strip()
        else:
            desc = f"{style} {noun}".strip()
            
        # Log-normal price distribution: median ~ £2.50, range £0.35 to £45.00
        raw_price = np.random.lognormal(mean=1.0, sigma=0.85)
        price = round(max(0.35, min(raw_price, 45.00)), 2)
        
        products.append({'StockCode': code, 'Description': desc, 'BaseUnitPrice': price})
        
    df_catalog = pd.DataFrame(products)
    return df_catalog


def build_country_distribution():
    """
    Returns country names and probabilities mirroring UCI Online Retail.
    ~90% UK, with remainder spread across ~18 countries.
    """
    countries = [
        'United Kingdom', 'Germany', 'France', 'EIRE', 'Spain',
        'Netherlands', 'Belgium', 'Switzerland', 'Portugal', 'Australia',
        'Norway', 'Italy', 'Channel Islands', 'Finland', 'Cyprus',
        'Sweden', 'Austria', 'Denmark', 'Japan', 'Poland'
    ]
    weights = [
        0.895, 0.023, 0.021, 0.018, 0.007,
        0.006, 0.005, 0.004, 0.004, 0.003,
        0.003, 0.002, 0.002, 0.0015, 0.0015,
        0.001, 0.001, 0.001, 0.001, 0.001
    ]
    # Normalize weights to sum exactly to 1.0
    weights = np.array(weights) / np.sum(weights)
    return countries, weights


def generate_customer_profiles(n_registered_customers=5000):
    """
    Generate realistic customer profiles modeling customer lifetime value,
    purchase frequencies, spend propensity (Pareto principle), and acquisition timing.
    """
    print(f"Generating {n_registered_customers} customer profiles with skewed spending...")
    countries, country_weights = build_country_distribution()
    
    customer_ids = [12000 + i for i in range(n_registered_customers)]
    assigned_countries = np.random.choice(countries, size=n_registered_customers, p=country_weights)
    
    # Segment customers into tiers to model realistic Pareto spend distribution:
    # Tier 1 (Wholesale/B2B): ~4.5% of customers, high frequency (22-50 orders), 20-42 items per basket
    # Tier 2 (Loyal Frequent Retail): ~16% of customers, moderate frequency (10-22 orders), 12-28 items per basket
    # Tier 3 (Regular Shoppers): ~32% of customers, (5-10 orders), 8-18 items per basket
    # Tier 4 (One-off / Casual): ~47.5% of customers, (1-4 orders), 4-10 items per basket
    
    tier_probs = [0.045, 0.160, 0.320, 0.475]
    tiers = np.random.choice([1, 2, 3, 4], size=n_registered_customers, p=tier_probs)
    
    profiles = []
    # Retail timeline: 2010-12-01 to 2011-12-09 (373 days)
    start_epoch = datetime.datetime(2010, 12, 1, 8, 0, 0)
    
    for cid, country, tier in zip(customer_ids, assigned_countries, tiers):
        if tier == 1:
            acq_day_offset = random.randint(0, 30)
            order_count = random.randint(22, 50)
            items_per_basket_range = (20, 42)
            qty_multiplier = (12, 96)
        elif tier == 2:
            acq_day_offset = random.randint(0, 150)
            order_count = random.randint(10, 22)
            items_per_basket_range = (12, 28)
            qty_multiplier = (4, 24)
        elif tier == 3:
            acq_day_offset = random.randint(0, 260)
            order_count = random.randint(5, 10)
            items_per_basket_range = (8, 18)
            qty_multiplier = (1, 10)
        else: # tier 4
            acq_day_offset = random.randint(0, 360)
            order_count = random.choice([1, 2, 2, 3, 4])
            items_per_basket_range = (4, 10)
            qty_multiplier = (1, 4)
            
        first_date = start_epoch + datetime.timedelta(days=acq_day_offset, hours=random.randint(0, 10))
        
        profiles.append({
            'CustomerID': cid,
            'Country': country,
            'Tier': tier,
            'FirstOrderDate': first_date,
            'TargetOrders': order_count,
            'BasketSizeRange': items_per_basket_range,
            'QtyRange': qty_multiplier
        })
        
    return profiles


def generate_synthetic_transactions(target_rows=505000):
    """
    Generate ~505,000 synthetic transaction rows with:
    - Multi-item baskets (InvoiceNo)
    - Realistic customer repurchase gaps
    - Pre-cleaning noise (~25% null CustomerID, ~2.5% cancellations, ~0.6% bad unit prices, duplicates)
    """
    start_time = time.time()
    catalog_df = generate_product_catalog(n_products=3200)
    customer_profiles = generate_customer_profiles(n_registered_customers=5000)
    countries, country_weights = build_country_distribution()
    
    catalog_records = catalog_df.to_dict('records')
    n_catalog = len(catalog_records)
    
    print("Generating order baskets and transactional line items...")
    
    # Store transactions list
    transactions = []
    
    # Invoice counter base (UCI Online Retail starts around 536365)
    invoice_seq = 536365
    
    # Max date boundary: 2011-12-09 20:00:00
    end_date = datetime.datetime(2011, 12, 9, 20, 0, 0)
    
    # Target breakdown:
    # Target registered rows ~ 75% of target: ~375,000
    # Target guest rows ~ 25% of target: ~125,000
    # Injected duplicate rows: ~5,200 (~1%)
    target_registered_rows = int(target_rows * 0.74)
    
    # 1. Generate registered customer order sequences
    for cust in customer_profiles:
        cid = cust['CustomerID']
        country = cust['Country']
        tier = cust['Tier']
        basket_min, basket_max = cust['BasketSizeRange']
        qty_min, qty_max = cust['QtyRange']
        
        current_date = cust['FirstOrderDate']
        
        for order_idx in range(cust['TargetOrders']):
            if current_date > end_date or len(transactions) >= target_registered_rows:
                break
                
            # Business hours: 07:00 to 19:59
            hour = random.randint(7, 19)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            invoice_date = current_date.replace(hour=hour, minute=minute, second=second)
            
            invoice_seq += 1
            inv_no = str(invoice_seq)
            
            # Basket size: how many distinct products in this invoice
            basket_size = random.randint(basket_min, basket_max)
            # Pick distinct items for this basket
            chosen_item_indices = np.random.choice(n_catalog, size=min(basket_size, n_catalog), replace=False)
            
            for idx in chosen_item_indices:
                prod = catalog_records[idx]
                qty = random.randint(qty_min, qty_max)
                price = prod['BaseUnitPrice']
                
                transactions.append({
                    'InvoiceNo': inv_no,
                    'StockCode': prod['StockCode'],
                    'Description': prod['Description'],
                    'Quantity': qty,
                    'InvoiceDate': invoice_date,
                    'UnitPrice': price,
                    'CustomerID': cid,
                    'Country': country,
                    'IsCancellation': False
                })
                
            # Calculate gap to next purchase (natural repeat interval)
            # Tier 1: 8-22 days; Tier 2: 18-40 days; Tier 3: 35-90 days; Tier 4: 60-150 days
            if tier == 1:
                gap_days = int(np.random.gamma(shape=3.5, scale=4.0)) + 7
            elif tier == 2:
                gap_days = int(np.random.gamma(shape=3.0, scale=8.0)) + 14
            elif tier == 3:
                gap_days = int(np.random.gamma(shape=2.5, scale=18.0)) + 25
            else:
                gap_days = int(np.random.gamma(shape=2.0, scale=35.0)) + 45
                
            current_date += datetime.timedelta(days=gap_days)

    print(f"Generated {len(transactions):,} lines from registered customers.")

    # 2. Generate Unregistered / Guest checkout transactions (~25% of overall rows)
    current_count = len(transactions)
    target_guest_rows = int(current_count / 0.75 * 0.25)
    print(f"Generating ~{target_guest_rows:,} unregistered / guest checkout rows (~25% null CustomerID)...")
    
    start_epoch = datetime.datetime(2010, 12, 1, 8, 0, 0)
    total_days = (end_date - start_epoch).days
    
    guest_rows_generated = 0
    while guest_rows_generated < target_guest_rows:
        invoice_seq += 1
        inv_no = str(invoice_seq)
        
        # Seasonality distribution: higher in Q4 (days 280 - 373)
        if random.random() < 0.45:
            day_offset = random.randint(280, total_days)
        else:
            day_offset = random.randint(0, total_days)
            
        hour = random.randint(7, 19)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        inv_date = start_epoch + datetime.timedelta(days=day_offset, hours=hour, minutes=minute, seconds=second)
        if inv_date > end_date:
            inv_date = end_date - datetime.timedelta(hours=random.randint(1, 24))
            
        guest_country = np.random.choice(countries, p=country_weights)
        basket_size = random.randint(4, 16)
        chosen_item_indices = np.random.choice(n_catalog, size=min(basket_size, n_catalog), replace=False)
        
        for idx in chosen_item_indices:
            prod = catalog_records[idx]
            qty = random.randint(1, 6)
            price = prod['BaseUnitPrice']
            
            transactions.append({
                'InvoiceNo': inv_no,
                'StockCode': prod['StockCode'],
                'Description': prod['Description'],
                'Quantity': qty,
                'InvoiceDate': inv_date,
                'UnitPrice': price,
                'CustomerID': np.nan,  # Null CustomerID
                'Country': guest_country,
                'IsCancellation': False
            })
            guest_rows_generated += 1

    df = pd.DataFrame(transactions)
    print(f"Total base non-duplicate transactions created: {len(df):,} rows.")

    # 3. Inject Cancellations (~2.5% of unique invoices)
    print("Injecting realistic order cancellations (prefixed with 'C' & negative quantities)...")
    all_invoices = df['InvoiceNo'].unique()
    cancellation_invoices = np.random.choice(all_invoices, size=int(len(all_invoices) * 0.025), replace=False)
    cancel_set = set(cancellation_invoices)
    
    # Mark cancellations: InvoiceNo prefixed with 'C', Quantity made negative
    cancel_mask = df['InvoiceNo'].isin(cancel_set)
    df.loc[cancel_mask, 'InvoiceNo'] = 'C' + df.loc[cancel_mask, 'InvoiceNo'].astype(str)
    df.loc[cancel_mask, 'Quantity'] = -1 * df.loc[cancel_mask, 'Quantity'].abs()
    df.drop(columns=['IsCancellation'], inplace=True, errors='ignore')

    # 4. Inject Zero/Negative Unit Prices (~0.6% of rows: admin adjustments, samples, bad debt)
    print("Injecting pre-cleaning zero/negative unit prices (~0.6% of rows)...")
    n_bad_price = int(len(df) * 0.006)
    bad_price_indices = np.random.choice(df.index, size=n_bad_price, replace=False)
    # 85% zero prices (free samples/promotions), 15% negative prices (debt/reconciliation adjustments)
    zero_indices = bad_price_indices[:int(n_bad_price * 0.85)]
    neg_indices = bad_price_indices[int(n_bad_price * 0.85):]
    df.loc[zero_indices, 'UnitPrice'] = 0.00
    df.loc[neg_indices, 'UnitPrice'] = -1.0 * np.round(np.random.uniform(0.50, 15.00, size=len(neg_indices)), 2)

    # 5. Inject Exact Duplicate Rows (~1.0% matching Kaggle dataset duplicate patterns, ~5,200 rows)
    print("Injecting exact duplicate rows (~1.0% of dataset, ~5,200 rows)...")
    n_dupes = 5200
    dupe_rows = df.sample(n=n_dupes, replace=False, random_state=SEED)
    df = pd.concat([df, dupe_rows], ignore_index=True)

    # Sort chronologically by InvoiceDate
    df = df.sort_values(by='InvoiceDate').reset_index(drop=True)
    
    # Format InvoiceDate as ISO string (YYYY-MM-DD HH:MM:SS)
    df['InvoiceDate'] = df['InvoiceDate'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # CustomerID formatting: float with NaNs for raw CSV
    # (in CSV, null CustomerIDs appear as empty fields)
    df['CustomerID'] = df['CustomerID'].astype('Int64')

    elapsed = time.time() - start_time
    print(f"Raw synthetic dataset generated successfully in {elapsed:.2f}s! Total rows: {len(df):,}")
    return df


def execute_data_cleaning_pipeline(raw_df):
    """
    Executes the multi-step data cleaning pipeline:
    1. Remove cancellations (InvoiceNo starting with 'C' or Quantity < 0)
    2. Remove rows with null CustomerID
    3. Remove rows with UnitPrice <= 0
    4. Remove exact duplicate rows
    
    Returns cleaned_df and a detailed step-by-step summary dictionary.
    """
    print("\n" + "="*70)
    print("EXECUTING MULTI-STEP DATA CLEANING PIPELINE")
    print("="*70)
    
    metrics = []
    
    # Initial Baseline
    initial_count = len(raw_df)
    current_df = raw_df.copy()
    print(f"Initial Raw Record Count: {initial_count:,}")
    
    # Step 1: Remove cancellations (InvoiceNo starting with 'C' OR Quantity < 0)
    step1_mask = current_df['InvoiceNo'].astype(str).str.startswith('C') | (current_df['Quantity'] < 0)
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
    step2_mask = current_df['CustomerID'].isna()
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
    
    # Cast CustomerID to clean int for cleaned data
    current_df['CustomerID'] = current_df['CustomerID'].astype(int)
    
    summary_df = pd.DataFrame(metrics)
    total_removed = initial_count - final_count
    
    print("\n" + "="*85)
    print("BEFORE / AFTER DATA CLEANING SUMMARY")
    print("="*85)
    print(f"{'Cleaning Step':<55} | {'Removed':>10} | {'Remaining':>12}")
    print("-" * 85)
    for m in metrics:
        print(f"{m['Step']:<55} | {m['Rows Removed']:>10,} | {m['Rows Remaining']:>12,}")
    print("-" * 85)
    print(f"{'TOTAL ROWS FILTERED':<55} | {total_removed:>10,} | {final_count:>12,}")
    print(f"Overall Retention Rate: {(final_count / initial_count)*100:.2f}% | Total Removed: {(total_removed / initial_count)*100:.2f}%\n")
    
    return current_df, summary_df


def load_to_sqlite(clean_df, db_path='online_retail.db', table_name='Transactions'):
    """
    Loads cleaned data into SQLite database, creates the table and indexes on
    CustomerID, InvoiceDate, and InvoiceNo.
    """
    print("="*70)
    print(f"INGESTING CLEANED DATA INTO SQLITE: {db_path} -> Table: [{table_name}]")
    print("="*70)
    
    # Remove existing db if needed to ensure fresh build
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create Table schema
    cursor.execute(f"""
    CREATE TABLE {table_name} (
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
    
    # Ingest data using high-speed chunks
    print(f"Inserting {len(clean_df):,} rows into [{table_name}]...")
    
    # Ensure types are native python types for sqlite3
    clean_df[['InvoiceNo', 'StockCode', 'Description', 'Quantity',
              'InvoiceDate', 'UnitPrice', 'CustomerID', 'Country']].to_sql(
        name=table_name,
        con=conn,
        if_exists='append',
        index=False,
        chunksize=50000
    )
        
    print(f"Successfully loaded all {len(clean_df):,} rows into [{table_name}].")
    
    # Create required indexes
    print("\nCreating performance indexes...")
    index_statements = [
        f"CREATE INDEX idx_transactions_customer_id ON {table_name}(CustomerID);",
        f"CREATE INDEX idx_transactions_invoice_date ON {table_name}(InvoiceDate);",
        f"CREATE INDEX idx_transactions_invoice_no ON {table_name}(InvoiceNo);"
    ]
    
    for stmt in index_statements:
        print(f"  Executing: {stmt}")
        cursor.execute(stmt)
    conn.commit()
    
    # Verify index creation
    cursor.execute(f"PRAGMA index_list({table_name});")
    indexes = cursor.fetchall()
    print("\nVerified SQLite Indexes:")
    for idx in indexes:
        print(f"  - Index Name: {idx[1]} (Unique: {bool(idx[2])})")
        
    # Verify Query Plans to prove indexes are functional
    print("\nValidating SQLite Index Query Plans (EXPLAIN QUERY PLAN):")
    sample_queries = [
        f"SELECT COUNT(*) FROM {table_name} WHERE CustomerID = 12345;",
        f"SELECT COUNT(*) FROM {table_name} WHERE InvoiceDate >= '2011-06-01';",
        f"SELECT COUNT(*) FROM {table_name} WHERE InvoiceNo = '540001';"
    ]
    for q in sample_queries:
        cursor.execute(f"EXPLAIN QUERY PLAN {q}")
        plan = cursor.fetchall()
        print(f"  Query: {q}")
        for p in plan:
            print(f"    -> Plan detail: {p[3]}")
            
    conn.close()
    print(f"\nDatabase setup complete. SQLite database file: {os.path.abspath(db_path)}")


def analyze_customer_behavior(clean_df):
    """
    Analyzes and validates the generated dataset's customer behavior:
    - Pareto spend distribution (revenue driven by top 10% customers)
    - Repeat purchase cadence & customer order frequencies
    - Country distribution breakdown
    """
    print("\n" + "="*70)
    print("VALIDATING REALISTIC CUSTOMER BEHAVIOR & METRICS")
    print("="*70)
    
    # Calculate Total Spend per line
    clean_df['LineTotal'] = clean_df['Quantity'] * clean_df['UnitPrice']
    total_revenue = clean_df['LineTotal'].sum()
    
    # Customer Spend aggregation
    cust_spend = clean_df.groupby('CustomerID').agg(
        TotalSpend=('LineTotal', 'sum'),
        OrderCount=('InvoiceNo', 'nunique'),
        ItemCount=('Quantity', 'sum')
    ).reset_index()
    
    cust_spend = cust_spend.sort_values(by='TotalSpend', ascending=False).reset_index(drop=True)
    n_cust = len(cust_spend)
    
    top_10_pct_count = int(n_cust * 0.10)
    top_10_spend = cust_spend.iloc[:top_10_pct_count]['TotalSpend'].sum()
    top_10_share = (top_10_spend / total_revenue) * 100
    
    top_20_pct_count = int(n_cust * 0.20)
    top_20_spend = cust_spend.iloc[:top_20_pct_count]['TotalSpend'].sum()
    top_20_share = (top_20_spend / total_revenue) * 100
    
    print(f"Total Unique Clean Customers: {n_cust:,}")
    print(f"Total Revenue Generated: GBP {total_revenue:,.2f}")
    print(f"Top 10% Customers ({top_10_pct_count:,} accounts): GBP {top_10_spend:,.2f} ({top_10_share:.2f}% of total revenue)")
    print(f"Top 20% Customers ({top_20_pct_count:,} accounts): GBP {top_20_spend:,.2f} ({top_20_share:.2f}% of total revenue)")
    print(f"Average Orders per Customer: {cust_spend['OrderCount'].mean():.2f} (Median: {cust_spend['OrderCount'].median():.0f}, Max: {cust_spend['OrderCount'].max()})")
    
    # Country distribution
    country_counts = clean_df['Country'].value_counts()
    uk_pct = (country_counts.get('United Kingdom', 0) / len(clean_df)) * 100
    print(f"\nCountry Distribution:")
    print(f"  United Kingdom: {country_counts.get('United Kingdom', 0):,} ({uk_pct:.2f}%)")
    print(f"  International (Other {len(country_counts)-1} countries): {len(clean_df) - country_counts.get('United Kingdom', 0):,} ({100 - uk_pct:.2f}%)")
    
    # Date Range
    print(f"\nDate Range: {clean_df['InvoiceDate'].min()} to {clean_df['InvoiceDate'].max()}")


def main():
    print("======================================================================")
    print("  SYNTHETIC E-COMMERCE TRANSACTION DATASET GENERATOR & SQL PIPELINE")
    print("======================================================================")
    total_start = time.time()
    
    raw_csv_path = 'raw_online_retail.csv'
    cleaned_csv_path = 'cleaned_online_retail.csv'
    db_path = 'online_retail.db'
    
    # 1. Generate Raw Dataset (~520,000 rows)
    raw_df = generate_synthetic_transactions(target_rows=520000)
    
    # Export raw CSV
    print(f"\nExporting raw dataset to {raw_csv_path}...")
    raw_df.to_csv(raw_csv_path, index=False)
    raw_size_mb = os.path.getsize(raw_csv_path) / (1024 * 1024)
    print(f"Raw CSV exported: {raw_csv_path} ({raw_size_mb:.2f} MB, {len(raw_df):,} rows)")
    
    # 2. Execute Data Cleaning Pipeline
    cleaned_df, summary_df = execute_data_cleaning_pipeline(raw_df)
    
    # Export cleaned CSV
    print(f"Exporting cleaned dataset to {cleaned_csv_path}...")
    cleaned_df.to_csv(cleaned_csv_path, index=False)
    clean_size_mb = os.path.getsize(cleaned_csv_path) / (1024 * 1024)
    print(f"Cleaned CSV exported: {cleaned_csv_path} ({clean_size_mb:.2f} MB, {len(cleaned_df):,} rows)")
    
    # 3. Analyze customer behavior
    analyze_customer_behavior(cleaned_df)
    
    # 4. Ingest Cleaned Data into SQLite with Indexes
    load_to_sqlite(cleaned_df, db_path=db_path, table_name='Transactions')
    db_size_mb = os.path.getsize(db_path) / (1024 * 1024)
    print(f"SQLite DB size: {db_size_mb:.2f} MB")
    
    total_elapsed = time.time() - total_start
    print("\n" + "="*70)
    print(f"PIPELINE EXECUTION FINISHED SUCCESSFULLY IN {total_elapsed:.2f}s!")
    print("="*70)

if __name__ == '__main__':
    main()
