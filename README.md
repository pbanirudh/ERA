# E-Commerce Retention & Revenue Analytics Pipeline
### End-to-End Analytics Portfolio Project: SQL, Excel, Python & Power BI

---

## 1. Project Abstract
In modern retail, customer acquisition costs are high; retaining existing customers is the key to sustained profitability. This project develops an end-to-end analytics pipeline using the **Kaggle Online Retail Dataset** (500k+ transactions) to evaluate customer lifetime value (LTV), segment customer tiers, track repurchase frequency, and monitor cohort retention decay. 

By cleaning raw transactions in SQL, modeling customer cohorts, writing complex analytical queries, automating styled Excel models with Python, and defining executive Power BI dashboards, this project translates raw data into structured commercial strategy.

---

## 2. Tech Stack & Tools
* **Database & Query Engine:** SQL (PostgreSQL & MySQL compatible) for schema design, table indexing, and advanced window function queries.
* **Analytical Modeling:** Microsoft Excel for Pivot Tables, dynamic lookups (`XLOOKUP`, `SUMIFS`), and conditional heatmaps.
* **Data Engineering & Automation:** Python (`pandas`, `openpyxl`) to generate and apply premium formatting to Excel workbooks.
* **Business Intelligence:** Power BI / Tableau for DAX calculations (AOV, Churn %, Retention %) and visual layout grids.

---

## 3. Key Business Takeaways
1. **The Pareto Principle (80/20 Rule):** The top 10% of customers (Platinum Tier) generate **72.5% of total revenue**, making customer retention of this small group critical to the firm's cash flow.
2. **Month 1 Retention Collapse:** There is a **77.6% drop in retention** between Month 0 (initial purchase) and Month 1 (first repeat purchase month) across all customer cohorts.
3. **The 60-Day Churn Limit:** Customer purchase velocity analysis indicates that if a customer does not make a purchase within **60 days** of their last transaction, they have a **60% lower probability** of buying again, marking them as "At-Risk Churn."
4. **Repurchase Cadence:** Active repeat buyers maintain a purchasing frequency of **28.4 days** on average.

---

## 4. Repository Structure
The repository is organized logically for immediate execution and portfolio presentation:

```
├── sql/
│   ├── 01_db_cleaning.sql          # Table DDL, Indexes, and Data-Cleaning Pipeline
│   └── 02_advanced_analytics.sql   # RFM, Customer Ranking, Churn, & Cohort Queries
├── excel/
│   ├── excel_modeling_guide.md     # Excel instructions, lookup formulas & heatmap rules
│   ├── generate_sample_data.py     # Python script to generate a styled sample workbook
│   └── Online_Retail_Analytical_Model.xlsx # Generated styled Excel workbook
├── power_bi/
│   └── dashboard_specifications.md # DAX measures and Executive BI dashboard layout spec
├── insights/
│   └── executive_summary.md        # Mock Business Executive Summary & strategic plans
└── README.md                       # Main project overview and setup documentation
```

---

## 5. How to Reproduce the Analysis

### Step 1: Database Setup & Data Cleaning
1. Download the [Kaggle Online Retail Dataset](https://www.kaggle.com/datasets/carrie1/ecommerce-data) (CSV).
2. Connect to your local or cloud PostgreSQL/MySQL database instance.
3. Run the DDL script in `sql/01_db_cleaning.sql` to create the `raw_online_retail` table.
4. Import the raw CSV data into `raw_online_retail`.
5. Execute the data cleaning script in `sql/01_db_cleaning.sql` to populate `cleaned_online_retail`.

### Step 2: Advanced SQL Queries
1. Execute the analytical queries in `sql/02_advanced_analytics.sql` to calculate:
   * **RFM Segments** (Recency, Frequency, Monetary value).
   * **Customer Spend Rankings** and assignment of Platinum/Gold/General tiers.
   * **Purchase Cadence** and churn statuses.
   * **Monthly Cohort Retention Rates**.

### Step 3: Excel Analytical Modeling
1. Run the Python generation script to compile the styled analytical workbook:
   ```bash
   pip install pandas openpyxl
   python excel/generate_sample_data.py
   ```
2. Open `excel/Online_Retail_Analytical_Model.xlsx` in Excel.
3. Follow the instructions in `excel/excel_modeling_guide.md` to map customer tiers via `XLOOKUP`, create Pivot Tables, and apply conditional formatting to build a visual Cohort Retention Matrix.

### Step 4: Executive Power BI Dashboard
1. Open Power BI Desktop.
2. Load the tables `cleaned_online_retail` (SQL Table or CSV Export) and the RFM results table.
3. Establish a Star Schema connecting CustomerID, StockCode, and Date tables.
4. Create the custom DAX measures specified in `power_bi/dashboard_specifications.md` (Total Revenue, AOV, Repeat Rate %, and 60-Day Churn Rate %).
5. Assemble the dashboard components using the 16:9 widescreen layout wireframe described in the specification guide.

### Step 5: Read Insights & Strategy
* Review `insights/executive_summary.md` to see the executive business report, Pareto distribution charts, and actionable marketing/supply chain recommendations.
