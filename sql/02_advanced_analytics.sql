-- ==========================================
-- 2. ADVANCED BUSINESS ANALYTICS QUERIES
-- E-Commerce Retail Analytics Portfolio Project
-- Compatible with MySQL and PostgreSQL
-- ==========================================

-- ------------------------------------------
-- QUERY 2.1: RFM METRICS (Recency, Frequency, Monetary)
-- Purpose: Quantifies customer value based on:
--   - Recency: How recently a customer made a purchase (days since last transaction relative to dataset end date)
--   - Frequency: How often they buy (distinct count of transactions)
--   - Monetary Value: How much money they spend (sum of total amount)
-- ------------------------------------------

-- Database compatibility check:
-- - PostgreSQL: MAX(InvoiceDate) - MAX(InvoiceDate)
-- - MySQL: DATEDIFF(MAX_DATE, InvoiceDate)
-- The query below uses a cross-compatible CTE to grab the global max date (benchmark) 
-- and compute the metrics for each customer.

WITH Dataset_Benchmark AS (
    -- Finds the latest date in the database to act as the "current day" for analysis
    SELECT MAX(InvoiceDate) AS global_max_date FROM cleaned_online_retail
),
Customer_Aggregates AS (
    SELECT 
        c.CustomerID,
        MAX(c.InvoiceDate) AS last_purchase_date,
        COUNT(DISTINCT c.InvoiceNo) AS Frequency,
        SUM(c.TotalAmount) AS MonetaryValue
    FROM 
        cleaned_online_retail c
    GROUP BY 
        c.CustomerID
)
SELECT 
    ca.CustomerID,
    -- Recency calculation: days between customer's last order and the dataset's benchmark date
    -- MySQL syntax: DATEDIFF(db.global_max_date, ca.last_purchase_date)
    -- PostgreSQL syntax: EXTRACT(DAY FROM db.global_max_date - ca.last_purchase_date)
    -- Standard-compliant dynamic expression:
    ROUND(
        (EXTRACT(EPOCH FROM db.global_max_date) - EXTRACT(EPOCH FROM ca.last_purchase_date)) / 86400
    ) AS Recency,
    ca.Frequency,
    ROUND(ca.MonetaryValue, 2) AS MonetaryValue
FROM 
    Customer_Aggregates ca
CROSS JOIN 
    Dataset_Benchmark db
ORDER BY 
    MonetaryValue DESC;


-- ------------------------------------------
-- QUERY 2.2: CUSTOMER RANKING & TIERING
-- Purpose: Ranks customers by total spend using DENSE_RANK() to prevent rank gaps,
-- and assigns them to Top 10%, Top 25%, or General tiers using PERCENT_RANK().
-- ------------------------------------------

WITH Customer_Spend AS (
    SELECT 
        CustomerID,
        Country,
        SUM(TotalAmount) AS TotalSpend,
        COUNT(DISTINCT InvoiceNo) AS TotalOrders
    FROM 
        cleaned_online_retail
    GROUP BY 
        CustomerID, Country
),
Customer_Ranks AS (
    SELECT 
        CustomerID,
        Country,
        TotalSpend,
        TotalOrders,
        -- DENSE_RANK assigns consecutive ranks to customers. Top spender is 1.
        DENSE_RANK() OVER (ORDER BY TotalSpend DESC) AS CustomerRank,
        -- PERCENT_RANK returns a value between 0 and 1 representing the percentile.
        PERCENT_RANK() OVER (ORDER BY TotalSpend DESC) AS PercentileRank
    FROM 
        Customer_Spend
)
SELECT 
    CustomerID,
    Country,
    ROUND(TotalSpend, 2) AS TotalSpend,
    TotalOrders,
    CustomerRank,
    CASE 
        WHEN PercentileRank <= 0.10 THEN 'Top 10% (Platinum Tier)'
        WHEN PercentileRank <= 0.25 THEN 'Top 25% (Gold Tier)'
        ELSE 'General Tier'
    END AS CustomerSegment
FROM 
    Customer_Ranks
ORDER BY 
    TotalSpend DESC;


-- ------------------------------------------
-- QUERY 2.3: CHURN & REPURCHASE ANALYSIS
-- Purpose: Evaluates purchasing velocity.
--   1. Uses LAG() to find the date of the customer's previous order.
--   2. Calculates the gap between orders to find the customer's average purchase cadence.
--   3. Identifies "At-Risk Churn" (no purchases within 60 days of the dataset's end date).
-- ------------------------------------------

WITH Invoice_Sequence AS (
    -- Deduplicate dates to get a sequence of unique purchase dates per customer
    SELECT DISTINCT
        CustomerID,
        InvoiceNo,
        InvoiceDate
    FROM 
        cleaned_online_retail
),
Order_Intervals AS (
    SELECT 
        CustomerID,
        InvoiceDate,
        -- Get the timestamp of the previous transaction
        LAG(InvoiceDate) OVER (PARTITION BY CustomerID ORDER BY InvoiceDate) AS PrevInvoiceDate
    FROM 
        Invoice_Sequence
),
Customer_Cadence AS (
    SELECT 
        CustomerID,
        -- Average days between consecutive orders for returning customers
        AVG(
            ROUND(
                (EXTRACT(EPOCH FROM InvoiceDate) - EXTRACT(EPOCH FROM PrevInvoiceDate)) / 86400
            )
        ) AS AvgRepurchaseCadenceDays,
        MAX(InvoiceDate) AS LastPurchaseDate
    FROM 
        Order_Intervals
    WHERE 
        PrevInvoiceDate IS NOT NULL -- Excludes the first purchase (no prior order)
    GROUP BY 
        CustomerID
),
Dataset_Max AS (
    SELECT MAX(InvoiceDate) AS max_date FROM cleaned_online_retail
)
SELECT 
    c.CustomerID,
    COALESCE(ROUND(cc.AvgRepurchaseCadenceDays, 1), 0.0) AS AvgRepurchaseCadenceDays,
    cc.LastPurchaseDate,
    ROUND(
        (EXTRACT(EPOCH FROM dm.max_date) - EXTRACT(EPOCH FROM cc.LastPurchaseDate)) / 86400
    ) AS DaysSinceLastPurchase,
    CASE 
        WHEN ROUND((EXTRACT(EPOCH FROM dm.max_date) - EXTRACT(EPOCH FROM cc.LastPurchaseDate)) / 86400) > 60 THEN 'At-Risk Churn'
        ELSE 'Active'
    END AS ChurnStatus
FROM 
    Customer_Cadence cc
CROSS JOIN 
    Dataset_Max dm
RIGHT JOIN (
    -- Ensures we don't exclude customers who only made 1 purchase (their AvgRepurchaseCadence is NULL)
    SELECT CustomerID FROM cleaned_online_retail GROUP BY CustomerID
) c ON cc.CustomerID = c.CustomerID;


-- ------------------------------------------
-- QUERY 2.4: COHORT ANALYSIS (ACQUISITION & RETENTION)
-- Purpose: Groups customers by the month of their first purchase (Cohort)
-- and monitors how active they are in subsequent months.
-- ------------------------------------------

WITH Customer_Acquisition AS (
    -- Step 1: Identify the customer acquisition date (first purchase date)
    SELECT 
        CustomerID,
        MIN(InvoiceDate) AS FirstPurchaseDate,
        -- Truncate to first day of acquisition month
        -- PostgreSQL: DATE_TRUNC('month', MIN(InvoiceDate))
        -- MySQL: STR_TO_DATE(DATE_FORMAT(MIN(InvoiceDate), '%Y-%m-01'), '%Y-%m-%d')
        DATE_TRUNC('month', MIN(InvoiceDate)) AS AcquisitionMonth
    FROM 
        cleaned_online_retail
    GROUP BY 
        CustomerID
),
Customer_Activity AS (
    -- Step 2: Track active transaction months for each customer
    SELECT DISTINCT
        CustomerID,
        DATE_TRUNC('month', InvoiceDate) AS ActivityMonth,
        SUM(TotalAmount) AS MonthlySpend
    FROM 
        cleaned_online_retail
    GROUP BY 
        CustomerID,
        DATE_TRUNC('month', InvoiceDate)
),
Cohort_Metrics AS (
    -- Step 3: Compute the difference in months between acquisition and activity (Cohort Index)
    SELECT 
        a.AcquisitionMonth,
        c.ActivityMonth,
        c.MonthlySpend,
        -- Number of months elapsed since first purchase
        (EXTRACT(YEAR FROM c.ActivityMonth) - EXTRACT(YEAR FROM a.AcquisitionMonth)) * 12 + 
        (EXTRACT(MONTH FROM c.ActivityMonth) - EXTRACT(MONTH FROM a.AcquisitionMonth)) AS CohortIndex,
        a.CustomerID
    FROM 
        Customer_Activity c
    JOIN 
        Customer_Acquisition a ON c.CustomerID = a.CustomerID
),
Cohort_Sizes AS (
    -- Step 4: Calculate the total unique customers in each cohort (Cohort Size)
    SELECT 
        AcquisitionMonth,
        COUNT(DISTINCT CustomerID) AS CohortSize
    FROM 
        Customer_Acquisition
    GROUP BY 
        AcquisitionMonth
)
-- Step 5: Pivot or aggregate retention and monetary metrics per cohort over time
SELECT 
    m.AcquisitionMonth,
    s.CohortSize,
    m.CohortIndex,
    COUNT(DISTINCT m.CustomerID) AS RetainedCustomers,
    ROUND(CAST(COUNT(DISTINCT m.CustomerID) AS DECIMAL) / s.CohortSize * 100, 2) AS RetentionRatePercent,
    ROUND(SUM(m.MonthlySpend), 2) AS CohortRevenue
FROM 
    Cohort_Metrics m
JOIN 
    Cohort_Sizes s ON m.AcquisitionMonth = s.AcquisitionMonth
GROUP BY 
    m.AcquisitionMonth,
    s.CohortSize,
    m.CohortIndex
ORDER BY 
    m.AcquisitionMonth,
    m.CohortIndex;
