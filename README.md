# Executive Retail Analytics & Churn Intelligence Platform
### Enterprise Analytics Dashboard • FastAPI, SQLite, XGBoost ML, Data Studio & Google Gemini AI

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%203-003B57?logo=sqlite)](https://www.sqlite.org/)
[![XGBoost](https://img.shields.io/badge/ML%20Engine-XGBoost-EB8E24)](https://xgboost.readthedocs.io/)
[![Google Gemini](https://img.shields.io/badge/AI%20Advisor-Google%20Gemini-4285F4?logo=google)](https://ai.google.dev/)
[![Status](https://img.shields.io/badge/Status-Live%20Ready-success)](#)

---

## 1. Executive Platform Overview

The **Executive Retail Analytics & Churn Intelligence Platform** is an enterprise-grade, full-stack decision support system built on **392,692 retail transactions** (£8.89M GMV). It combines real-time SQL analytics, machine learning churn hazard modeling with XGBoost, an interactive Data Studio for ingesting new datasets, and an **AI Executive Advisor** that explains analytical results and prescribes prioritized retention playbooks.

### Multi-View Navigation Suite:
1. 📊 **Executive Overview:** 5 executive KPI cards, dynamic revenue trends, Pareto customer tier distribution, empirical repurchase cadence, and interactive 2012 revenue scenario simulator.
2. 👤 **Customer 360:** Individual account dossier with dynamic RFM scores (1–5), XGBoost churn probability, lifetime order timeline, top purchased SKUs, and one-click AI retention strategy generation.
3. 🧬 **Cohort Studio:** Dynamic acquisition-month cohort matrix tracking Month-0 to Month-12 retention decay, cohort revenue volume, and active customer counts.
4. 🎯 **ML Churn Radar & VIP Rescue:** Machine learning churn classification (Low, Moderate, Critical Risk) with an actionable VIP Rescue Center and CSV export.
5. 📁 **Data Studio & Ingestion Engine:** Drag-and-drop CSV/Excel upload with automated data cleaning, manual transaction logging, record deletion, and one-click baseline restoration.
6. 🔍 **Interactive SQL Sandbox:** In-browser query editor preloaded with 5 analytical presets and live SQLite execution plans (`EXPLAIN QUERY PLAN`).
7. 🤖 **AI Executive Advisor & Strategist:** Grounded in live database telemetry, powered by **Google Gemini LLM** (with built-in Chief Analytics Officer reasoning engine fallback) to deliver data-backed executive briefings, root-cause diagnostics, and prioritized P0/P1/P2 action plans.

---

## 2. Key Empirical Insights

* **The Pareto Asymmetry (80/20 Rule):** The top 10% Platinum tier generates **72.5% of total gross revenue** (£6.4M), presenting severe customer concentration risk.
* **Repeat Customer Value:** Repeat buyers make up 65.6% of the customer base but drive **93.1% of cumulative GMV**.
* **The Month-1 Cohort Chasm:** There is a **77.6% drop in retention** between Month 0 (initial purchase) and Month 1 across all historical cohorts.
* **The 60-Day Churn Limit:** Over 79% of all repeat orders occur within 60 days. Inactivity exceeding 60 days results in a **60% lower probability** of repurchasing.
* **Average Wholesale Cadence:** Repeat commercial accounts repurchase on an average cycle of **28.4 days**.

---

## 3. Quickstart & Running the Application

### Prerequisites
* Python 3.9+ installed
* Git

### Installation & Launch
```bash
# 1. Clone repository
git clone https://github.com/pbanirudh/Executive-Retail-Analytics-Churn-Intelligence-Platform.git
cd Executive-Retail-Analytics-Churn-Intelligence-Platform

# 2. Install dependencies
pip install fastapi uvicorn pandas numpy scikit-learn xgboost openpyxl google-generativeai

# 3. Launch live analytics server
python -m uvicorn app.server:app --reload --port 8000
```

Open your browser to: **`http://localhost:8000`**

---

## 4. How to Use the Application

### 📁 Uploading New Data (Data Studio)
1. Navigate to the **"📁 Data Studio & Upload"** tab in the top navigation.
2. Drag and drop any retail CSV or Excel (`.xlsx`) file into the upload zone (or click to browse).
3. Select your ingestion mode:
   - **Append Mode (default):** Cleans and inserts records into the existing database.
   - **Replace Mode:** Flushes previous data and initializes a fresh database with your file.
4. Click **"📤 Upload & Clean Dataset"**. The platform automatically:
   - Filters cancelled orders (`InvoiceNo` starting with `C`)
   - Eliminates null or guest `CustomerID` records
   - Strips non-positive prices and quantities
   - Deduplicates identical line-items
   - Re-indexes the SQLite database
   - Automatically re-scores all customers through the ML churn engine!
5. View recent transactions in the table below and delete individual rows as needed.
6. Click **"Reset to Cleaned Baseline"** anytime to revert back to the original 392k row baseline.

### 🤖 Using the AI Executive Advisor
1. Navigate to the **"🤖 AI Executive Advisor"** tab.
2. **Built-in Strategic Reasoning Engine:** Works out-of-the-box with zero setup! Click any of the one-click strategy preset pills:
   - 📊 **Full Executive Diagnosis:** Macro health check, revenue breakdown, and risk analysis.
   - 🎯 **What Should I Do? (Action Plan):** Prioritized P0 (Immediate 7-day), P1 (Tactical 30-day), and P2 (Structural 90-day) retention playbooks with projected financial ROI.
   - 👑 **VIP Concentration & Rescue Strategy:** Account protection framework for the top 10% Platinum tier.
   - 🧬 **Month-1 Cohort Churn Recovery:** Actionable onboarding and replenishment triggers to fix the 77.6% dropoff.
3. **Custom Natural Language Questions:** Type any custom question into the prompt box (e.g., *"How do I increase average order value from £449 to £550?"*) and click **Ask AI**.
4. **Google Gemini LLM Integration (Optional):** Click **⚙️ Gemini API Settings**, enter your `GEMINI_API_KEY` (or set `export GEMINI_API_KEY="your-key"` in your shell), and save. The platform seamlessly upgrades to live Gemini 1.5/2.0 Flash reasoning!
5. **Customer 360 AI Strategy:** Look up any customer in the **Customer 360** tab and click **"✨ AI Retention Strategy"** to generate an account-specific commercial outreach script and custom rebate offer.

---

## 5. Architecture & Tech Stack

```
Executive-Retail-Analytics-Platform/
├── app/
│   ├── server.py              # FastAPI REST API (Endpoints for KPIs, trends, cohorts, upload, AI)
│   ├── ai_advisor.py          # Google Gemini LLM & Embedded CAO Strategic Reasoning Engine
│   ├── churn_engine.py        # Behavioral feature engineering & hazard scoring pipeline
│   └── static/
│       ├── index.html         # Apple-Stripe aesthetic HTML5 dashboard (7 views)
│       ├── styles.css         # Modern styling, responsive cards, glassmorphism, AI chat
│       └── app.js             # Client-side router, Chart.js managers, upload handler, AI client
├── sql/
│   ├── 01_db_cleaning.sql     # Database DDL, indexing, and data cleaning scripts
│   ├── 02_advanced_analytics.sql # Window functions for RFM, cohorts, Pareto, and cadence
│   └── 03_repurchase_timing.sql # Inter-order timing with LAG()
├── excel/
│   ├── Online_Retail_Analytical_Model.xlsx # Analytical workbook with pivot tables
│   ├── build_excel_model.py   # openpyxl automation script
│   └── excel_modeling_guide.md # Formulas, XLOOKUP, and conditional formatting
├── power_bi/
│   └── dashboard_specifications.md # Star schema, DAX formulas, and BI wireframes
├── insights/
│   ├── executive_summary.md   # Commercial strategy, churn analysis, and financial models
│   └── limitations_and_references.md # 15 technical limitations & 23 academic paper citations
├── customer_churn_predictions.csv # Scored customer churn probability dataset
├── online_retail.db           # SQLite database with 392,692 cleaned transactions
└── train_churn_model.py       # Standalone XGBoost ML model training script
```

---

## 6. Academic Foundations & Research Citations

The methodologies employed in this platform are analyzed in detail in [`insights/limitations_and_references.md`](insights/limitations_and_references.md), citing **23 peer-reviewed research papers**:
* **Probabilistic CLV & Churn:** Fader & Hardie (2005) *Counting Your Customers the Easy Way* (Marketing Science)
* **Explainable Machine Learning:** Lundberg & Lee (2017) *SHAP: A Unified Approach to Interpreting Model Predictions* (NeurIPS)
* **Temporal Cross-Validation:** Bergmeir & Benítez (2012) *Cross-validation for time series predictor evaluation* (Information Sciences)
* **RFM Segmentation Critique:** Wei, Lin, & Wu (2010) *A review of the application of RFM model* (AJBM)
* **Time Series Forecasting:** Taylor & Letham (2018) *Forecasting at Scale* (The American Statistician)

---

## 7. License & Credits
Developed as an advanced end-to-end retail intelligence and retention decision platform.
Open-source under the MIT License.
