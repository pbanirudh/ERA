-- ==========================================
-- FEATURE 3: REPURCHASE TIMING & 60-DAY CHURN ANALYSIS
-- Compatible with SQLite, PostgreSQL, and MySQL
-- Database: online_retail.db | Table: Transactions
-- ==========================================

-- ----------------------------------------------------
-- SECTION 3.1: INVOICE SEQUENCE & INTER-ORDER GAP TABLE
-- Uses LAG() window function to calculate days between consecutive orders.
-- ----------------------------------------------------
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
        InvoiceNo,
        InvoiceDate,
        LAG(InvoiceDate) OVER (
            PARTITION BY CustomerID 
            ORDER BY InvoiceDate
        ) AS PrevInvoiceDate,
        -- SQLite date math: julianday(t2) - julianday(t1) returns days difference
        ROUND(
            julianday(InvoiceDate) - julianday(
                LAG(InvoiceDate) OVER (PARTITION BY CustomerID ORDER BY InvoiceDate)
            ), 1
        ) AS DaysSinceLastOrder
    FROM 
        Distinct_Invoices
)
SELECT 
    CustomerID,
    InvoiceNo,
    InvoiceDate,
    PrevInvoiceDate,
    DaysSinceLastOrder
FROM 
    Order_Gaps
WHERE 
    PrevInvoiceDate IS NOT NULL
ORDER BY 
    CustomerID, InvoiceDate;


-- ----------------------------------------------------
-- SECTION 3.2: AVERAGE CUSTOMER PURCHASE CADENCE
-- Aggregates repeat buyers to determine average days between purchases.
-- ----------------------------------------------------
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
        ROUND(MAX(DaysSinceLastOrder), 1) AS MaxDaysBetweenOrders,
        MAX(InvoiceDate) AS MostRecentOrderDate
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


-- ----------------------------------------------------
-- SECTION 3.3: 60-DAY INACTIVITY & CHURN DROP-OFF ANALYSIS
-- Evaluates the drop-off in repurchase probability when inactivity exceeds 60 days.
-- ----------------------------------------------------
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
        END AS CadenceBucket,
        CASE 
            WHEN DaysGap <= 60 THEN 'Within 60-Day Window'
            ELSE 'Beyond 60 Days (At-Risk / Lapsed)'
        END AS InactivityStatus
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


-- ----------------------------------------------------
-- SECTION 3.4: CURRENT CUSTOMER CHURN RISK SCORING (RELATIVE TO DATASET END)
-- ----------------------------------------------------
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
