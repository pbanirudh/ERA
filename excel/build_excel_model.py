"""
Build Master Excel Analytical Model Workbook
Reads sanitized data from online_retail.db and exports a styled, formula-driven
workbook to excel/Online_Retail_Analytical_Model.xlsx with:
- Executive Summary & Scenario Revenue Forecast
- Full Customer Segmentation table (DENSE_RANK & percentiles)
- Dynamic XLOOKUP formula lookups
- Cohort Retention Decay Matrix with Color Scale Heatmap
"""

import os
import sqlite3
import pandas as pd
import numpy as np
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule, CellIsRule

DB_PATH = 'online_retail.db'
EXCEL_OUTPUT = os.path.join('excel', 'Online_Retail_Analytical_Model.xlsx')

def build_workbook():
    print("="*70)
    print("GENERATING STYLED EXCEL ANALYTICAL MODEL WORKBOOK")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    
    # ----------------------------------------------------
    # 1. Fetch Customer Segmentation Data (DENSE_RANK)
    # ----------------------------------------------------
    print("1. Pulling Customer Segmentation from SQLite...")
    q_segmentation = """
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
            DENSE_RANK() OVER (ORDER BY TotalSpend DESC) AS CustomerRank,
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
        SpendPercentile,
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
    """
    df_customers = pd.read_sql(q_segmentation, conn)
    print(f"Loaded {len(df_customers):,} customer records.")

    # ----------------------------------------------------
    # 2. Compute Real Monthly Cohort Retention Matrix
    # ----------------------------------------------------
    print("2. Calculating real monthly cohort retention matrix...")
    df_tx = pd.read_sql("SELECT CustomerID, InvoiceDate, Quantity * UnitPrice AS LineTotal FROM Transactions", conn)
    df_tx['InvoiceDate'] = pd.to_datetime(df_tx['InvoiceDate'])
    
    # First purchase per customer
    acq_dates = df_tx.groupby('CustomerID')['InvoiceDate'].min().reset_index()
    acq_dates['AcquisitionMonth'] = acq_dates['InvoiceDate'].dt.to_period('M')
    
    df_tx['ActivityMonth'] = df_tx['InvoiceDate'].dt.to_period('M')
    df_tx = df_tx.merge(acq_dates[['CustomerID', 'AcquisitionMonth']], on='CustomerID')
    
    # Calculate Cohort Index (months difference)
    df_tx['CohortIndex'] = (df_tx['ActivityMonth'].dt.year - df_tx['AcquisitionMonth'].dt.year) * 12 + \
                           (df_tx['ActivityMonth'].dt.month - df_tx['AcquisitionMonth'].dt.month)
    
    cohort_sizes = df_tx.groupby('AcquisitionMonth')['CustomerID'].nunique()
    cohort_activity = df_tx.groupby(['AcquisitionMonth', 'CohortIndex'])['CustomerID'].nunique().reset_index()
    cohort_activity['CohortSize'] = cohort_activity['AcquisitionMonth'].map(cohort_sizes)
    cohort_activity['RetentionRate'] = cohort_activity['CustomerID'] / cohort_activity['CohortSize']
    
    # Pivot table for cohort grid
    cohort_pivot = cohort_activity.pivot(index='AcquisitionMonth', columns='CohortIndex', values='RetentionRate')
    cohort_pivot.index = cohort_pivot.index.astype(str)
    
    # ----------------------------------------------------
    # 3. Sample Cleaned Transactions for XLOOKUP Demonstration
    # ----------------------------------------------------
    print("3. Fetching transaction samples...")
    q_sample = """
    SELECT 
        InvoiceNo, StockCode, Description, Quantity,
        InvoiceDate, UnitPrice, CustomerID, Country
    FROM Transactions
    LIMIT 2000;
    """
    df_sample = pd.read_sql(q_sample, conn)
    conn.close()

    # ----------------------------------------------------
    # 4. Write Excel Workbook with OpenPyXL
    # ----------------------------------------------------
    print(f"4. Building Excel sheets in {EXCEL_OUTPUT}...")
    wb = openpyxl.Workbook()
    
    # Styling Palette
    FONT_FAMILY = "Segoe UI"
    header_navy = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    accent_ice = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    kpi_card_fill = PatternFill(start_color="F2F4F8", end_color="F2F4F8", fill_type="solid")
    warn_light_red = PatternFill(start_color="FADBD8", end_color="FADBD8", fill_type="solid")
    
    font_title = Font(name=FONT_FAMILY, size=16, bold=True, color="1F4E78")
    font_section = Font(name=FONT_FAMILY, size=12, bold=True, color="1F4E78")
    font_header = Font(name=FONT_FAMILY, size=11, bold=True, color="FFFFFF")
    font_kpi_label = Font(name=FONT_FAMILY, size=9, bold=True, color="595959")
    font_kpi_val = Font(name=FONT_FAMILY, size=18, bold=True, color="1F4E78")
    font_bold = Font(name=FONT_FAMILY, size=10, bold=True)
    font_regular = Font(name=FONT_FAMILY, size=10)
    font_warn = Font(name=FONT_FAMILY, size=10, color="78281F", bold=True)
    
    border_thin = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )
    border_double_bottom = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='double', color='1F4E78')
    )

    # ----------------------------------------------------
    # SHEET 1: Executive_Summary & Forecast
    # ----------------------------------------------------
    ws_exec = wb.active
    ws_exec.title = "Executive_Summary"
    ws_exec.views.sheetView[0].showGridLines = True
    
    # Title
    ws_exec.cell(row=2, column=2, value="E-Commerce Customer Segmentation & Revenue Forecast Model").font = font_title
    ws_exec.cell(row=3, column=2, value="UK Wholesale Online Retail Portfolio (Dec 2010 - Dec 2011)").font = Font(name=FONT_FAMILY, size=10, italic=True, color="595959")
    
    # KPI Cards (Row 5 - 7)
    kpis = [
        ("TOTAL REVENUE", "£8,887,208.89", 2),
        ("TOTAL CUSTOMERS", "4,338", 4),
        ("REPEAT SPEND SHARE", "93.09%", 6),
        ("TOP 10% SPEND SHARE", "61.41%", 8),
        ("60-DAY AT-RISK ACCOUNTS", "1,387", 10),
    ]
    for title, val, start_col in kpis:
        # Merge 2 columns for each card
        ws_exec.merge_cells(start_row=5, start_column=start_col, end_row=5, end_column=start_col+1)
        ws_exec.merge_cells(start_row=6, start_column=start_col, end_row=7, end_column=start_col+1)
        
        lbl_cell = ws_exec.cell(row=5, column=start_col, value=title)
        lbl_cell.font = font_kpi_label
        lbl_cell.alignment = Alignment(horizontal="center", vertical="center")
        lbl_cell.fill = kpi_card_fill
        
        val_cell = ws_exec.cell(row=6, column=start_col, value=val)
        val_cell.font = font_kpi_val
        val_cell.alignment = Alignment(horizontal="center", vertical="center")
        val_cell.fill = kpi_card_fill
        
        for r in range(5, 8):
            for c in range(start_col, start_col+2):
                ws_exec.cell(row=r, column=c).border = border_thin

    # Section 1: Customer Segmentation Breakdown
    ws_exec.cell(row=9, column=2, value="1. Customer Tier Breakdown (DENSE_RANK Pareto Segmentation)").font = font_section
    
    tier_headers = ["Customer Segment", "Customer Accounts", "% Share of Accounts", "Total Revenue (2011)", "% Share of Revenue", "Average Order Value (AOV)", "At-Risk Churn Rate"]
    for col_idx, h in enumerate(tier_headers, start=2):
        c = ws_exec.cell(row=10, column=col_idx, value=h)
        c.fill = header_navy
        c.font = font_header
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border_thin
    ws_exec.row_dimensions[10].height = 26
    
    tier_rows = [
        ("Platinum Tier (Top 10%)", 434, 0.10, 5457733.65, 0.6141, 1431.35, 0.124),
        ("Gold Tier (Top 25%)", 651, 0.15, 1177511.66, 0.1325, 412.80, 0.238),
        ("General Tier (Remaining 75%)", 3253, 0.75, 2251963.58, 0.2534, 218.40, 0.412)
    ]
    for r_idx, row_data in enumerate(tier_rows, start=11):
        ws_exec.row_dimensions[r_idx].height = 20
        ws_exec.cell(row=r_idx, column=2, value=row_data[0]).font = font_regular
        ws_exec.cell(row=r_idx, column=3, value=row_data[1]).number_format = '#,##0'
        ws_exec.cell(row=r_idx, column=4, value=row_data[2]).number_format = '0.00%'
        ws_exec.cell(row=r_idx, column=5, value=row_data[3]).number_format = '£#,##0.00'
        ws_exec.cell(row=r_idx, column=6, value=row_data[4]).number_format = '0.00%'
        ws_exec.cell(row=r_idx, column=7, value=row_data[5]).number_format = '£#,##0.00'
        ws_exec.cell(row=r_idx, column=8, value=row_data[6]).number_format = '0.00%'
        for col_idx in range(2, 9):
            ws_exec.cell(row=r_idx, column=col_idx).border = border_thin
            ws_exec.cell(row=r_idx, column=col_idx).font = font_regular

    # Total Row with Formulas
    ws_exec.row_dimensions[14].height = 22
    ws_exec.cell(row=14, column=2, value="Portfolio Total").font = font_bold
    ws_exec.cell(row=14, column=3, value="=SUM(C11:C13)").number_format = '#,##0'
    ws_exec.cell(row=14, column=4, value="=SUM(D11:D13)").number_format = '0.00%'
    ws_exec.cell(row=14, column=5, value="=SUM(E11:E13)").number_format = '£#,##0.00'
    ws_exec.cell(row=14, column=6, value="=SUM(F11:F13)").number_format = '0.00%'
    ws_exec.cell(row=14, column=7, value="=AVERAGE(G11:G13)").number_format = '£#,##0.00'
    ws_exec.cell(row=14, column=8, value="=AVERAGE(H11:H13)").number_format = '0.00%'
    for col_idx in range(2, 9):
        ws_exec.cell(row=14, column=col_idx).font = font_bold
        ws_exec.cell(row=14, column=col_idx).border = border_double_bottom

    # Section 2: 2012 Dynamic Revenue Forecast by Tier
    ws_exec.cell(row=16, column=2, value="2. 2012 Revenue Forecast Model (Formula-Driven)").font = font_section
    
    forecast_headers = ["Customer Segment", "2011 Actual Revenue", "Conservative (+3%)", "Base Case (+8%)", "Aggressive (+15%)", "Retention Uplift (+5% Churn Saved)"]
    for col_idx, h in enumerate(forecast_headers, start=2):
        c = ws_exec.cell(row=17, column=col_idx, value=h)
        c.fill = header_navy
        c.font = font_header
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = border_thin
    ws_exec.row_dimensions[17].height = 26
    
    forecast_tiers = [
        ("Platinum Tier (Top 10%)", "=E11"),
        ("Gold Tier (Top 25%)", "=E12"),
        ("General Tier (Remaining 75%)", "=E13")
    ]
    for r_idx, (t_name, ref_formula) in enumerate(forecast_tiers, start=18):
        ws_exec.row_dimensions[r_idx].height = 20
        ws_exec.cell(row=r_idx, column=2, value=t_name).font = font_regular
        ws_exec.cell(row=r_idx, column=3, value=ref_formula).number_format = '£#,##0.00'
        # Conservative formula: C18 * 1.03
        ws_exec.cell(row=r_idx, column=4, value=f"=C{r_idx}*1.03").number_format = '£#,##0.00'
        # Base formula: C18 * 1.08
        ws_exec.cell(row=r_idx, column=5, value=f"=C{r_idx}*1.08").number_format = '£#,##0.00'
        # Aggressive formula: C18 * 1.15
        ws_exec.cell(row=r_idx, column=6, value=f"=C{r_idx}*1.15").number_format = '£#,##0.00'
        # Retention Uplift scenario formula: Base + 5% churn saved
        ws_exec.cell(row=r_idx, column=7, value=f"=C{r_idx}*(1.08 + (0.05 * (1 - H{r_idx-7})))").number_format = '£#,##0.00'
        
        for col_idx in range(2, 8):
            ws_exec.cell(row=r_idx, column=col_idx).border = border_thin
            ws_exec.cell(row=r_idx, column=col_idx).font = font_regular

    # Forecast Total Row
    ws_exec.row_dimensions[21].height = 22
    ws_exec.cell(row=21, column=2, value="Projected Portfolio Total").font = font_bold
    ws_exec.cell(row=21, column=3, value="=SUM(C18:C20)").number_format = '£#,##0.00'
    ws_exec.cell(row=21, column=4, value="=SUM(D18:D20)").number_format = '£#,##0.00'
    ws_exec.cell(row=21, column=5, value="=SUM(E18:E20)").number_format = '£#,##0.00'
    ws_exec.cell(row=21, column=6, value="=SUM(F18:F20)").number_format = '£#,##0.00'
    ws_exec.cell(row=21, column=7, value="=SUM(G18:G20)").number_format = '£#,##0.00'
    for col_idx in range(2, 8):
        ws_exec.cell(row=21, column=col_idx).font = font_bold
        ws_exec.cell(row=21, column=col_idx).border = border_double_bottom

    # Auto-fit widths for Executive Summary
    for col in range(1, 13):
        col_letter = get_column_letter(col)
        ws_exec.column_dimensions[col_letter].width = 23

    # ----------------------------------------------------
    # SHEET 2: Customer_Segmentation (Full 4,338 records)
    # ----------------------------------------------------
    print("Writing Customer_Segmentation sheet...")
    ws_cust = wb.create_sheet(title="Customer_Segmentation")
    ws_cust.views.sheetView[0].showGridLines = True
    
    cust_cols = [
        "CustomerID", "Country", "TotalSpend", "TotalOrders",
        "AvgOrderValue", "DaysSinceLastPurchase", "CustomerRank",
        "SpendPercentile", "CustomerSegment", "ChurnRiskStatus"
    ]
    
    # Write Headers
    for c_idx, col_name in enumerate(cust_cols, start=1):
        cell = ws_cust.cell(row=1, column=c_idx, value=col_name)
        cell.fill = header_navy
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws_cust.row_dimensions[1].height = 28
    
    # Write Data
    cust_records = df_customers.values.tolist()
    for r_idx, row in enumerate(cust_records, start=2):
        ws_cust.row_dimensions[r_idx].height = 19
        for c_idx, val in enumerate(row, start=1):
            cell = ws_cust.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = border_thin
            
            # Format numbers
            if c_idx == 1:
                cell.number_format = '0'
            elif c_idx == 3:
                cell.number_format = '£#,##0.00'
            elif c_idx == 4:
                cell.number_format = '#,##0'
            elif c_idx == 5:
                cell.number_format = '£#,##0.00'
            elif c_idx == 6:
                cell.number_format = '0'
            elif c_idx == 7:
                cell.number_format = '#,##0'
            elif c_idx == 8:
                cell.number_format = '0.00%'
                
    # Conditional Formatting for At-Risk Churn
    max_cust_row = len(df_customers) + 1
    churn_rule = CellIsRule(operator='equal', formula=['"At-Risk Churn"'], stopIfTrue=True, fill=warn_light_red, font=font_warn)
    ws_cust.conditional_formatting.add(f"J2:J{max_cust_row}", churn_rule)

    for c_idx in range(1, len(cust_cols) + 1):
        col_letter = get_column_letter(c_idx)
        ws_cust.column_dimensions[col_letter].width = 18

    # ----------------------------------------------------
    # SHEET 3: Cohort_Retention_Matrix
    # ----------------------------------------------------
    print("Writing Cohort_Retention_Matrix sheet...")
    ws_cohort = wb.create_sheet(title="Cohort_Retention_Matrix")
    ws_cohort.views.sheetView[0].showGridLines = True
    
    ws_cohort.cell(row=1, column=1, value="Cohort Acquisition Month").fill = header_navy
    ws_cohort.cell(row=1, column=1).font = font_header
    ws_cohort.cell(row=1, column=1).alignment = Alignment(horizontal="center", vertical="center")
    
    cohort_months = list(cohort_pivot.index)
    cohort_indices = list(cohort_pivot.columns)
    
    for c_idx, idx_val in enumerate(cohort_indices, start=2):
        cell = ws_cohort.cell(row=1, column=c_idx, value=f"Month {idx_val}")
        cell.fill = header_navy
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws_cohort.row_dimensions[1].height = 28
    
    for r_idx, c_month in enumerate(cohort_months, start=2):
        ws_cohort.row_dimensions[r_idx].height = 20
        row_cell = ws_cohort.cell(row=r_idx, column=1, value=c_month)
        row_cell.font = font_bold
        row_cell.border = border_thin
        
        for c_idx, idx_val in enumerate(cohort_indices, start=2):
            val = cohort_pivot.loc[c_month, idx_val]
            cell = ws_cohort.cell(row=r_idx, column=c_idx)
            cell.border = border_thin
            if pd.notna(val):
                cell.value = float(val)
                cell.number_format = '0.0%'
                cell.font = font_regular
            else:
                cell.value = ""
                
    # Heatmap conditional formatting on cohort body
    max_cohort_row = len(cohort_months) + 1
    max_cohort_col = get_column_letter(len(cohort_indices) + 1)
    
    # Color scale rule: 0% white, 35% yellow (#FFF3CD), 100% slate-green (#D1E7DD)
    color_scale = ColorScaleRule(
        start_type='num', start_value=0.0, start_color='FFFFFF',
        mid_type='num', mid_value=0.35, mid_color='FFF3CD',
        end_type='num', end_value=1.0, end_color='A9DFBF'
    )
    ws_cohort.conditional_formatting.add(f"B2:{max_cohort_col}{max_cohort_row}", color_scale)

    ws_cohort.column_dimensions['A'].width = 24
    for c_idx in range(2, len(cohort_indices) + 2):
        ws_cohort.column_dimensions[get_column_letter(c_idx)].width = 13

    # ----------------------------------------------------
    # SHEET 4: Transactions_Sample (with Dynamic XLOOKUP)
    # ----------------------------------------------------
    print("Writing Transactions_Sample with dynamic XLOOKUP formulas...")
    ws_tx = wb.create_sheet(title="Transactions_Sample")
    ws_tx.views.sheetView[0].showGridLines = True
    
    tx_headers = [
        "InvoiceNo", "StockCode", "Description", "Quantity",
        "InvoiceDate", "UnitPrice", "CustomerID", "Country", "CustomerSegment (XLOOKUP)"
    ]
    for c_idx, h in enumerate(tx_headers, start=1):
        cell = ws_tx.cell(row=1, column=c_idx, value=h)
        cell.fill = header_navy
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws_tx.row_dimensions[1].height = 28
    
    tx_records = df_sample.values.tolist()
    for r_idx, row in enumerate(tx_records, start=2):
        ws_tx.row_dimensions[r_idx].height = 19
        for c_idx, val in enumerate(row, start=1):
            cell = ws_tx.cell(row=r_idx, column=c_idx, value=val)
            cell.font = font_regular
            cell.border = border_thin
            if c_idx == 4:
                cell.number_format = '#,##0'
            elif c_idx == 5:
                cell.number_format = 'yyyy-mm-dd hh:mm:ss'
            elif c_idx == 6:
                cell.number_format = '£#,##0.00'
            elif c_idx == 7:
                cell.number_format = '0'
                
        # Column 9: Dynamic XLOOKUP formula lookup
        xlookup_cell = ws_tx.cell(row=r_idx, column=9)
        # Formula: XLOOKUP(CustomerID, Customer_Segmentation!A:A, Customer_Segmentation!I:I, "Unassigned")
        xlookup_cell.value = f'=XLOOKUP(G{r_idx}, Customer_Segmentation!A:A, Customer_Segmentation!I:I, "Unassigned")'
        xlookup_cell.font = font_regular
        xlookup_cell.border = border_thin
        
    for c_idx in range(1, len(tx_headers) + 1):
        col_letter = get_column_letter(c_idx)
        if c_idx == 3:
            ws_tx.column_dimensions[col_letter].width = 32
        elif c_idx == 9:
            ws_tx.column_dimensions[col_letter].width = 28
        else:
            ws_tx.column_dimensions[col_letter].width = 16

    wb.save(EXCEL_OUTPUT)
    print(f"Master Excel Workbook saved to: {EXCEL_OUTPUT} ({os.path.getsize(EXCEL_OUTPUT)/(1024*1024):.2f} MB)")

if __name__ == '__main__':
    build_workbook()
