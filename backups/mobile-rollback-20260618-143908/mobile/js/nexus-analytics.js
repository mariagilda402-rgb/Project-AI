/** Nexus Mobile — nexus-analytics.js */
// ================================================================
// ANALYTICS & CHARTS DASHBOARD (Chart.js)
// ================================================================

window._chartInstances = window._chartInstances || {};
let _chartInstances = window._chartInstances;

function initChartDefaults() {
    if (typeof Chart !== 'undefined') {
        Chart.defaults.color = 'rgba(255, 255, 255, 0.6)';
        Chart.defaults.font.family = "'Inter', sans-serif";
        Chart.defaults.scale.grid.color = 'rgba(255, 255, 255, 0.05)';
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 15, 25, 0.9)';
        Chart.defaults.plugins.tooltip.titleColor = '#fff';
        Chart.defaults.plugins.tooltip.bodyColor = '#ccc';
        Chart.defaults.plugins.tooltip.borderColor = 'rgba(108, 92, 231, 0.3)';
        Chart.defaults.plugins.tooltip.borderWidth = 1;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
        Chart.defaults.plugins.tooltip.padding = 10;
    }
}

function safeDestroyChart(id) {
    window._chartInstances = window._chartInstances || {};
    _chartInstances = window._chartInstances;

    const trackedChart = _chartInstances[id];
    if (trackedChart && typeof trackedChart.destroy === 'function') {
        try {
            trackedChart.destroy();
        } catch (error) {
            console.warn('Chart destroy failed for tracked instance:', id, error);
        }
    }

    const canvas = document.getElementById(id);
    const registeredChart = canvas && typeof Chart !== 'undefined' && typeof Chart.getChart === 'function'
        ? Chart.getChart(canvas)
        : null;
    if (registeredChart && registeredChart !== trackedChart && typeof registeredChart.destroy === 'function') {
        try {
            registeredChart.destroy();
        } catch (error) {
            console.warn('Chart destroy failed for registry instance:', id, error);
        }
    }

    delete window._chartInstances[id];
    delete _chartInstances[id];
}

// ─── Finance Charts ──────────────────────────────────────────────

function renderFinanceCharts() {
    if (typeof Chart === 'undefined') return;
    initChartDefaults();
    
    const raw = (LocalDB.get('finance_transactions') || []).filter(t => !t.is_deleted);
    const txDate = t => (t.occurred_at || t.date || t.created_at || '').slice(0, 10);
    const transactions = raw.map(t => ({
        ...t,
        date: txDate(t),
        amount: Number(t.amount) || 0
    }));
    
    // 1. PIE CHART: Expenses by Category (Current Month)
    const now = new Date();
    const currMonth = now.toISOString().slice(0, 7); // YYYY-MM
    
    const expensesThisMonth = transactions.filter(t => t.type === 'expense' && t.date.startsWith(currMonth));
    const catTotals = {};
    expensesThisMonth.forEach(t => {
        catTotals[t.category] = (catTotals[t.category] || 0) + t.amount;
    });
    
    const catLabels = Object.keys(catTotals);
    const catData = Object.values(catTotals);
    
    safeDestroyChart('finance-pie-chart');
    const pieCtx = document.getElementById('finance-pie-chart');
    if (pieCtx && catLabels.length > 0) {
        _chartInstances['finance-pie-chart'] = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: catLabels,
                datasets: [{
                    data: catData,
                    backgroundColor: ['#22d3ee', '#a78bfa', '#fb923c', '#fb7185', '#34d399', '#fbbf24', '#94a3b8'],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { position: 'right', labels: { boxWidth: 12, usePointStyle: true, font: {size: 11} } }
                }
            }
        });
    }

    // 2. BAR CHART: Last 6 Months (Income vs Expense)
    const months = [];
    for (let i = 5; i >= 0; i--) {
        const d = new Date();
        d.setMonth(d.getMonth() - i);
        months.push(d.toISOString().slice(0, 7)); // YYYY-MM
    }
    
    const incomeData = months.map(m => {
        return transactions.filter(t => t.type === 'income' && t.date.startsWith(m)).reduce((s,t) => s + t.amount, 0);
    });
    const expenseData = months.map(m => {
        return transactions.filter(t => t.type === 'expense' && t.date.startsWith(m)).reduce((s,t) => s + t.amount, 0);
    });
    
    const monthLabels = months.map(m => {
        const [yy, mm] = m.split('-');
        const names = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
        return names[parseInt(mm)-1];
    });

    safeDestroyChart('finance-bar-chart');
    const barCtx = document.getElementById('finance-bar-chart');
    if (barCtx) {
        _chartInstances['finance-bar-chart'] = new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: monthLabels,
                datasets: [
                    { label: 'Receitas', data: incomeData, backgroundColor: '#34d399', borderRadius: 4 },
                    { label: 'Despesas', data: expenseData, backgroundColor: '#fb7185', borderRadius: 4 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { display: false } },
                    y: { border: { display: false }, ticks: { maxTicksLimit: 5 } }
                },
                plugins: { legend: { display: true, position: 'top', labels: { usePointStyle: true, boxWidth: 8, font: {size: 11} } } }
            }
        });
    }
}

// ─── Habits Chart ────────────────────────────────────────────────

function renderHabitCharts() {
    if (typeof Chart === 'undefined') return;
    initChartDefaults();
    
    const habits = LocalDB.getAll('habits') || [];
    const days = 14;
    const labels = [];
    const percentages = [];
    
    for (let i = days - 1; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const iso = d.toISOString().split('T')[0];
        labels.push(d.getDate() + '/' + (d.getMonth()+1));
        
        let totalActive = 0;
        let totalDone = 0;
        
        habits.forEach(h => {
            // Very simplified: assuming all habits are daily for the chart
            totalActive++;
            if (h.history && h.history.includes(iso)) totalDone++;
        });
        
        percentages.push(totalActive === 0 ? 0 : Math.round((totalDone / totalActive) * 100));
    }
    
    safeDestroyChart('habits-line-chart');
    const ctx = document.getElementById('habits-line-chart');
    if (ctx) {
        _chartInstances['habits-line-chart'] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Aderência (%)',
                    data: percentages,
                    borderColor: '#a78bfa',
                    backgroundColor: 'rgba(167, 139, 250, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#a78bfa',
                    pointRadius: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { display: false }, ticks: { maxTicksLimit: 7 } },
                    y: { min: 0, max: 100, border: { display: false }, ticks: { stepSize: 25 } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
}

// ─── Studies Chart ───────────────────────────────────────────────

function renderStudyCharts() {
    if (typeof Chart === 'undefined') return;
    initChartDefaults();

    const pomos = LocalDB.get('pomo_sessions') || [];
    const pomoDate = (p) => p.session_date || p.date || (p.created_at || '').split('T')[0];

    const days = 7;
    const labels = [];
    const pomoData = [];

    for (let i = days - 1; i >= 0; i--) {
        const d = new Date();
        d.setDate(d.getDate() - i);
        const iso = d.toISOString().split('T')[0];
        labels.push(d.toLocaleDateString('pt-BR', { weekday: 'short' }));
        const count = pomos.filter(p => String(pomoDate(p)).startsWith(iso)).length;
        pomoData.push(count);
    }
    
    safeDestroyChart('studies-bar-chart');
    const ctx = document.getElementById('studies-bar-chart');
    if (ctx) {
        _chartInstances['studies-bar-chart'] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Pomodoros',
                    data: pomoData,
                    backgroundColor: '#fb923c',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { grid: { display: false } },
                    y: { border: { display: false }, ticks: { stepSize: 1 } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
}

// Intercept the loaders to trigger chart rendering
const _origLoadFinanceForCharts = window.loadFinance;
window.loadFinance = function() {
    if (typeof _origLoadFinanceForCharts === 'function') _origLoadFinanceForCharts();
    ensureChartJs().then(() => setTimeout(renderFinanceCharts, 100));
};

const _origLoadHabitsForCharts = window.loadHabits;
window.loadHabits = function() {
    if (typeof _origLoadHabitsForCharts === 'function') _origLoadHabitsForCharts();
    ensureChartJs().then(() => setTimeout(renderHabitCharts, 100));
};

const _origLoadStudiesForCharts = window.loadStudies;
window.loadStudies = function() {
    if (typeof _origLoadStudiesForCharts === 'function') _origLoadStudiesForCharts();
    ensureChartJs().then(() => setTimeout(renderStudyCharts, 100));
};
