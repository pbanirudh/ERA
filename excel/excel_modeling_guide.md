# Excel Analytical Modeling Guide
### Online Retail E-Commerce Analytics Project

This guide provides step-by-step instructions to import, model, and visualize the cleaned retail dataset using Microsoft Excel. It covers Power Query data loading, Pivot Table generation, advanced dynamic formulas (`XLOOKUP`, `SUMIFS`), and Cohort Heatmap conditional formatting.

---

## 1. Data Ingestion & Setup (Power Query)
Before building formulas, load the cleaned dataset into Excel using Power Query to maintain data types and connection parameters:

1. Open a blank workbook in Excel.
2. Navigate to the **Data** tab -> **Get Data** -> **From File** -> **From Text/CSV** (or **From Database** if connecting directly to PostgreSQL/MySQL).
3. Select your cleaned data export (e.g., `cleaned_online_retail.csv`).
4. Click **Transform Data** to open the Power Query Editor.
5. Verify column data types:
   - `InvoiceNo`, `StockCode`, `Description`, `CustomerID`, `Country` -> **Text**
   - `Quantity` -> **Whole Number**
   - `InvoiceDate` -> **Date/Time**
   - `UnitPrice`, `TotalAmount` -> **Decimal Number (Currency)**
6. Click **Close & Load To...** -> Select **Table** and load to a sheet named `CleanedData`. Excel will create a structured table named `CleanedData` by default.

---

## 2. Dynamic Excel Formulas
Use these formulas in your analytical sheets to perform lookup matching and dynamic aggregation.

### 2.1 mapping Customer Tiers with XLOOKUP
If you have an RFM summary table (imported from SQL as `RFM_Table`) and want to map customer tiers directly onto your raw transactions in `CleanedData`, add a new column named `CustomerSegment` and enter:

```excel
=XLOOKUP([@CustomerID], RFM_Table[CustomerID], RFM_Table[CustomerSegment], "Guest Check-Out", 0, 1)
```

**Formula breakdown:**
* `[@CustomerID]`: Lookup value in the current transaction row.
* `RFM_Table[CustomerID]`: Lookup array containing unique Customer IDs.
* `RFM_Table[CustomerSegment]`: Return array containing the tier labels (Platinum, Gold, General).
* `"Guest Check-Out"`: Default value if the lookup returns an error (no customer matching).
* `0`: Exact match.
* `1`: Search first-to-last.

### 2.2 Dynamic aggregation with SUMIFS
To calculate the total spend of a specific customer in a custom formula-driven KPI card:

```excel
=SUMIFS(CleanedData[TotalAmount], CleanedData[CustomerID], H2)
```

To calculate the total revenue generated in a specific Country for a specific month (e.g., "United Kingdom", Dec 2011):

```excel
=SUMIFS(CleanedData[TotalAmount], CleanedData[Country], "United Kingdom", CleanedData[InvoiceDate], ">=2011-12-01", CleanedData[InvoiceDate], "<=2011-12-31")
```

---

## 3. Dynamic Pivot Tables
Pivot Tables are essential for aggregating hundreds of thousands of retail transactions instantly.

### 3.1 Monthly Revenue Trends
1. Select any cell inside the `CleanedData` table.
2. Go to **Insert** -> **PivotTable** -> Load into a new worksheet named `Monthly_Revenue`.
3. Drag **InvoiceDate** into the **Rows** area.
   * *Note: Excel will automatically group this into Years, Quarters, and Months. Drag Quarters out of the Rows area to keep just Years and Months.*
4. Drag **TotalAmount** into the **Values** area.
   * Click the drop-down on `Sum of TotalAmount` -> **Value Field Settings** -> Set name to `Total Revenue` -> Click **Number Format** -> Select **Currency ($)** with 2 decimal places.
5. Drag **Country** into the **Filters** area to allow dynamic region slicing.
6. Insert a chart: Go to **PivotTable Analyze** -> **PivotChart** -> Select **Line Chart with Markers** to show month-over-month trend.

### 3.2 Cohort Retention Matrix (Grid)
To build a classic cohort retention matrix showing customer decay over time:

1. Insert a new Pivot Table from the `cleaned_cohort_retention_data` SQL output.
2. Drag **AcquisitionMonth** (the cohort start month) into the **Rows** area.
3. Drag **CohortIndex** (number of months elapsed) into the **Columns** area.
4. Drag **CustomerID** (Count Distinct) or **RetentionRatePercent** (Average) into the **Values** area.
   * *If using Retained Customers count:* Set Value Field Settings to **Distinct Count**.
   * *If using Retention Rate:* Set Value Field Settings to **Average**, and change the format to **Percentage (0.00%)**.

---

## 4. Conditional Formatting Rules

To make the Cohort Retention Grid immediately interpretable for executives, apply color scale heatmaps:

### 4.1 Cohort Retention Decay Heatmap
1. Highlight all values inside the Pivot Table body (excluding the Row Totals and Column Totals).
2. Go to **Home** -> **Conditional Formatting** -> **Color Scales**.
3. Select the **Green-Yellow-Red** color scale.
4. To refine the color rules: Go to **Conditional Formatting** -> **Manage Rules** -> Edit the color scale:
   * Change **Minimum** to a light red color (hex: `#F8D7DA`) or white.
   * Change **Midpoint** (50% retention) to yellow (hex: `#FFF3CD`).
   * Change **Maximum** (100% retention at Cohort Month 0) to a deep slate/blue-green (hex: `#D1E7DD` or a rich green).
   * This displays a smooth gradient showing customer retention dropping off over time.

### 4.2 Highlighting Churn-Risk Segments
To flag customer groups with high churn risk in your master customer sheet:
1. Highlight the `DaysSinceLastPurchase` column in your customer dashboard table.
2. Go to **Home** -> **Conditional Formatting** -> **New Rule**.
3. Select **Format only cells that contain**.
4. Set Cell Value to: **Greater than** -> `60`.
5. Click **Format...** -> Go to **Fill** tab -> Select a light warning red (hex: `#FADBD8`) and dark red text (hex: `#78281F`).
6. Click **OK**. Customers who have been inactive for over 60 days will now stand out.
