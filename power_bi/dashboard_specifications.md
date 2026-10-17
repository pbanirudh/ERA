# Executive Power BI Dashboard Specifications
### Online Retail Analytics: Revenue Concentration, Churn & Cohort Retention

This document outlines the complete **Star Schema data model**, **DAX Measure Catalog**, and **Visual Layout Grid** to build an interactive, presentation-ready Executive BI Dashboard in Power BI.

---

## 1. Data Model Architecture (Star Schema)

The tables in the `power_bi/` directory form a high-performance Star Schema:

```
          +--------------------+
          |    Dim_Calendar    |
          |--------------------|
          | Date (PK)          |
          +---------+----------+
                    | 1
                    |
                    | *
+-------------------+---+      * +--------------------+
|   Fact_Transactions   +--------+   Dim_Customers    |
|-----------------------|        |--------------------|
| InvoiceNo             |        | CustomerID (PK)    |
| StockCode (FK)        |        | Country            |
| CustomerID (FK)       |        | CustomerSegment    |
| InvoiceDate (FK)      |        | CustomerRank       |
| Quantity              |        | ChurnRiskStatus    |
| UnitPrice             |        | ChurnProbability   |
| TotalAmount           |        | RiskTier           |
+-----------+-----------+        +--------------------+
            | *
            |
            | 1
+-----------+-----------+
|     Dim_Products      |
|-----------------------|
| StockCode (PK)        |
| Description           |
| AvgUnitPrice          |
+-----------------------+
```

### Relationships to Establish in Power BI:
1. `Fact_Transactions[CustomerID]` $\rightarrow$ `Dim_Customers[CustomerID]` (Many-to-One `* : 1`, Single direction)
2. `Fact_Transactions[StockCode]` $\rightarrow$ `Dim_Products[StockCode]` (Many-to-One `* : 1`, Single direction)
3. `Fact_Transactions[InvoiceDate]` $\rightarrow$ `Dim_Calendar[Date]` (Many-to-One `* : 1`, Single direction)

---

## 2. Advanced DAX Measures Catalog

Create a dedicated table named `_Measures` in Power BI and add the following DAX calculations:

### 2.1 Core Revenue & Volume Measures
```dax
-- Total Revenue
Total Revenue = SUM(Fact_Transactions[TotalAmount])

-- Total Order Invoices
Total Orders = DISTINCTCOUNT(Fact_Transactions[InvoiceNo])

-- Total Distinct Customers
Total Customers = DISTINCTCOUNT(Dim_Customers[CustomerID])

-- Average Order Value (AOV)
Average Order Value = 
DIVIDE([Total Revenue], [Total Orders], 0)
```

### 2.2 Retention & Repeat Spend Measures
```dax
-- Repeat Customers (Customers with 2 or more distinct orders)
Repeat Customers = 
COUNTROWS(
    FILTER(
        VALUES(Dim_Customers[CustomerID]),
        CALCULATE(DISTINCTCOUNT(Fact_Transactions[InvoiceNo])) >= 2
    )
)

-- Repeat Customer Rate (%)
Repeat Customer Rate % = 
DIVIDE([Repeat Customers], [Total Customers], 0)

-- Repeat Customer Revenue
Repeat Customer Revenue = 
CALCULATE(
    [Total Revenue],
    FILTER(
        VALUES(Dim_Customers[CustomerID]),
        CALCULATE(DISTINCTCOUNT(Fact_Transactions[InvoiceNo])) >= 2
    )
)

-- Repeat Revenue Share % (Benchmark: 93.09%)
Repeat Revenue Share % = 
DIVIDE([Repeat Customer Revenue], [Total Revenue], 0)
```

### 2.3 Churn & Inactivity Measures
```dax
-- 60-Day Churn Rate (%)
60-Day Churn Rate % = 
VAR MaxDate = CALCULATE(MAX(Fact_Transactions[InvoiceDate]), ALL(Fact_Transactions))
VAR AtRiskCustomers = 
    CALCULATE(
        DISTINCTCOUNT(Dim_Customers[CustomerID]),
        Dim_Customers[DaysSinceLastPurchase] > 60
    )
RETURN
    DIVIDE(AtRiskCustomers, [Total Customers], 0)

-- High Risk Accounts (from ML Model)
ML High Risk Customers = 
CALCULATE(
    DISTINCTCOUNT(Dim_Customers[CustomerID]),
    Dim_Customers[RiskTier] = "High Risk (Critical Churn)"
)
```

### 2.4 Pareto Concentration Measure
```dax
-- Top 10% Spend Share % (Benchmark: 61.41%)
Top 10% Revenue Share % = 
VAR Top10Revenue = 
    CALCULATE(
        [Total Revenue],
        Dim_Customers[CustomerSegment] = "Platinum Tier (Top 10%)"
    )
RETURN
    DIVIDE(Top10Revenue, [Total Revenue], 0)
```

---

## 3. Executive Dashboard Visual Layout (16:9 Widescreen)

### Theme Palette:
* **Canvas Background:** Light gray `#F4F6F9` or Slate Dark Mode `#121620`
* **Card Fills:** Pure White `#FFFFFF` (Light) or Dark Charcoal `#1B2232` (Dark)
* **Primary Accent:** Navy Blue `#1F4E78`
* **Warning / Churn Accent:** Warm Amber / Soft Crimson `#D9534F`
* **Success Accent:** Jade Green `#28A745`

```
+---------------------------------------------------------------------------------------------------------------+
|  EXECUTIVE REVENUE & CUSTOMER RETENTION DASHBOARD           [Slicers: Country | Customer Segment | Year-Month]|
+---------------------------------------------------------------------------------------------------------------+
|  +--------------------+  +--------------------+  +--------------------+  +--------------------+  +------------+
|  | TOTAL REVENUE      |  | ACTIVE CUSTOMERS   |  | REPEAT SPEND SHARE |  | TOP 10% SHARE      |  | CHURN RATE |
|  |   £8,887,209       |  |      4,338         |  |      93.09%        |  |      61.41%        |  |   31.97%   |
|  +--------------------+  +--------------------+  +--------------------+  +--------------------+  +------------+
+---------------------------------------------------------------------------------------------------------------+
|  +----------------------------------------------+  +----------------------------------------------------------+
|  | MONTHLY REVENUE & ORDER VOLUME TREND         |  | COHORT RETENTION DECAY (MATRIX)                          |
|  | Visual: Line and Clustered Column Chart      |  | Visual: Matrix Table                                     |
|  | X-Axis: Dim_Calendar[MonthYear]              |  | Rows: Dim_Cohorts[AcquisitionMonth]                      |
|  | Column Y: [Total Revenue]                    |  | Columns: Dim_Cohorts[CohortIndex]                        |
|  | Line Y: [Total Orders]                       |  | Values: AVERAGE(Dim_Cohorts[RetentionRatePct])           |
|  | (Highlights massive Q4 holiday volume surge) |  | Conditional Formatting: Green-Yellow-White heatmap scale |
|  +----------------------------------------------+  +----------------------------------------------------------+
+---------------------------------------------------------------------------------------------------------------+
|  +---------------------------+  +---------------------------+  +----------------------------------------------+
|  | REVENUE BY CUSTOMER TIER  |  | TOP 10 VIP CUSTOMERS      |  | CHURN RISK DISTRIBUTION (ML PREDICTIONS)    |
|  | Visual: Donut Chart       |  | Visual: Bar Chart         |  | Visual: 100% Stacked Bar                     |
|  | Legend: CustomerSegment   |  | Y-Axis: CustomerID        |  | Category: CustomerSegment                    |
|  | Values: [Total Revenue]   |  | X-Axis: [Total Revenue]   |  | Legend: RiskTier (Low / Moderate / High)     |
|  | (Platinum: 61.4% share)   |  | Data Labels: £ On bars    |  | Value: Customer Count                        |
|  +---------------------------+  +---------------------------+  +----------------------------------------------+
```

---

## 4. How to Load and Build in Power BI Desktop (Quick Setup)

1. Open **Power BI Desktop**.
2. Click **Get Data** $\rightarrow$ **Text/CSV**.
3. Load the 5 files in `power_bi/`:
   * `Fact_Transactions.csv`
   * `Dim_Customers.csv`
   * `Dim_Products.csv`
   * `Dim_Calendar.csv`
   * `Dim_Cohorts.csv`
4. In the **Model view**, confirm the 1-to-many relationships link `Fact_Transactions` to `Dim_Customers`, `Dim_Products`, and `Dim_Calendar`.
5. Create a new table named `_Measures` and paste the DAX measures from Section 2.
6. Assemble the visuals matching the wireframe layout in Section 3.
