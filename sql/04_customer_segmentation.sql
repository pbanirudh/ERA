-- ==========================================
-- FEATURE 4: CUSTOMER SEGMENTATION & RFM TIERING
-- Database: online_retail.db | Table: Transactions
-- Compatible with SQLite, PostgreSQL, and MySQL
-- ==========================================

-- ----------------------------------------------------
-- SECTION 4.1: DENSE_RANK CUSTOMER TIERING
-- Assigns consecutive ranks by total spend and classifies customers into:
--   - Platinum Tier (Top 10% Spenders)
--   - Gold Tier (Next 15% Spenders, Top 11-25%)
--   - General Tier (Remaining 75%)
-- ----------------------------------------------------

WITH Benchmark AS (
    SELECT MAX(InvoiceDate) AS MaxDatasetDate FROM Transactions
),
Customer_Aggregates AS (
    SELECT 
        t.CustomerID,
        t.Country,
        ROUND(SUM(t.Quantity * t.UnitPrice), 2) AS TotalSpend,
        COUNT(DISTINCT t.InvoiceNo) AS TotalOrders,
        ROUND(SUM(t.Quantity * t.UnitPrice) / COUNT(DISTINCT t.InvoiceNo), 2) AS AvgOrderValue,
        ROUND(julianday(b.MaxDatasetDate) - julianday(MAX(t.InvoiceDate)), 1) AS DaysSinceLastPurchase
    FROM 
        Transactions t
    CROSS JOIN 
        Benchmark b
    GROUP BY 
        t.CustomerID, t.Country
),
Customer_Rankings AS (
    SELECT 
        CustomerID,
        Country,
        TotalSpend,
        TotalOrders,
        AvgOrderValue,
        DaysSinceLastPurchase,
        -- DENSE_RANK guarantees consecutive ranks without gaps
        DENSE_RANK() OVER (ORDER BY TotalSpend DESC) AS CustomerRank,
        -- Cumulative distribution to determine exact percentiles
        ROUND(CUME_DIST() OVER (ORDER BY TotalSpend DESC), 4) AS SpendPercentile
    FROM 
        Customer_Aggregates
)
SELECT 
    CustomerID,
    Country,
    TotalSpend,
    TotalOrders,
    AvgOrderValue,
    DaysSinceLastPurchase,
    CustomerRank,
    ROUND(SpendPercentile * 100.0, 2) AS SpendPercentilePct,
    CASE 
        WHEN SpendPercentile <= 0.10 THEN 'Platinum Tier (Top 10%)'
        WHEN SpendPercentile <= 0.25 THEN 'Gold Tier (Top 25%)'
        ELSE 'General Tier'
    END AS CustomerSegment,
    CASE 
        WHEN DaysSinceLastPurchase > 60 THEN 'At-Risk Churn'
        ELSE 'Active'
    END AS ChurnRiskStatus
FROM 
    Customer_Rankings
ORDER BY 
    TotalSpend DESC;


-- ----------------------------------------------------
-- SECTION 4.2: SEGMENT PERFORMANCE SUMMARY
-- Rollup by assigned tier to evaluate revenue share and churn exposure.
-- ----------------------------------------------------
WITH Benchmark AS (
    SELECT MAX(InvoiceDate) AS MaxDatasetDate FROM Transactions
),
Customer_Rankings AS (
    SELECT 
        t.CustomerID,
        SUM(t.Quantity * t.UnitPrice) AS TotalSpend,
        COUNT(DISTINCT t.InvoiceNo) AS TotalOrders,
        ROUND(julianday(b.MaxDatasetDate) - julianday(MAX(t.InvoiceDate)), 1) AS DaysSinceLastPurchase,
        CUME_DIST() OVER (ORDER BY SUM(t.Quantity * t.UnitPrice) DESC) AS SpendPercentile
    FROM 
        Transactions t
    CROSS JOIN 
        Benchmark b
    GROUP BY 
        t.CustomerID
),
Tiered_Customers AS (
    SELECT 
        CustomerID,
        TotalSpend,
        TotalOrders,
        DaysSinceLastPurchase,
        CASE 
            WHEN SpendPercentile <= 0.10 THEN 'Platinum Tier (Top 10%)'
            WHEN SpendPercentile <= 0.25 THEN 'Gold Tier (Top 25%)'
            ELSE 'General Tier'
        END AS CustomerSegment,
        CASE 
            WHEN DaysSinceLastPurchase > 60 THEN 1 
            ELSE 0 
        END AS IsAtRisk
    FROM 
        Customer_Rankings
)
SELECT 
    CustomerSegment,
    COUNT(CustomerID) AS CustomerCount,
    ROUND(COUNT(CustomerID) * 100.0 / (SELECT COUNT(*) FROM Tiered_Customers), 2) AS CustomerSharePct,
    ROUND(SUM(TotalSpend), 2) AS TotalTierRevenue,
    ROUND(SUM(TotalSpend) * 100.0 / (SELECT SUM(TotalSpend) FROM Tiered_Customers), 2) AS RevenueSharePct,
    ROUND(AVG(TotalOrders), 2) AS AvgOrdersPerCustomer,
    ROUND(AVG(TotalSpend) / AVG(TotalOrders), 2) AS TierAOV,
    SUM(IsAtRisk) AS AtRiskAccounts,
    ROUND(SUM(IsAtRisk) * 100.0 / COUNT(CustomerID), 2) AS AtRiskRatePct
FROM 
    Tiered_Customers
GROUP BY 
    CustomerSegment
ORDER BY 
    TotalTierRevenue DESC;
