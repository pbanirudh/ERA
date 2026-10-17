-- ==========================================
-- FEATURE 2: REVENUE CONCENTRATION & REPEAT SPEND ANALYSIS
-- Compatible with SQLite, PostgreSQL, and MySQL
-- Database: online_retail.db | Table: Transactions
-- ==========================================

-- ----------------------------------------------------
-- SECTION 2.1: CUSTOMER REVENUE SUMMARY TABLE / CTE
-- Computes lifetime spend, total invoices, and distinct products per customer.
-- ----------------------------------------------------

WITH Customer_Metrics AS (
    SELECT 
        CustomerID,
        Country,
        COUNT(DISTINCT InvoiceNo) AS TotalInvoices,
        COUNT(StockCode) AS TotalLineItems,
        SUM(Quantity) AS TotalUnitsSold,
        ROUND(SUM(Quantity * UnitPrice), 2) AS TotalRevenue,
        ROUND(AVG(Quantity * UnitPrice), 2) AS AvgLineItemValue,
        MIN(InvoiceDate) AS FirstPurchaseDate,
        MAX(InvoiceDate) AS LastPurchaseDate
    FROM 
        Transactions
    GROUP BY 
        CustomerID, Country
),

-- ----------------------------------------------------
-- SECTION 2.2: CUSTOMER REVENUE RANKING
-- Uses DENSE_RANK() to rank customers by total revenue (1 = top spender).
-- ----------------------------------------------------
Customer_Ranks AS (
    SELECT 
        CustomerID,
        Country,
        TotalInvoices,
        TotalRevenue,
        CASE 
            WHEN TotalInvoices >= 2 THEN 'Repeat Customer'
            ELSE 'Single Order'
        END AS CustomerType,
        DENSE_RANK() OVER (ORDER BY TotalRevenue DESC) AS RevenueRank,
        ROW_NUMBER() OVER (ORDER BY TotalRevenue DESC) AS RowNum,
        COUNT(*) OVER () AS TotalCustomers,
        SUM(TotalRevenue) OVER () AS PortfolioRevenue
    FROM 
        Customer_Metrics
)
SELECT 
    CustomerID,
    Country,
    TotalInvoices,
    CustomerType,
    TotalRevenue,
    RevenueRank,
    ROUND(TotalRevenue * 100.0 / PortfolioRevenue, 3) AS PctOfTotalRevenue,
    ROUND(SUM(TotalRevenue) OVER (ORDER BY TotalRevenue DESC) * 100.0 / PortfolioRevenue, 2) AS CumulativeRevenuePct
FROM 
    Customer_Ranks
ORDER BY 
    TotalRevenue DESC;


-- ----------------------------------------------------
-- SECTION 2.3: REPEAT CUSTOMER (2+ INVOICES) REVENUE SHARE
-- Proves what percentage of total revenue is driven by repeat buyers.
-- ----------------------------------------------------
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


-- ----------------------------------------------------
-- SECTION 2.4: PARETO REVENUE CONCENTRATION (TOP 10% & TOP 20%)
-- Quantifies the exact revenue share driven by top customer percentiles.
-- ----------------------------------------------------
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
