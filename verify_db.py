import sqlite3
import pandas as pd

conn = sqlite3.connect('online_retail.db')

print('=== 1. Table Row Count ===')
count_df = pd.read_sql('SELECT COUNT(*) as count FROM Transactions', conn)
print(count_df)

print('\n=== 2. Sample 5 Clean Rows ===')
sample_df = pd.read_sql('SELECT * FROM Transactions LIMIT 5', conn)
print(sample_df)

print('\n=== 3. Indexes on Transactions ===')
indexes_df = pd.read_sql("PRAGMA index_list('Transactions')", conn)
print(indexes_df[['seq', 'name', 'unique']])

print('\n=== 4. Data Cleaning Verification (Should all be 0) ===')
audit_df = pd.read_sql("""
SELECT 
    SUM(CASE WHEN CustomerID IS NULL THEN 1 ELSE 0 END) as null_customers,
    SUM(CASE WHEN UnitPrice <= 0 THEN 1 ELSE 0 END) as non_positive_price,
    SUM(CASE WHEN Quantity <= 0 THEN 1 ELSE 0 END) as non_positive_qty,
    SUM(CASE WHEN InvoiceNo LIKE 'C%' THEN 1 ELSE 0 END) as cancellations
FROM Transactions
""", conn)
print(audit_df)

print('\n=== 5. Country Distribution Summary ===')
countries_df = pd.read_sql("""
SELECT Country, COUNT(*) as tx_count, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Transactions), 2) as pct
FROM Transactions
GROUP BY Country
ORDER BY tx_count DESC
LIMIT 10
""", conn)
print(countries_df)

conn.close()
