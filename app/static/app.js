/**
 * Executive E-Commerce Analytics Dashboard Client Logic
 * Multi-View Platform:
 * - 1. Executive Overview
 * - 2. Customer 360 Deep-Dive
 * - 3. Cohort Retention Laboratory
 * - 4. ML Churn Radar & VIP Rescue Center
 * - 5. Live Interactive SQL Query Sandbox
 */

document.addEventListener('DOMContentLoaded', () => {
  initDashboard();
});

let currentView = 'overview';
let trendChartInstance = null;
let tierChartInstance = null;
let churnChartInstance = null;
let cadenceChartInstance = null;
let currentRescueData = [];

// ----------------------------------------------------
// SQL Presets for Live Sandbox
// ----------------------------------------------------
const SQL_PRESETS = {
  preset1: `-- QUERY 1: REPEAT CUSTOMER REVENUE SHARE (93.09%)
WITH Customer_Aggs AS (
    SELECT 
        CustomerID,
        COUNT(DISTINCT InvoiceNo) AS OrderCount,
        SUM(Quantity * UnitPrice) AS CustomerSpend
    FROM Transactions
    GROUP BY CustomerID
)
SELECT 
    CASE WHEN OrderCount >= 2 THEN 'Repeat Customer (2+ Orders)' ELSE 'One-Time Customer (1 Order)' END AS Tier,
    COUNT(CustomerID) AS Accounts,
    ROUND(COUNT(CustomerID) * 100.0 / (SELECT COUNT(DISTINCT CustomerID) FROM Transactions), 2) AS CustomerPct,
    ROUND(SUM(CustomerSpend), 2) AS Revenue,
    ROUND(SUM(CustomerSpend) * 100.0 / (SELECT SUM(Quantity * UnitPrice) FROM Transactions), 2) AS RevenueSharePct
FROM Customer_Aggs
GROUP BY CASE WHEN OrderCount >= 2 THEN 'Repeat Customer (2+ Orders)' ELSE 'One-Time Customer (1 Order)' END;`,

  preset2: `-- QUERY 2: PARETO REVENUE DISTRIBUTION (TOP 5%, 10%, 20%)
WITH Ranked AS (
    SELECT 
        CustomerID,
        SUM(Quantity * UnitPrice) AS Spend,
        ROW_NUMBER() OVER (ORDER BY SUM(Quantity * UnitPrice) DESC) AS SpendRank,
        COUNT(*) OVER () AS TotalCust,
        SUM(SUM(Quantity * UnitPrice)) OVER () AS TotalSpend
    FROM Transactions
    GROUP BY CustomerID
)
SELECT 'Top 5% Customers' AS GroupName, COUNT(*) AS Accounts, ROUND(SUM(Spend), 2) AS Revenue, ROUND(SUM(Spend)*100.0/MAX(TotalSpend), 2) AS RevenueSharePct FROM Ranked WHERE SpendRank <= CAST(TotalCust * 0.05 AS INT)
UNION ALL
SELECT 'Top 10% Customers' AS GroupName, COUNT(*) AS Accounts, ROUND(SUM(Spend), 2) AS Revenue, ROUND(SUM(Spend)*100.0/MAX(TotalSpend), 2) AS RevenueSharePct FROM Ranked WHERE SpendRank <= CAST(TotalCust * 0.10 AS INT)
UNION ALL
SELECT 'Top 20% Customers' AS GroupName, COUNT(*) AS Accounts, ROUND(SUM(Spend), 2) AS Revenue, ROUND(SUM(Spend)*100.0/MAX(TotalSpend), 2) AS RevenueSharePct FROM Ranked WHERE SpendRank <= CAST(TotalCust * 0.20 AS INT)
UNION ALL
SELECT 'Remaining 80%' AS GroupName, COUNT(*) AS Accounts, ROUND(SUM(Spend), 2) AS Revenue, ROUND(SUM(Spend)*100.0/MAX(TotalSpend), 2) AS RevenueSharePct FROM Ranked WHERE SpendRank > CAST(TotalCust * 0.20 AS INT);`,

  preset3: `-- QUERY 3: INTER-ORDER CADENCE WITH LAG()
WITH Distinct_Invoices AS (
    SELECT DISTINCT CustomerID, InvoiceNo, InvoiceDate FROM Transactions
),
Gaps AS (
    SELECT 
        CustomerID,
        InvoiceDate,
        LAG(InvoiceDate) OVER (PARTITION BY CustomerID ORDER BY InvoiceDate) AS PrevDate,
        ROUND(julianday(InvoiceDate) - julianday(LAG(InvoiceDate) OVER (PARTITION BY CustomerID ORDER BY InvoiceDate)), 1) AS DaysGap
    FROM Distinct_Invoices
)
SELECT 
    CASE 
        WHEN DaysGap <= 30 THEN '01. <= 30 Days'
        WHEN DaysGap <= 60 THEN '02. 31 - 60 Days'
        WHEN DaysGap <= 90 THEN '03. 61 - 90 Days'
        ELSE '04. > 90 Days'
    END AS CadenceBucket,
    COUNT(*) AS Repurchases,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM Gaps WHERE PrevDate IS NOT NULL), 2) AS SharePct
FROM Gaps
WHERE PrevDate IS NOT NULL
GROUP BY 1 ORDER BY 1;`,

  preset4: `-- QUERY 4: DENSE_RANK CUSTOMER SPEND RANKING (TOP 25)
WITH Customer_Totals AS (
    SELECT 
        CustomerID,
        Country,
        ROUND(SUM(Quantity * UnitPrice), 2) AS TotalSpend,
        COUNT(DISTINCT InvoiceNo) AS Orders,
        ROUND(SUM(Quantity * UnitPrice) / COUNT(DISTINCT InvoiceNo), 2) AS AOV
    FROM Transactions
    GROUP BY CustomerID, Country
)
SELECT 
    DENSE_RANK() OVER (ORDER BY TotalSpend DESC) AS CustomerRank,
    CustomerID,
    Country,
    TotalSpend,
    Orders,
    AOV
FROM Customer_Totals
ORDER BY TotalSpend DESC
LIMIT 25;`,

  preset5: `-- QUERY 5: DATA CLEANING AUDIT CHECK (ZERO NULLS & INVALID ENTRIES)
SELECT 
    COUNT(*) AS CleanedRows,
    COUNT(DISTINCT CustomerID) AS UniqueCustomers,
    COUNT(DISTINCT InvoiceNo) AS UniqueInvoices,
    SUM(CASE WHEN CustomerID IS NULL THEN 1 ELSE 0 END) AS NullCustomers,
    SUM(CASE WHEN Quantity <= 0 THEN 1 ELSE 0 END) AS NonPositiveQty,
    SUM(CASE WHEN UnitPrice <= 0 THEN 1 ELSE 0 END) AS NonPositivePrice,
    SUM(CASE WHEN InvoiceNo LIKE 'C%' THEN 1 ELSE 0 END) AS Cancellations
FROM Transactions;`
};

// ----------------------------------------------------
// Master Navigation View Switcher
// ----------------------------------------------------
function switchView(viewName) {
  currentView = viewName;
  
  // Update Tab Buttons
  document.querySelectorAll('.menu-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-view') === viewName);
  });
  
  // Update Panels
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.remove('active');
  });
  
  const targetPanel = document.getElementById(`view-${viewName}`);
  if (targetPanel) {
    targetPanel.classList.add('active');
  }
  
  // Trigger View Initializer
  if (viewName === 'overview') {
    // Redraw charts if needed
    if (trendChartInstance) trendChartInstance.resize();
  } else if (viewName === 'customer360') {
    if (!document.getElementById('c360ProfileContainer').style.display || document.getElementById('c360ProfileContainer').style.display === 'none') {
      lookupCustomer(14646);
    }
  } else if (viewName === 'cohorts') {
    loadDetailedCohortMatrix('retention');
  } else if (viewName === 'churn') {
    loadVIPRescueCenter();
  } else if (viewName === 'sqlsandbox') {
    if (!document.getElementById('sqlTextarea').value) {
      loadSQLPreset();
    }
  }
}

function refreshCurrentView() {
  if (currentView === 'overview') initDashboard();
  else if (currentView === 'customer360') lookupCustomer();
  else if (currentView === 'cohorts') loadDetailedCohortMatrix('retention');
  else if (currentView === 'churn') loadVIPRescueCenter();
  else if (currentView === 'sqlsandbox') executeSQLQuery();
}

// ----------------------------------------------------
// 1. Initial Dashboard Loader (Overview)
// ----------------------------------------------------
async function initDashboard() {
  await loadKPIs();
  await loadRevenueTrend();
  await loadTierDistribution();
  await loadChurnDistribution();
  loadCadenceChart();
  await searchCustomers();
  initSimulator();
}

// ----------------------------------------------------
// Number Counter Animation Helper
// ----------------------------------------------------
function animateCounter(elementId, targetValue, isCurrency = false, isPercent = false, duration = 1200) {
  const el = document.getElementById(elementId);
  if (!el) return;
  
  const startTime = performance.now();
  const startVal = 0;
  
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1.0);
    const easeProgress = 1 - Math.pow(1 - progress, 3);
    const current = startVal + (targetValue - startVal) * easeProgress;
    
    if (isCurrency) {
      el.textContent = '£' + current.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    } else if (isPercent) {
      el.textContent = current.toFixed(2) + '%';
    } else {
      el.textContent = Math.round(current).toLocaleString('en-GB');
    }
    
    if (progress < 1.0) requestAnimationFrame(update);
  }
  requestAnimationFrame(update);
}

async function loadKPIs() {
  try {
    const res = await fetch('/api/kpis');
    const data = await res.json();
    
    animateCounter('kpiRevenue', data.total_revenue, true, false);
    animateCounter('kpiCustomers', data.total_customers, false, false);
    animateCounter('kpiRepeatShare', data.repeat_revenue_share_pct, false, true);
    animateCounter('kpiTop10Share', data.top_10_share_pct, false, true);
    animateCounter('kpiChurnRate', data.churn_rate_pct, false, true);
    
    document.getElementById('kpiAtRiskCount').textContent = `${data.at_risk_customers.toLocaleString()} at-risk`;
  } catch (err) {
    console.error('Error fetching KPIs:', err);
  }
}

async function loadRevenueTrend() {
  try {
    const res = await fetch('/api/revenue-trend');
    const data = await res.json();
    
    const labels = data.map(d => d.month_year);
    const revenues = data.map(d => d.revenue);
    const orders = data.map(d => d.orders);
    
    const ctx = document.getElementById('trendChart').getContext('2d');
    if (trendChartInstance) trendChartInstance.destroy();
    
    trendChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Monthly Revenue (£)',
            data: revenues,
            backgroundColor: 'rgba(37, 99, 235, 0.75)',
            hoverBackgroundColor: 'rgba(37, 99, 235, 0.95)',
            borderRadius: 6,
            yAxisID: 'y',
            order: 2
          },
          {
            label: 'Order Volume',
            data: orders,
            type: 'line',
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            borderWidth: 3,
            pointBackgroundColor: '#f59e0b',
            pointRadius: 4,
            tension: 0.3,
            yAxisID: 'y1',
            order: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', labels: { font: { family: 'Plus Jakarta Sans', weight: 600 } } },
          tooltip: {
            backgroundColor: '#0f172a',
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              label: context => context.dataset.label.includes('Revenue') ? 
                `Revenue: £${context.raw.toLocaleString('en-GB', { minimumFractionDigits: 2 })}` : 
                `Orders: ${context.raw.toLocaleString('en-GB')}`
            }
          }
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            grid: { color: '#f1f5f9' },
            ticks: { callback: v => '£' + (v / 1000).toFixed(0) + 'k' }
          },
          y1: {
            position: 'right',
            grid: { display: false },
            ticks: { callback: v => v.toLocaleString() }
          }
        }
      }
    });
  } catch (err) {
    console.error('Error loading trend:', err);
  }
}

async function loadTierDistribution() {
  try {
    const res = await fetch('/api/tier-distribution');
    const data = await res.json();
    
    const labels = data.map(d => d.TierName.split(' (')[0]);
    const revenues = data.map(d => d.tier_revenue);
    const pcts = data.map(d => d.revenue_pct);
    
    const ctx = document.getElementById('tierDonutChart').getContext('2d');
    if (tierChartInstance) tierChartInstance.destroy();
    
    tierChartInstance = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: revenues,
          backgroundColor: ['#2563eb', '#f59e0b', '#94a3b8'],
          borderWidth: 2,
          borderColor: '#ffffff',
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Plus Jakarta Sans', weight: 600 } } },
          tooltip: {
            callbacks: {
              label: context => ` ${labels[context.dataIndex]}: £${revenues[context.dataIndex].toLocaleString('en-GB')} (${pcts[context.dataIndex]}%)`
            }
          }
        },
        cutout: '68%'
      }
    });
  } catch (err) {
    console.error('Error loading tier chart:', err);
  }
}

async function loadChurnDistribution() {
  try {
    const res = await fetch('/api/churn-distribution');
    const data = await res.json();
    
    const labels = data.map(d => d.tier);
    const counts = data.map(d => d.count);
    const pcts = data.map(d => d.pct);
    const colors = data.map(d => d.color);
    
    const ctx = document.getElementById('churnRiskChart').getContext('2d');
    if (churnChartInstance) churnChartInstance.destroy();
    
    churnChartInstance = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Customer Accounts',
          data: counts,
          backgroundColor: colors,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: context => ` Accounts: ${context.raw.toLocaleString()} (${pcts[context.dataIndex]}%)`
            }
          }
        },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: '#f1f5f9' } }
        }
      }
    });
  } catch (err) {
    console.error('Error loading churn chart:', err);
  }
}

function loadCadenceChart() {
  const ctx = document.getElementById('cadenceChart').getContext('2d');
  if (cadenceChartInstance) cadenceChartInstance.destroy();
  
  cadenceChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['<= 30 Days', '31 - 60 Days', '61 - 90 Days', '91 - 120 Days', '> 120 Days'],
      datasets: [{
        label: '% of Repurchases',
        data: [58.88, 20.19, 8.51, 5.03, 7.39],
        backgroundColor: ['#10b981', '#34d399', '#fbbf24', '#f87171', '#ef4444'],
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: context => ` Share: ${context.raw}% of all repeat purchases`
          }
        }
      },
      scales: {
        x: { grid: { display: false } },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: { callback: v => v + '%' }
        }
      }
    }
  });
}

// ----------------------------------------------------
// Customer Search (Overview Table)
// ----------------------------------------------------
let searchTimeout = null;
const searchInput = document.getElementById('customerSearchInput');
const tierSelect = document.getElementById('tierFilterSelect');

if (searchInput) {
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(searchCustomers, 300);
  });
}
if (tierSelect) {
  tierSelect.addEventListener('change', searchCustomers);
}

async function searchCustomers() {
  const query = searchInput ? searchInput.value.trim() : '';
  const tier = tierSelect ? tierSelect.value : 'all';
  
  try {
    const url = `/api/customers?limit=25&q=${encodeURIComponent(query)}&tier=${encodeURIComponent(tier)}`;
    const res = await fetch(url);
    const customers = await res.json();
    
    const tbody = document.getElementById('customerTableBody');
    tbody.innerHTML = '';
    
    if (customers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:20px; color:var(--text-muted);">No matching customers found.</td></tr>`;
      return;
    }
    
    customers.forEach(c => {
      const tr = document.createElement('tr');
      tr.style.cursor = 'pointer';
      tr.title = 'Click to open Customer 360 profile';
      tr.onclick = () => {
        switchView('customer360');
        lookupCustomer(c.CustomerID);
      };
      
      let tierBadge = 'badge-general';
      if (c.Tier === 'Platinum') tierBadge = 'badge-platinum';
      else if (c.Tier === 'Gold') tierBadge = 'badge-gold';
      
      let riskBadge = 'badge-risk-low';
      let riskText = 'Low Risk';
      if (c.RiskTier.includes('High')) { riskBadge = 'badge-risk-high'; riskText = 'Critical'; }
      else if (c.RiskTier.includes('Mod')) { riskBadge = 'badge-risk-med'; riskText = 'Moderate'; }
      
      tr.innerHTML = `
        <td style="font-weight:700; color:var(--accent-primary);">#${c.CustomerID}</td>
        <td>${c.Country}</td>
        <td style="font-weight:700;">£${c.TotalSpend.toLocaleString('en-GB', { minimumFractionDigits: 2 })}</td>
        <td>${c.TotalOrders}</td>
        <td>£${c.AOV.toFixed(2)}</td>
        <td>${c.RecencyDays.toFixed(0)}d</td>
        <td>#${c.SpendRank}</td>
        <td><span class="badge ${tierBadge}">${c.Tier}</span></td>
        <td><span style="font-weight:600; color:${c.Status === 'Active' ? '#10b981' : '#f43f5e'};">${c.Status}</span></td>
        <td><span class="badge ${riskBadge}">${(c.ChurnProbability * 100).toFixed(0)}% (${riskText})</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error searching customers:', err);
  }
}

// ----------------------------------------------------
// 2. View 2: Customer 360 Logic
// ----------------------------------------------------
async function lookupCustomer(cid = null) {
  const custId = cid || parseInt(document.getElementById('c360Input').value);
  if (!custId) {
    alert('Please enter a valid Customer ID');
    return;
  }
  
  document.getElementById('c360Input').value = custId;
  
  try {
    const res = await fetch(`/api/customer-profile/${custId}`);
    if (!res.ok) {
      alert(`Customer ID #${custId} not found`);
      return;
    }
    const data = await res.json();
    const meta = data.metadata;
    const rfm = data.rfm;
    const ml = data.ml;
    
    document.getElementById('c360ProfileContainer').style.display = 'block';
    document.getElementById('c360Avatar').textContent = meta.Country.substring(0, 2).toUpperCase();
    document.getElementById('c360Name').textContent = `Customer #${meta.CustomerID}`;
    document.getElementById('c360Country').textContent = `Country: ${meta.Country} • First Order: ${meta.first_date.split(' ')[0]}`;
    
    // Badges
    const tierBadge = document.getElementById('c360TierBadge');
    tierBadge.textContent = `${rfm.tier} Tier`;
    tierBadge.className = `badge badge-${rfm.tier.toLowerCase()}`;
    
    const riskBadge = document.getElementById('c360RiskBadge');
    riskBadge.textContent = `${(ml.probability * 100).toFixed(0)}% Churn (${ml.risk_tier.split(' (')[0]})`;
    riskBadge.className = `badge ${ml.risk_tier.includes('High') ? 'badge-risk-high' : (ml.risk_tier.includes('Mod') ? 'badge-risk-med' : 'badge-risk-low')}`;
    
    // Metrics
    document.getElementById('c360Spend').textContent = '£' + meta.total_spend.toLocaleString('en-GB', { minimumFractionDigits: 2 });
    document.getElementById('c360Orders').textContent = meta.total_orders;
    document.getElementById('c360Items').textContent = `${meta.total_items.toLocaleString()} units • ${meta.unique_products} unique items`;
    document.getElementById('c360AOV').textContent = '£' + meta.aov.toFixed(2);
    document.getElementById('c360Recency').textContent = `${meta.recency_days.toFixed(0)} days`;
    document.getElementById('c360LastDate').textContent = `Last order: ${meta.last_date.split(' ')[0]}`;
    
    // RFM Scores
    document.getElementById('c360RScore').textContent = `${rfm.r} / 5`;
    document.getElementById('c360FScore').textContent = `${rfm.f} / 5`;
    document.getElementById('c360MScore').textContent = `${rfm.m} / 5`;
    
    // AI Action
    document.getElementById('c360ActionText').textContent = ml.recommended_action;
    
    // Invoices Table
    const invTbody = document.getElementById('c360InvoicesTable');
    invTbody.innerHTML = '';
    data.invoices.forEach(inv => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight:700;">#${inv.InvoiceNo}</td>
        <td>${inv.InvoiceDate}</td>
        <td>${inv.items_count} items</td>
        <td>${inv.total_units} units</td>
        <td style="font-weight:700;">£${inv.invoice_total.toFixed(2)}</td>
      `;
      invTbody.appendChild(tr);
    });
    
    // Top Products Table
    const prodTbody = document.getElementById('c360ProductsTable');
    prodTbody.innerHTML = '';
    data.top_products.forEach(p => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="font-weight:700;">${p.StockCode}</td>
        <td style="max-width:180px; overflow:hidden; text-overflow:ellipsis;">${p.Description}</td>
        <td>${p.units}</td>
        <td style="font-weight:700;">£${p.product_spend.toFixed(2)}</td>
      `;
      prodTbody.appendChild(tr);
    });
    
  } catch (err) {
    console.error('Error fetching customer profile:', err);
  }
}

// ----------------------------------------------------
// 3. View 3: Cohort Studio (Multi-Metric Matrix)
// ----------------------------------------------------
let activeCohortMetric = 'retention';

function switchCohortMetric(metric) {
  activeCohortMetric = metric;
  ['Retention', 'Revenue', 'Count'].forEach(m => {
    const btn = document.getElementById(`btnCohort${m}`);
    if (btn) btn.classList.toggle('active', m.toLowerCase() === metric);
  });
  loadDetailedCohortMatrix(metric);
}

async function loadDetailedCohortMatrix(metric = 'retention') {
  try {
    const res = await fetch(`/api/cohorts?metric=${metric}`);
    const data = await res.json();
    
    const theadRow = document.getElementById('cohortDetailedHeaderRow');
    const tbody = document.getElementById('cohortDetailedTableBody');
    
    theadRow.innerHTML = '<th class="cohort-month-col">Acquisition Cohort</th><th>Cohort Size</th>';
    data.indices.forEach(idx => {
      const th = document.createElement('th');
      th.textContent = `Month ${idx}`;
      theadRow.appendChild(th);
    });
    
    tbody.innerHTML = '';
    data.months.forEach((month, rIdx) => {
      const tr = document.createElement('tr');
      const size = data.sizes[rIdx];
      let html = `<td class="cohort-month-col">${month}</td><td style="font-weight:700; background:#f8fafc;">${size.toLocaleString()}</td>`;
      
      data.indices.forEach((colIdx, cIdx) => {
        const val = data.matrix[rIdx][cIdx];
        if (val > 0) {
          let bg = '#ffffff';
          let textColor = '#0f172a';
          let text = '';
          
          if (metric === 'retention') {
            text = val.toFixed(1) + '%';
            if (val >= 80) { bg = '#d1fae5'; textColor = '#065f46'; }
            else if (val >= 35) { bg = '#ecfdf5'; textColor = '#047857'; }
            else if (val >= 20) { bg = '#fef3c7'; textColor = '#92400e'; }
            else { bg = '#f8fafc'; textColor = '#64748b'; }
          } else if (metric === 'revenue') {
            text = '£' + (val / 1000).toFixed(0) + 'k';
            bg = val >= 50000 ? '#e0e7ff' : (val >= 20000 ? '#eef2ff' : '#f8fafc');
            textColor = '#1e3a8a';
          } else { // count
            text = val.toString();
            bg = val >= 200 ? '#f1f5f9' : '#ffffff';
          }
          
          html += `<td style="background:${bg}; color:${textColor};">${text}</td>`;
        } else {
          html += `<td style="color:#cbd5e1;">-</td>`;
        }
      });
      tr.innerHTML = html;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading detailed cohorts:', err);
  }
}

// ----------------------------------------------------
// 4. View 4: ML Churn Radar & VIP Rescue Center
// ----------------------------------------------------
async function loadVIPRescueCenter() {
  try {
    const res = await fetch('/api/vip-rescue');
    const data = await res.json();
    currentRescueData = data.accounts;
    
    document.getElementById('rescueCountVal').textContent = data.accounts_count.toLocaleString();
    document.getElementById('rescueRevenueVal').textContent = '£' + data.total_revenue_at_stake.toLocaleString('en-GB', { minimumFractionDigits: 2 });
    document.getElementById('rescueAvgGapVal').textContent = `${data.avg_recency_days} days`;
    
    const tbody = document.getElementById('rescueTableBody');
    tbody.innerHTML = '';
    
    data.accounts.forEach(acc => {
      const tr = document.createElement('tr');
      tr.style.cursor = 'pointer';
      tr.onclick = () => {
        switchView('customer360');
        lookupCustomer(acc.CustomerID);
      };
      
      tr.innerHTML = `
        <td style="font-weight:700; color:var(--accent-primary);">#${acc.CustomerID}</td>
        <td>${acc.Country}</td>
        <td style="font-weight:700;">£${acc.TotalSpend.toLocaleString('en-GB', { minimumFractionDigits: 2 })}</td>
        <td>${acc.TotalOrders}</td>
        <td>${acc.RecencyDays.toFixed(0)}d ago</td>
        <td><span class="badge badge-${acc.Tier.toLowerCase()}">${acc.Tier}</span></td>
        <td><span class="badge badge-risk-high">${(acc.ChurnProbability * 100).toFixed(0)}% Risk</span></td>
        <td style="font-size:12px; color:#b45309; font-weight:600;">Dispatch priority executive outreach</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error('Error loading VIP rescue:', err);
  }
}

function exportRescueCSV() {
  if (!currentRescueData || currentRescueData.length === 0) {
    alert('No accounts to export');
    return;
  }
  
  let csv = 'CustomerID,Country,TotalSpend,TotalOrders,RecencyDays,Tier,ChurnProbability\n';
  currentRescueData.forEach(r => {
    csv += `${r.CustomerID},"${r.Country}",${r.TotalSpend},${r.TotalOrders},${r.RecencyDays},"${r.Tier}",${r.ChurnProbability}\n`;
  });
  
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.setAttribute('href', url);
  a.setAttribute('download', 'vip_churn_rescue_list.csv');
  a.click();
}

// ----------------------------------------------------
// 5. View 5: Live SQL Query Sandbox
// ----------------------------------------------------
function loadSQLPreset() {
  const presetKey = document.getElementById('sqlPresetSelect').value;
  const sql = SQL_PRESETS[presetKey] || SQL_PRESETS.preset1;
  document.getElementById('sqlTextarea').value = sql;
  executeSQLQuery();
}

async function executeSQLQuery() {
  const query = document.getElementById('sqlTextarea').value.trim();
  if (!query) return;
  
  const timerLabel = document.getElementById('sqlExecutionTimer');
  timerLabel.textContent = 'Executing...';
  timerLabel.style.color = '#3b82f6';
  
  try {
    const res = await fetch('/api/sql-sandbox', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query })
    });
    
    if (!res.ok) {
      const err = await res.json();
      timerLabel.textContent = 'Execution Error';
      timerLabel.style.color = '#f43f5e';
      alert('SQL Error: ' + err.detail);
      return;
    }
    
    const result = await res.json();
    timerLabel.textContent = `Executed in ${result.execution_time_ms}ms (${result.row_count} rows)`;
    timerLabel.style.color = '#10b981';
    
    // Display Query Plan
    const planBox = document.getElementById('queryPlanBox');
    const planText = document.getElementById('queryPlanText');
    if (result.query_plan && result.query_plan.length > 0) {
      planBox.style.display = 'block';
      planText.innerHTML = result.query_plan.map(p => `• ${p}`).join('<br>');
    } else {
      planBox.style.display = 'none';
    }
    
    // Display Table Headers
    const thead = document.getElementById('sqlResultsThead');
    thead.innerHTML = '<tr>' + result.columns.map(c => `<th>${c}</th>`).join('') + '</tr>';
    
    // Display Table Rows
    const tbody = document.getElementById('sqlResultsTbody');
    tbody.innerHTML = '';
    result.rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.innerHTML = r.map(val => {
        const displayVal = typeof val === 'number' ? val.toLocaleString() : (val !== null ? val : 'NULL');
        return `<td>${displayVal}</td>`;
      }).join('');
      tbody.appendChild(tr);
    });
    
  } catch (err) {
    timerLabel.textContent = 'Network Error';
    timerLabel.style.color = '#f43f5e';
    console.error('SQL execution error:', err);
  }
}

// ----------------------------------------------------
// Simulator Logic
// ----------------------------------------------------
function initSimulator() {
  const growthSlider = document.getElementById('growthSlider');
  const churnSlider = document.getElementById('churnSlider');
  if (growthSlider && churnSlider) {
    growthSlider.addEventListener('input', runSimulation);
    churnSlider.addEventListener('input', runSimulation);
    runSimulation();
  }
}

async function runSimulation() {
  const growth = parseFloat(document.getElementById('growthSlider').value);
  const churn = parseFloat(document.getElementById('churnSlider').value);
  
  document.getElementById('growthValBubble').textContent = `+${growth.toFixed(1)}%`;
  document.getElementById('churnValBubble').textContent = `+${churn.toFixed(1)}%`;
  
  try {
    const res = await fetch(`/api/forecast?growth=${growth}&churn_save=${churn}`);
    const data = await res.json();
    
    document.getElementById('projectedRevenueVal').textContent = '£' + data.projected_2012.toLocaleString('en-GB', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    const incPct = ((data.incremental_revenue / data.baseline_2011) * 100).toFixed(2);
    document.getElementById('incrementalRevenueVal').textContent = `+£${data.incremental_revenue.toLocaleString('en-GB', { minimumFractionDigits: 0 })} (+${incPct}% Uplift)`;
    
    const tiers = data.tier_projections;
    document.getElementById('simTierBreakdown').textContent = 
      `Platinum: £${(tiers.Platinum / 1e6).toFixed(2)}M • Gold: £${(tiers.Gold / 1e6).toFixed(2)}M • General: £${(tiers.General / 1e6).toFixed(2)}M`;
  } catch (err) {
    console.error('Error running simulation:', err);
  }
}
