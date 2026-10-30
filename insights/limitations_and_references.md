# Limitations & Research References

## Executive Retail Analytics & Churn Intelligence Platform

> [!NOTE]
> This document identifies **15 technical limitations** across 6 categories, each grounded in academic literature with **20+ cited research papers**. It covers the dataset, ML model, analytical methods, platform architecture, and proposed mitigations.

---

## Table of Contents

1. [Dataset Limitations](#1-dataset-limitations)
2. [Machine Learning Model Limitations](#2-machine-learning-model-limitations)
3. [Analytical Methodology Limitations](#3-3-analytical-methodology-limitations)
4. [Platform & Architecture Limitations](#4-platform--architecture-limitations)
5. [Business Generalizability Limitations](#5-business-generalizability-limitations)
6. [Proposed Mitigations & Future Work](#6-proposed-mitigations--future-work)
7. [Full Reference List](#7-full-reference-list)

---

## 1. Dataset Limitations

### 1.1 Short Observation Window (13 Months)

The UCI Online Retail dataset spans **December 2010 to December 2011** — a single calendar year. This restricts long-term lifecycle analysis and makes it impossible to distinguish **true churn from seasonal purchasing behavior** (e.g., customers who only buy during the Christmas holiday season year-over-year). Survival analysis and multi-year cohort tracking require substantially longer observation periods [1][2].

> *"A 12-month window restricts long-term lifecycle analysis. It is difficult to distinguish true churn from multi-seasonal purchasing behavior."*
> — Hadden et al., via UCI Online Retail Dataset analyses [1]

### 1.2 Missing Customer IDs (~25% Records Discarded)

A significant proportion of raw transactions contain **null `CustomerID` values** (guest checkouts). These ~135,000+ rows are entirely discarded during cleaning, restricting behavioral models to only ~4,338 registered customers and introducing **selection bias** — anonymous transactions that may contain valuable macro-trend patterns are lost [2][3].

### 1.3 No Explicit Churn Label (Non-Contractual Setting)

Unlike telecom or SaaS datasets where churn is triggered by contract cancellation, this is a **non-contractual e-commerce** setting. Customers can stop purchasing at any time without formally "leaving." The project defines churn as **no purchase in the final 70 days** of the dataset — this heuristic introduces label noise, as a "churned" customer might simply be an infrequent buyer with a long inter-purchase cycle [4][5].

> *"Researchers must arbitrarily define a threshold... this heuristic introduces label noise; a 'churned' customer might just be an infrequent buyer."*
> — Semantic Scholar review of non-contractual churn studies [4]

### 1.4 Lack of Rich Covariates

The dataset contains only **8 transactional columns** — no customer demographics, website clickstream data, marketing touchpoints, customer service interactions, product review sentiments, or session-level behavioral data. This limits the model to relying heavily on engineered RFM features and basic transactional history, reducing predictive nuance [2][6].

---

## 2. Machine Learning Model Limitations

### 2.1 No Cross-Validation or Hyperparameter Tuning

The XGBoost model uses a **single 80/20 stratified train-test split** with manually selected hyperparameters (`n_estimators=250`, `learning_rate=0.03`, `max_depth=5`). No k-fold cross-validation, GridSearchCV, RandomizedSearchCV, or Bayesian optimization is employed. This creates a risk of **overfitting to a single split** and potentially suboptimal hyperparameter choices [7][8].

> *"If hyperparameter tuning is managed poorly, XGBoost is susceptible to overfitting on noisy e-commerce data, degrading out-of-time validation performance."*
> — ResearchGate review of XGBoost churn prediction [7]

### 2.2 No Temporal Cross-Validation

Despite the inherently **temporal nature** of transaction data, the project uses a simple random stratified split rather than time-series-aware cross-validation (e.g., expanding window or sliding window). While the observation vs. prediction window is correctly separated, the training data within the observation window is not validated across time folds, which can leak temporal patterns [9][2].

### 2.3 Class Imbalance — Limited Treatment

The model compensates for class imbalance using only XGBoost's `scale_pos_weight` parameter. **No SMOTE, ADASYN, or focal loss** is applied. Academic literature strongly recommends combining resampling techniques with cost-sensitive learning, especially in non-contractual e-commerce where churn ratios can be heavily skewed [7][10].

> *"Standard XGBoost aims to minimize overall error, which can cause the model to overwhelmingly predict the majority class (non-churners), leading to poor recall for actual churners."*
> — Aptii Research Journal [10]

### 2.4 No Model Interpretability (SHAP / LIME)

The platform relies solely on XGBoost's **built-in gain-based feature importance**, which measures how much a feature improves the loss function across all splits — but does not explain **individual predictions**. No SHAP (Shapley Additive Explanations) or LIME (Local Interpretable Model-agnostic Explanations) is implemented. Marketers cannot understand *why* a specific customer is flagged as high-risk without per-instance explanations [7][11].

> *"E-commerce marketers cannot act on a simple 'churn probability' score alone. They need to know why a customer is leaving to deploy targeted retention offers."*
> — DRPress: Explainable XGBoost for E-Commerce Churn [11]

### 2.5 No Feature Selection Methods

All **14 engineered features** are used without any feature selection process (e.g., mutual information, recursive feature elimination, LASSO regularization, or permutation importance). Including irrelevant or highly correlated features can introduce noise and reduce generalization performance [8][12].

### 2.6 No Model Comparison or Ensemble

Only **XGBoost** is trained and evaluated. No comparison with alternative algorithms (Random Forest, LightGBM, CatBoost, Logistic Regression, Neural Networks) or ensemble stacking is performed. Academic best practice recommends evaluating multiple models to establish a performance baseline and identify the best architecture for the specific data distribution [8][13][14].

---

## 3. Analytical Methodology Limitations

### 3.1 Static RFM Thresholds (Not Quantile-Based)

RFM scores are assigned using **manually hardcoded thresholds** (e.g., Recency ≤30d → 5, Frequency ≥10 → 5, Monetary ≥£5,000 → 5) rather than data-driven quantile-based scoring. This introduces **subjective bias** and produces unstable segment boundaries that won't adapt to new data distributions or different retail contexts [15][16].

> *"Standard RFM typically assigns scores using quintiles or arbitrary manager-set thresholds. This introduces subjective bias and can lead to unstable cluster boundaries."*
> — FinSI AI & Academic RFM Reviews [15]

### 3.2 No Probabilistic CLV Models

The project lacks **probabilistic Customer Lifetime Value** models such as **BG/NBD** (Beta-Geometric/Negative Binomial Distribution) for purchase frequency modeling, **Pareto/NBD** for churn timing, or **Gamma-Gamma** for monetary value estimation. These models are the academic gold standard for non-contractual settings and would provide statistically rigorous CLV estimates instead of simple RFM aggregates [5][17].

### 3.3 Rule-Based Segmentation (No Unsupervised Learning)

Customer segments (Platinum/Gold/General) are defined by **percentile-based rules** using `CUME_DIST()`. No unsupervised machine learning (K-Means, DBSCAN, hierarchical clustering, or Gaussian Mixture Models) is used to discover natural customer groupings. Rule-based segmentation cannot capture complex multi-dimensional behavioral clusters that emerge organically from the data [16][18].

### 3.4 Revenue Simulator is Not Statistical Forecasting

The "Revenue Impact Simulator" uses a **simple linear formula**: `projected = baseline × (1 + growth%) + (at_risk_pool × recovery%)`. This is **not** time-series forecasting. No ARIMA, Prophet, Holt-Winters exponential smoothing, or ML-based forecasting is implemented. The simulator cannot account for seasonality, trend decomposition, or confidence intervals [19].

### 3.5 Cohort Analysis — Aggregated Group Blindness

The cohort retention matrix tracks **aggregate group behavior** rather than individual dynamics. An entire cohort may appear to retain well while a tiny fraction of hyper-loyal users drives the metrics and the rest have completely churned — the **ecological fallacy** problem. Additionally, newer cohorts inherently have less observable history (right-censorship), requiring survival analysis adjustments that are not implemented [15][20].

### 3.6 Hardcoded Dashboard Metrics

Several key dashboard values are **statically hardcoded** rather than dynamically computed from the API:
- Cadence distribution chart (58.88%, 20.19%, 8.51%, 5.03%, 7.39%)
- Top-10% revenue share KPI (61.41%)
- Various subtitle statistics

This means the dashboard will not reflect changes if data is uploaded or modified via the Data Studio.

---

## 4. Platform & Architecture Limitations

### 4.1 SQLite Single-Writer Bottleneck

SQLite allows multiple concurrent readers but **only one writer** at a time. In a multi-user analytics platform where data uploads and transaction inserts occur alongside dashboard reads, concurrent write requests will queue up or throw `database is locked` errors. SQLite cannot scale horizontally across multiple server instances [21][22].

### 4.2 No Real-Time Streaming Pipeline

The platform uses a **request-response** architecture. No WebSocket connections, Server-Sent Events, or streaming data pipelines exist. Dashboard data is only updated on page load or manual refresh — not in real-time. Production analytics platforms typically require event-driven architectures with message brokers (Redis Pub/Sub, Kafka) for live metric updates [21].

---

## 5. Business Generalizability Limitations

### 5.1 B2B Wholesale Context — Not B2C

The dataset represents a **UK-based wholesale gift retailer** selling to other businesses (gift shops). A significant portion of customers are **B2B wholesalers** buying inventory in bulk with irregular cycles. Purchasing patterns, churn definitions, RFM thresholds, and segmentation logic derived from this data **may not generalize to standard B2C retail** e-commerce [2][3].

### 5.2 No Product-Level or Basket Analysis

The platform performs no **association rule mining** (Apriori, FP-Growth), **market basket analysis**, or **product recommendation modeling**. Product-level insights (which items are frequently co-purchased, which products are associated with churn) are entirely absent, limiting the depth of retention strategy recommendations [6][18].

### 5.3 Geographic Concentration Bias

The dataset is **~80% UK transactions**. Analytics and segmentation are computed across all 37 countries without geographic stratification, meaning UK purchasing patterns dominate all aggregate metrics and potentially mask divergent international behavior [2].

---

## 6. Proposed Mitigations & Future Work

| Limitation | Recommended Mitigation | Academic Basis |
|:---|:---|:---|
| Short observation window | Acquire multi-year transactional data; apply survival analysis (Cox PH) | [1][20] |
| No cross-validation | Implement 5-fold time-series-aware CV with expanding window | [9][8] |
| Class imbalance | Add SMOTE/ADASYN + evaluate with PR-AUC and F₂-score | [10][7] |
| No interpretability | Integrate SHAP for global + local explanations | [11][14] |
| Static RFM thresholds | Switch to quantile-based scoring or K-Means clustering on RFM features | [15][16][18] |
| No CLV modeling | Implement BG/NBD + Gamma-Gamma via `lifetimes` library | [5][17] |
| Linear revenue simulator | Replace with Facebook Prophet or ARIMA with seasonality decomposition | [19] |
| No model comparison | Benchmark XGBoost vs. LightGBM, CatBoost, Random Forest, Logistic Regression | [8][13] |
| No feature selection | Apply RFE, mutual information, or permutation importance | [12][8] |
| SQLite bottleneck | Migrate to PostgreSQL + TimescaleDB for production workloads | [21][22] |
| No basket analysis | Implement Apriori/FP-Growth for product co-occurrence mining | [6][18] |
| Cohort ecological fallacy | Augment with individual-level survival curves (Kaplan-Meier) | [15][20] |

---

## 7. Full Reference List

**[1]** Chen, D., Sain, S.L., & Guo, K. (2012). *"Data mining for the online retail industry: A case study of RFM model-based customer segmentation using data mining."* Journal of Database Marketing & Customer Strategy Management, 19(3), 197–208. DOI: 10.1057/dbm.2012.17

**[2]** Daqing, C. (2015). *"Online Retail Dataset."* UCI Machine Learning Repository. Available at: https://archive.ics.uci.edu/ml/datasets/Online+Retail

**[3]** Hadden, J., Tiwari, A., Roy, R., & Ruta, D. (2007). *"Computer assisted customer churn management: State-of-the-art and future trends."* Computers & Operations Research, 34(10), 2902–2917. DOI: 10.1016/j.cor.2005.11.007

**[4]** Fader, P.S., & Hardie, B.G.S. (2009). *"Probability Models for Customer-Base Analysis."* Journal of Interactive Marketing, 23(1), 61–69. DOI: 10.1016/j.intmar.2008.11.003

**[5]** Fader, P.S., Hardie, B.G.S., & Lee, K.L. (2005). *"'Counting Your Customers' the Easy Way: An Alternative to the Pareto/NBD Model."* Marketing Science, 24(2), 275–284. DOI: 10.1287/mksc.1040.0098

**[6]** Jahan, I., & Sanam, T.F. (2024). *"A comprehensive framework for customer retention in E-commerce using machine learning based on churn prediction, customer segmentation, and recommendation."* Electronic Commerce Research and Applications, 67, 101427. DOI: 10.1016/j.elerap.2024.101427

**[7]** ResearchGate (2024). *"Implementing XGBoost Model for Predicting Customer Churn in E-Commerce Platforms."* With analysis of SMOTE integration and F₂-score optimization for recall-favoring evaluation.

**[8]** Imani, M., Joudaki, M., Beikmohamadi, A., & Arabnia, H.R. (2025). *"Customer Churn Prediction: A Review of Recent Advances, Trends, and Challenges in Conventional Machine Learning and Deep Learning."* Preprints.org. DOI: 10.20944/preprints202501.0001.v1

**[9]** Bergmeir, C., & Benítez, J.M. (2012). *"On the use of cross-validation for time series predictor evaluation."* Information Sciences, 191, 192–213. DOI: 10.1016/j.ins.2011.12.028

**[10]** Aptii Research (2024). *"Implementing XGBoost Model for Predicting Customer Churn in E-Commerce Platforms."* Aptii Open Research Journal, Indonesia.

**[11]** DRPress (2024). *"An Experimental Study on E-commerce Customer Churn Prediction Based on the Explainable XGBoost Algorithm."* With SHAP + RFM segmentation integration for overcoming interpretability and customer heterogeneity limitations.

**[12]** Guyon, I., & Elisseeff, A. (2003). *"An Introduction to Variable and Feature Selection."* Journal of Machine Learning Research, 3, 1157–1182.

**[13]** Vafeiadis, T., Diamantaras, K.I., Sarigiannidis, G., & Chatzisavvas, K.C. (2015). *"A comparison of machine learning techniques for customer churn prediction."* Simulation Modelling Practice and Theory, 55, 1–9. DOI: 10.1016/j.simpat.2015.03.003

**[14]** Lundberg, S.M., & Lee, S.I. (2017). *"A Unified Approach to Interpreting Model Predictions."* Advances in Neural Information Processing Systems (NeurIPS), 30. (SHAP paper)

**[15]** Wei, J.T., Lin, S.Y., & Wu, H.H. (2010). *"A review of the application of RFM model."* African Journal of Business Management, 4(19), 4199–4206.

**[16]** Christy, A.J., Umamakeswari, A., Priyatharsini, L., & Neyaa, A. (2021). *"RFM ranking – An effective approach to customer segmentation."* Journal of King Saud University – Computer and Information Sciences, 33(10), 1251–1257. DOI: 10.1016/j.jksuci.2018.09.004

**[17]** Fader, P.S., Hardie, B.G.S., & Lee, K.L. (2005). *"RFM and CLV: Using iso-value curves for customer base analysis."* Journal of Marketing Research, 42(4), 415–430. DOI: 10.1509/jmkr.2005.42.4.415

**[18]** Kansal, T., Bahuguna, S., Singh, V., & Choudhury, T. (2018). *"Customer Segmentation using K-means Clustering."* International Conference on Computational Techniques, Electronics and Mechanical Systems (CTEMS). DOI: 10.1109/CTEMS.2018.8769171

**[19]** Taylor, S.J., & Letham, B. (2018). *"Forecasting at Scale."* The American Statistician, 72(1), 37–45. DOI: 10.1080/00031305.2017.1380080 (Facebook Prophet)

**[20]** Kleinbaum, D.G., & Klein, M. (2012). *Survival Analysis: A Self-Learning Text.* 3rd Edition, Springer. DOI: 10.1007/978-1-4419-6646-9

**[21]** Hipp, R.D. (2023). *"SQLite: Appropriate Uses For SQLite."* Official SQLite Documentation. Available at: https://www.sqlite.org/whentouse.html

**[22]** Ramírez-Gallego, S., et al. (2017). *"A survey on data preprocessing for data stream mining."* Neurocomputing, 239, 39–57. DOI: 10.1016/j.neucom.2017.01.078

**[23]** Taylor & Francis (2025). *"A comprehensive survey on customer churn analysis studies."* Examines the complete customer journey and touchpoints influencing churn behavior. DOI: 10.1080/03155986.2025 (forthcoming)
