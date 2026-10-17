"""
Execute and Validate SQL Feature 2 (Revenue Concentration) and Feature 3 (Repurchase Timing)
"""

import sqlite3
import pandas as pd

conn = sqlite3.connect('online_retail.db')

print("="*80)
print("FEATURE 2: REVENUE CONCENTRATION & REPEAT SPEND ANALYSIS")
print("="*80)

print("\n--- 2.1 Repeat Customer (2+ Invoices) Revenue Share ---")
q_repeat = """
WITH Customer_Aggregates AS (
    SELECT 
        CustomerID,
        COUNT(DISTINCT InvoiceNo) AS InvoiceCount,
        SUM(Quantity * UnitPrice) AS CustomerSpend
    FROM 
        Transactions
    GROUP BY 
        CustomerID
),
Segmented_Spend AS (
    SELECT 
        CASE 
            WHEN InvoiceCount >= 2 THEN 'Repeat Customer (2+ Invoices)'
            ELSE 'One-Time Customer (1 Invoice)'
        END AS CustomerTier,
        COUNT(CustomerID) AS CustomerCount,
        SUM(CustomerSpend) AS TierRevenue
    FROM 
        Customer_Aggregates
    GROUP BY 
        CASE 
            WHEN InvoiceCount >= 2 THEN 'Repeat Customer (2+ Invoices)'
            ELSE 'One-Time Customer (1 Invoice)'
        END
)
SELECT 
    CustomerTier,
    CustomerCount,
    ROUND(CustomerCount * 100.0 / (SELECT COUNT(DISTINCT CustomerID) FROM Transactions), 2) AS CustomerSharePct,
    ROUND(TierRevenue, 2) AS TotalTierRevenue,
    ROUND(TierRevenue * 100.0 / (SELECT SUM(Quantity * UnitPrice) FROM Transactions), 2) AS RevenueSharePct
FROM 
    Segmented_Spend
ORDER BY 
    TotalTierRevenue DESC;
"""
print(pd.read_sql(q_repeat, conn))

print("\n--- 2.2 Pareto Revenue Concentration (Top 5%, 10%, 20%) ---")
q_pareto = """
WITH Ranked_Customers AS (
    SELECT 
        CustomerID,
        SUM(Quantity * UnitPrice) AS TotalSpend,
        ROW_NUMBER() OVER (ORDER BY SUM(Quantity * UnitPrice) DESC) AS SpendRank,
        COUNT(*) OVER () AS TotalCustomerCount,
        SUM(SUM(Quantity * UnitPrice)) OVER () AS TotalPortfolioSpend
    FROM 
        Transactions
    GROUP BY 
        CustomerID
)
SELECT 
    'Top 5% Customers' AS CustomerGroup,
    COUNT(CustomerID) AS Accounts,
    ROUND(SUM(TotalSpend), 2) AS GroupRevenue,
    ROUND(SUM(TotalSpend) * 100.0 / MAX(TotalPortfolioSpend), 2) AS RevenueSharePct
FROM Ranked_Customers
WHERE SpendRank <= CAST(TotalCustomerCount * 0.05 AS INT)

UNION ALL

SELECT 
    'Top 10% Customers' AS CustomerGroup,
    COUNT(CustomerID) AS Accounts,
    ROUND(SUM(TotalSpend), 2) AS GroupRevenue,
    ROUND(SUM(TotalSpend) * 100.0 / MAX(TotalPortfolioSpend), 2) AS RevenueSharePct
FROM Ranked_Customers
WHERE SpendRank <= CAST(TotalCustomerCount * 0.10 AS INT)

UNION ALL

SELECT 
    'Top 20% Customers' AS CustomerGroup,
    COUNT(CustomerID) AS Accounts,
    ROUND(SUM(TotalSpend), 2) AS GroupRevenue,
    ROUND(SUM(TotalSpend) * 100.0 / MAX(TotalPortfolioSpend), 2) AS RevenueSharePct
FROM Ranked_Customers
WHERE SpendRank <= CAST(TotalCustomerCount * 0.20 AS INT)

UNION ALL

SELECT 
    'Remaining 80% Customers' AS CustomerGroup,
    COUNT(CustomerID) AS Accounts,
    ROUND(SUM(TotalSpend), 2) AS GroupRevenue,
    ROUND(SUM(TotalSpend) * 100.0 / MAX(TotalPortfolioSpend), 2) AS RevenueSharePct
FROM Ranked_Customers
WHERE SpendRank > CAST(TotalCustomerCount * 0.20 AS INT);
"""
print(pd.read_sql(q_pareto, conn))


print("\n" + "="*80)
print("FEATURE 3: REPURCHASE TIMING & 60-DAY INACTIVITY ANALYSIS")
print("="*80)

print("\n--- 3.1 Repeat Customer Purchase Cadence Benchmark ---")
q_cadence = """
WITH Distinct_Invoices AS (
    SELECT DISTINCT
        CustomerID,
        InvoiceNo,
        InvoiceDate
    FROM 
        Transactions
),
Order_Gaps AS (
    SELECT 
        CustomerID,
        InvoiceDate,
        LAG(InvoiceDate) OVER (
            PARTITION BY CustomerID 
            ORDER BY InvoiceDate
        ) AS PrevInvoiceDate,
        ROUND(
            julianday(InvoiceDate) - julianday(
                LAG(InvoiceDate) OVER (PARTITION BY CustomerID ORDER BY InvoiceDate)
            ), 1
        ) AS DaysSinceLastOrder
    FROM 
        Distinct_Invoices
),
Customer_Cadence AS (
    SELECT 
        CustomerID,
        COUNT(DaysSinceLastOrder) AS RepeatOrderCount,
        ROUND(AVG(DaysSinceLastOrder), 1) AS AvgDaysBetweenOrders,
        ROUND(MIN(DaysSinceLastOrder), 1) AS MinDaysBetweenOrders,
        ROUND(MAX(DaysSinceLastOrder), 1) AS MaxDaysBetweenOrders
    FROM 
        Order_Gaps
    WHERE 
        PrevInvoiceDate IS NOT NULL
    GROUP BY 
        CustomerID
)
SELECT 
    COUNT(CustomerID) AS RepeatCustomersAnalyzed,
    ROUND(AVG(AvgDaysBetweenOrders), 1) AS BenchmarkAvgCadenceDays,
    ROUND(AVG(MinDaysBetweenOrders), 1) AS BenchmarkMinCadenceDays,
    ROUND(AVG(MaxDaysBetweenOrders), 1) AS BenchmarkMaxCadenceDays
FROM 
    Customer_Cadence;
"""
print(pd.read_sql(q_cadence, conn))

print("\n--- 3.2 Repurchase Distribution by Inactivity Windows (60-Day Drop-Off) ---")
q_windows = """
WITH Distinct_Invoices AS (
    SELECT DISTINCT
        CustomerID,
        InvoiceNo,
        InvoiceDate
    FROM 
        Transactions
),
Order_Gaps AS (
    SELECT 
        CustomerID,
        InvoiceDate,
        LAG(InvoiceDate) OVER (
            PARTITION BY CustomerID 
            ORDER BY InvoiceDate
        ) AS PrevInvoiceDate,
        ROUND(
            julianday(InvoiceDate) - julianday(
                LAG(InvoiceDate) OVER (PARTITION BY CustomerID ORDER BY InvoiceDate)
            ), 1
        ) AS DaysGap
    FROM 
        Distinct_Invoices
),
Gap_Buckets AS (
    SELECT 
        CustomerID,
        DaysGap,
        CASE 
            WHEN DaysGap <= 30 THEN '01. <= 30 Days'
            WHEN DaysGap <= 60 THEN '02. 31 - 60 Days'
            WHEN DaysGap <= 90 THEN '03. 61 - 90 Days'
            WHEN DaysGap <= 120 THEN '04. 91 - 120 Days'
            ELSE '05. > 120 Days'
        END AS CadenceBucket
    FROM 
        Order_Gaps
    WHERE 
        PrevInvoiceDate IS NOT NULL
)
SELECT 
    CadenceBucket,
    COUNT(*) AS RepurchaseEvents,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Gap_Buckets), 2) AS PctOfAllRepurchases,
    ROUND(SUM(COUNT(*)) OVER (ORDER BY CadenceBucket) * 100.0 / (SELECT COUNT(*) FROM Gap_Buckets), 2) AS CumulativePct
FROM 
    Gap_Buckets
GROUP BY 
    CadenceBucket
ORDER BY 
    CadenceBucket;
"""
print(pd.read_sql(q_windows, conn))

print("\n--- 3.3 Customer Base Churn Status Relative to Dataset End Date ---")
q_churn = """
WITH Benchmark AS (
    SELECT MAX(InvoiceDate) AS MaxDatasetDate FROM Transactions
),
Customer_Recency AS (
    SELECT 
        t.CustomerID,
        MAX(t.InvoiceDate) AS LastOrderDate,
        ROUND(julianday(b.MaxDatasetDate) - julianday(MAX(t.InvoiceDate)), 1) AS DaysSinceLastPurchase,
        COUNT(DISTINCT t.InvoiceNo) AS LifetimeOrders,
        ROUND(SUM(t.Quantity * t.UnitPrice), 2) AS LifetimeSpend
    FROM 
        Transactions t
    CROSS JOIN 
        Benchmark b
    GROUP BY 
        t.CustomerID
)
SELECT 
    CASE 
        WHEN DaysSinceLastPurchase <= 30 THEN 'Active (<= 30 Days)'
        WHEN DaysSinceLastPurchase <= 60 THEN 'Cooling (31 - 60 Days)'
        WHEN DaysSinceLastPurchase <= 120 THEN 'At-Risk Churn (61 - 120 Days)'
        ELSE 'Lapsed / Churned (> 120 Days)'
    END AS ChurnSegment,
    COUNT(CustomerID) AS CustomerCount,
    ROUND(COUNT(CustomerID) * 100.0 / (SELECT COUNT(*) FROM Customer_Recency), 2) AS CustomerSharePct,
    ROUND(SUM(LifetimeSpend), 2) AS TotalSegmentRevenue,
    ROUND(SUM(LifetimeSpend) * 100.0 / (SELECT SUM(LifetimeSpend) FROM Customer_Recency), 2) AS RevenueSharePct
FROM 
    Customer_Recency
GROUP BY 
    CASE 
        WHEN DaysSinceLastPurchase <= 30 THEN 'Active (<= 30 Days)'
        WHEN DaysSinceLastPurchase <= 60 THEN 'Cooling (31 - 60 Days)'
        WHEN DaysSinceLastPurchase <= 120 THEN 'At-Risk Churn (61 - 120 Days)'
        ELSE 'Lapsed / Churned (> 120 Days)'
    END
ORDER BY 
    MIN(DaysSinceLastPurchase);
"""
print(pd.read_sql(q_churn, conn))

conn.close()
