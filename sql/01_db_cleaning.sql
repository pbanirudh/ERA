-- ==========================================
-- 1. DATABASE SETUP & DATA CLEANING BLUEPRINT
-- E-Commerce Retail Analytics Portfolio Project
-- Compatible with MySQL and PostgreSQL
-- ==========================================

-- ------------------------------------------
-- SECTION 1.1: DDL FOR RAW SCHEMA
-- This table mirrors the structure of the Kaggle Online Retail CSV.
-- ------------------------------------------

-- Drop the raw table if it already exists to ensure a clean start
DROP TABLE IF EXISTS raw_online_retail;

CREATE TABLE raw_online_retail (
    InvoiceNo VARCHAR(50),      -- Stored as string to handle alphanumeric invoice numbers (e.g., 'C12345' for cancellations)
    StockCode VARCHAR(50),      -- Stored as string to handle alphanumeric product codes (e.g., 'POST', '85123A')
    Description VARCHAR(255),   -- Description of the item purchased
    Quantity INT,               -- Number of units purchased (can be negative for returns/cancellations)
    InvoiceDate VARCHAR(50),    -- Raw date/time string, to be parsed during data cleaning
    UnitPrice DECIMAL(10, 4),   -- Price per single unit, allowing up to 4 decimal places for precision
    CustomerID VARCHAR(50),     -- Customer ID (often missing/null in the raw data, stored as string to handle clean cast)
    Country VARCHAR(100)        -- Country of the customer
);

-- ------------------------------------------
-- SECTION 1.2: DDL FOR CLEANED SCHEMA
-- This optimized table holds the sanitized transaction data.
-- ------------------------------------------

-- Drop the cleaned table if it already exists
DROP TABLE IF EXISTS cleaned_online_retail;

CREATE TABLE cleaned_online_retail (
    InvoiceNo VARCHAR(50) NOT NULL,
    StockCode VARCHAR(50) NOT NULL,
    Description VARCHAR(255) NOT NULL,
    Quantity INT NOT NULL,
    InvoiceDate TIMESTAMP NOT NULL,  -- Casted and normalized date-time
    UnitPrice DECIMAL(10, 2) NOT NULL, -- Normalized price rounded to 2 decimal places
    CustomerID VARCHAR(50) NOT NULL,   -- Non-nullable to ensure cohort/RFM validity
    Country VARCHAR(100) NOT NULL,
    TotalAmount DECIMAL(12, 2) NOT NULL -- Calculated field (Quantity * UnitPrice) to simplify downstream BI queries
);

-- ------------------------------------------
-- SECTION 1.3: PERFORMANCE INDEXES
-- Indexes speed up queries on large datasets (500k+ rows).
-- ------------------------------------------

-- Optimize queries grouping or filtering by CustomerID (e.g., RFM, Cohorts)
CREATE INDEX idx_cleaned_customer_id ON cleaned_online_retail(CustomerID);

-- Optimize queries filtering or aggregating by date range (e.g., Monthly Revenue, Recency)
CREATE INDEX idx_cleaned_invoice_date ON cleaned_online_retail(InvoiceDate);

-- Optimize queries linking items within the same invoice (e.g., Basket Analysis)
CREATE INDEX idx_cleaned_invoice_no ON cleaned_online_retail(InvoiceNo);


-- ------------------------------------------
-- SECTION 1.4: DATA CLEANING PIPELINE
-- This script extracts, transforms, and loads (ETL) data from raw to cleaned.
-- ------------------------------------------

-- Explanation of Cleaning Criteria:
-- 1. CustomerID IS NOT NULL: Analysis of customer behavior (RFM, LTV, Retention) is impossible without CustomerID.
--    Records without IDs (guest checkouts) are discarded from the analytics dataset.
-- 2. Quantity > 0 and InvoiceNo NOT LIKE 'C%': Invoices beginning with 'C' are cancellations/returns.
--    We filter them out to establish a baseline of actual sales.
-- 3. UnitPrice > 0: Excludes free samples, bad entries, adjustments, and promotional gifts.
-- 4. Date Parsing: Handles conversion from raw string to structured TIMESTAMP.

INSERT INTO cleaned_online_retail (
    InvoiceNo,
    StockCode,
    Description,
    Quantity,
    InvoiceDate,
    UnitPrice,
    CustomerID,
    Country,
    TotalAmount
)
SELECT 
    InvoiceNo,
    StockCode,
    COALESCE(TRIM(Description), 'Unknown Product') AS Description, -- Replace blank or null descriptions
    Quantity,
    -- DATE PARSING COMPATIBILITY NOTE:
    -- Depending on your RDBMS, choose the appropriate date conversion function:
    -- PostgreSQL: TO_TIMESTAMP(InvoiceDate, 'MM/DD/YYYY HH24:MI') or CAST(InvoiceDate AS TIMESTAMP)
    -- MySQL: STR_TO_DATE(InvoiceDate, '%m/%d/%Y %H:%i')
    -- Below, we use standard CAST which works if the raw string is already in standard ISO format (YYYY-MM-DD HH:MM:SS),
    -- or we can use the explicit database-specific functions. We show the PostgreSQL syntax as default here:
    CAST(InvoiceDate AS TIMESTAMP) AS InvoiceDate,
    ROUND(UnitPrice, 2) AS UnitPrice,
    TRIM(CustomerID) AS CustomerID,
    TRIM(Country) AS Country,
    ROUND(Quantity * UnitPrice, 2) AS TotalAmount
FROM 
    raw_online_retail
WHERE 
    CustomerID IS NOT NULL 
    AND TRIM(CustomerID) <> ''
    AND TRIM(CustomerID) <> 'NaN' -- Clean up text nulls
    AND Quantity > 0 
    AND InvoiceNo NOT LIKE 'C%' 
    AND UnitPrice > 0.00;
