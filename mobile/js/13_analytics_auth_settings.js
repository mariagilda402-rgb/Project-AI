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
    
    const transactions = LocalDB.getAll('transactions') || [];
    
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


// ================================================================
// MULTI-USER AUTH & SETTINGS
// ================================================================

let currentUser = null;

// Listen for auth changes
if (window.nexusSupabase) {
    window.nexusSupabase.auth.onAuthStateChange((event, session) => {
        currentUser = session ? session.user : null;
        updateSettingsUI();
        if (event === 'SIGNED_IN') {
            forceSyncData();
        }
    });
    
    // Initial check
    window.nexusSupabase.auth.getSession().then(({ data: { session } }) => {
        currentUser = session ? session.user : null;
        updateSettingsUI();
    });
}

function updateSettingsUI() {
    const title = document.getElementById('auth-status-title');
    const desc = document.getElementById('auth-status-desc');
    const icon = document.getElementById('auth-status-icon');
    const btnLogin = document.getElementById('btn-login-google');
    const btnLogout = document.getElementById('btn-logout');
    
    if (!title) return;

    if (currentUser) {
        icon.innerHTML = '<i class="fa-solid fa-cloud-check" style="color:var(--accent-green)"></i>';
        title.textContent = `Logado como: ${currentUser.user_metadata?.full_name || currentUser.email}`;
        desc.textContent = 'Seus dados estão sendo sincronizados na nuvem.';
        btnLogin.style.display = 'none';
        btnLogout.style.display = 'block';
    } else {
        icon.innerHTML = '<i class="fa-solid fa-cloud-offline" style="color:var(--text-secondary)"></i>';
        title.textContent = 'Offline (Conta Local)';
        desc.textContent = 'Seus dados estão salvos apenas neste dispositivo.';
        btnLogin.style.display = 'flex';
        btnLogout.style.display = 'none';
    }
}

function getOAuthRedirectUrl() {
    if (window.NexusAndroid && typeof window.NexusAndroid.getOAuthRedirect === 'function') {
        return window.NexusAndroid.getOAuthRedirect();
    }
    if (window.location.protocol === 'file:') {
        return 'com.nexus.mobile://auth/callback';
    }
    return window.location.origin + window.location.pathname;
}

window.handleOAuthCallback = async function(callbackUrl) {
    if (!window.nexusSupabase || !callbackUrl) return;
    try {
        const parsed = new URL(callbackUrl.replace('com.nexus.mobile://', 'https://local/'));
        const code = parsed.searchParams.get('code');
        if (code) {
            const { error } = await window.nexusSupabase.auth.exchangeCodeForSession(code);
            if (error) showToast('Erro OAuth: ' + error.message);
            else {
                showToast('Login realizado com sucesso!');
                if (typeof forceSyncData === 'function') forceSyncData();
            }
            return;
        }
        const hashIdx = callbackUrl.indexOf('#');
        if (hashIdx > -1) {
            const hashParams = new URLSearchParams(callbackUrl.substring(hashIdx + 1));
            const access_token = hashParams.get('access_token');
            const refresh_token = hashParams.get('refresh_token');
            if (access_token && refresh_token) {
                const { error } = await window.nexusSupabase.auth.setSession({ access_token, refresh_token });
                if (error) showToast('Erro OAuth: ' + error.message);
                else showToast('Login realizado com sucesso!');
            }
        }
    } catch (e) {
        console.error('OAuth callback error:', e);
        showToast('Falha ao processar login.');
    }
};

async function loginWithGoogle() {
    if (!isNetworkOnline()) {
        showToast("Sem conexão com a internet.");
        return;
    }
    if (!window.nexusSupabase) {
        showToast("Servidor indisponível (Offline).");
        return;
    }
    const redirectTo = getOAuthRedirectUrl();
    const useExternalBrowser = !!(window.NexusAndroid && typeof window.NexusAndroid.openOAuthUrl === 'function');
    const { data, error } = await window.nexusSupabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
            redirectTo,
            skipBrowserRedirect: useExternalBrowser
        }
    });
    if (error) {
        showToast("Erro no login: " + error.message);
        return;
    }
    if (useExternalBrowser && data?.url) {
        window.NexusAndroid.openOAuthUrl(data.url);
        showToast("Complete o login no navegador...");
    }
}

async function logoutGoogle() {
    if (!window.nexusSupabase) return;
    const { error } = await window.nexusSupabase.auth.signOut();
    if (!error) {
        currentUser = null;
        updateSettingsUI();
        showToast("Você saiu da conta.");
    }
}

// Intercept pushChangesToSupabase — unified via syncData
window.pushChangesToSupabase = syncData;

function forceSyncData() {
    if (!isNetworkOnline()) {
        showToast("Sem conexão — sincronização indisponível.");
        return;
    }
    showToast("Sincronizando com a Nuvem...");
    syncData().then(() => {
        showToast("Sincronização concluída!");
    }).catch(() => {
        showToast("Sincronização indisponível — modo offline ativo.");
    });
}

window.forceSyncData = forceSyncData;
window.loginWithGoogle = loginWithGoogle;
window.logoutGoogle = logoutGoogle;
window.handleOAuthCallback = window.handleOAuthCallback;

window.triggerOcrCamera = function() {
    if (window.AndroidNative && typeof window.AndroidNative.openNativeCamera === 'function') {
        window.AndroidNative.openNativeCamera();
        showToast('Abrindo câmera...');
    } else {
        showToast('Câmera disponível apenas no app Android.');
    }
};

window.onNativeCameraResult = function(dataUrl) {
    if (!dataUrl) return;
    const editor = document.getElementById('note-content-rich');
    if (editor) {
        const img = document.createElement('img');
        img.src = dataUrl;
        img.style.maxWidth = '100%';
        img.style.borderRadius = '8px';
        editor.appendChild(img);
        showToast('Foto inserida na nota.');
    } else {
        showToast('Foto capturada — abra o editor de notas para inserir.');
    }
};

// ─── ENEM Quiz (mobile) ───────────────────────────────────────────

const ENEM_QUIZ_QUESTIONS = [
    { area: 'Matemática', stem: 'Uma família reduziu o consumo mensal de energia de 240 kWh para 204 kWh. Qual foi a redução percentual?', options: ['12%', '15%', '18%', '36%'], correct_index: 1, explanation: 'A redução foi de 36 kWh. 36/240 = 15%.' },
    { area: 'Matemática', stem: 'Em uma função afim f(x)=2x+3, qual é o valor de f(5)?', options: ['10', '11', '13', '15'], correct_index: 2, explanation: 'f(5)=2*5+3=13.' },
    { area: 'Matemática', stem: 'Um reservatório comporta 1200 litros e está com 35% da capacidade. Quantos litros faltam para enchê-lo?', options: ['420', '650', '780', '900'], correct_index: 2, explanation: '35% de 1200 = 420. Faltam 780 litros.' },
    { area: 'Português', stem: "Na frase 'Ela estudou muito, portanto foi bem na prova', a palavra 'portanto' indica:", options: ['oposição', 'conclusão', 'adição', 'condição'], correct_index: 1, explanation: "'Portanto' introduz uma conclusão." },
    { area: 'Português', stem: 'Em textos dissertativo-argumentativos, a tese é:', options: ['um exemplo secundário', 'a opinião central defendida', 'a citação obrigatória', 'o resumo final'], correct_index: 1, explanation: 'A tese é o ponto de vista central do texto.' },
    { area: 'Português', stem: "A expressão 'chuva de ideias' é um exemplo de linguagem:", options: ['literal', 'figurada', 'técnica', 'jurídica'], correct_index: 1, explanation: 'Usa sentido figurado.' },
    { area: 'Ciências da Natureza', stem: 'Durante a fotossíntese, a fase clara produz principalmente:', options: ['glicose e oxigênio', 'ATP e NADPH', 'DNA e RNA', 'sais minerais'], correct_index: 1, explanation: 'A fase clara produz ATP e NADPH.' },
    { area: 'Ciências da Natureza', stem: 'Ao ligar vários aparelhos em uma mesma tomada, o risco de aquecimento aumenta por:', options: ['da queda da gravidade', 'do aumento da corrente elétrica', 'da redução da frequência', 'da ausência de tensão'], correct_index: 1, explanation: 'Mais aparelhos = maior corrente = mais aquecimento.' },
    { area: 'Ciências da Natureza', stem: 'A mitocôndria é associada principalmente à:', options: ['digestão intracelular', 'respiração celular', 'fotossíntese', 'síntese de proteínas'], correct_index: 1, explanation: 'Mitocôndrias produzem ATP via respiração celular.' },
    { area: 'Ciências Humanas', stem: 'A Revolução Industrial intensificou a urbanização porque:', options: ['eliminou todas as fábricas', 'concentrou empregos nas cidades', 'proibiu o comércio', 'reduziu a produção'], correct_index: 1, explanation: 'Fábricas nas cidades atraíram trabalhadores.' },
    { area: 'Ciências Humanas', stem: 'No Brasil, a política do café com leite relacionava-se a elites de:', options: ['São Paulo e Minas Gerais', 'Amazonas e Pará', 'Bahia e Pernambuco', 'Rio Grande do Sul e Ceará'], correct_index: 0, explanation: 'Café (SP) e leite (MG).' },
    { area: 'Ciências Humanas', stem: 'O conceito de cidadania envolve direitos:', options: ['apenas privados', 'civis, políticos e sociais', 'somente comerciais', 'exclusivos de governantes'], correct_index: 1, explanation: 'Cidadania = direitos + deveres na vida coletiva.' }
];

let _quizQuestions = [], _quizIdx = 0, _quizCorrect = 0, _quizAttemptId = null, _quizTimerId = null, _quizSeconds = 0, _quizAnswers = [];

function formatQuizTime(s) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return (m < 10 ? '0' : '') + m + ':' + (sec < 10 ? '0' : '') + sec;
}

window.openQuiz = function() {
    document.getElementById('quiz-view').style.display = 'flex';
    document.getElementById('quiz-setup').style.display = 'block';
    document.getElementById('quiz-play').style.display = 'none';
    document.getElementById('quiz-done').style.display = 'none';
};

window.closeQuiz = function() {
    if (_quizTimerId) clearInterval(_quizTimerId);
    document.getElementById('quiz-view').style.display = 'none';
};

window.startQuiz = function() {
    const area = document.getElementById('quiz-area-sel')?.value || '';
    const count = parseInt(document.getElementById('quiz-mode-sel')?.value || '5', 10);
    let pool = ENEM_QUIZ_QUESTIONS.slice();
    if (area) pool = pool.filter(q => q.area === area);
    pool.sort(() => Math.random() - 0.5);
    _quizQuestions = pool.slice(0, Math.min(count, pool.length));
    if (!_quizQuestions.length) {
        showToast('Nenhuma questão para esta área.');
        return;
    }
    _quizIdx = 0;
    _quizCorrect = 0;
    _quizSeconds = 0;
    _quizAnswers = [];
    _quizAttemptId = 'qa_' + Date.now();
    if (_quizTimerId) clearInterval(_quizTimerId);
    _quizTimerId = setInterval(() => {
        _quizSeconds++;
        const t = document.getElementById('quiz-timer');
        if (t) t.textContent = formatQuizTime(_quizSeconds);
    }, 1000);
    document.getElementById('quiz-setup').style.display = 'none';
    document.getElementById('quiz-play').style.display = 'block';
    document.getElementById('quiz-done').style.display = 'none';
    renderQuizQuestion();
};

function renderQuizQuestion() {
    const play = document.getElementById('quiz-play');
    if (_quizIdx >= _quizQuestions.length) {
        finishQuiz();
        return;
    }
    const q = _quizQuestions[_quizIdx];
    play.innerHTML = `
        <div class="quiz-card glass">
            <div class="quiz-meta">
                <span>Questão ${_quizIdx + 1}/${_quizQuestions.length} · ${escapeHtml(q.area)}</span>
                <span id="quiz-timer" class="quiz-timer">${formatQuizTime(_quizSeconds)}</span>
            </div>
            <p class="quiz-stem">${escapeHtml(q.stem)}</p>
            <div class="quiz-options">
                ${q.options.map((o, i) => `<button type="button" class="quiz-opt" data-i="${i}">${escapeHtml(o)}</button>`).join('')}
            </div>
        </div>`;
    play.querySelectorAll('.quiz-opt').forEach(btn => {
        btn.onclick = () => onQuizPick(parseInt(btn.dataset.i, 10));
    });
}

function onQuizPick(chosen) {
    const q = _quizQuestions[_quizIdx];
    const ok = chosen === q.correct_index;
    if (ok) _quizCorrect++;
    _quizAnswers.push({ question: q.stem, area: q.area, chosen, correct_index: q.correct_index, ok, explanation: q.explanation });
    _quizIdx++;
    renderQuizQuestion();
}

function finishQuiz() {
    if (_quizTimerId) clearInterval(_quizTimerId);
    const total = _quizQuestions.length;
    const score = total ? Math.round((_quizCorrect / total) * 100) : 0;
    const attempt = {
        id: _quizAttemptId,
        area: document.getElementById('quiz-area-sel')?.value || 'Todas',
        score_pct: score,
        correct_count: _quizCorrect,
        total_count: total,
        duration_sec: _quizSeconds,
        finished_at: new Date().toISOString(),
        answers_json: JSON.stringify(_quizAnswers)
    };
    LocalDB.upsert('quiz_attempts', attempt);
    awardXP(Math.round(score / 5), 'Quiz ENEM: ' + score + '%');
    loadStudyStats();

    document.getElementById('quiz-play').style.display = 'none';
    const done = document.getElementById('quiz-done');
    done.style.display = 'block';
    const cls = score >= 70 ? 'good' : score >= 50 ? 'mid' : 'bad';
    const wrong = _quizAnswers.filter(a => !a.ok);
    done.innerHTML = `
        <div class="quiz-result glass">
            <h3>Resultado</h3>
            <div class="quiz-score ${cls}">${score}%</div>
            <p>${_quizCorrect}/${total} acertos · ${formatQuizTime(_quizSeconds)}</p>
            ${wrong.length ? `<div class="quiz-review">${wrong.slice(0, 3).map(w => `
                <div class="quiz-review-item">
                    <p>${escapeHtml(w.question)}</p>
                    <small>${escapeHtml(w.explanation)}</small>
                </div>`).join('')}</div>` : '<p style="color:var(--accent-green)">Perfeito! 🎉</p>'}
            <div class="quiz-result-actions">
                <button class="quiz-btn" onclick="quizToFlashcards()"><i class="fa-solid fa-clone"></i> Cards dos erros</button>
                <button class="quiz-btn secondary" onclick="startQuiz()">De novo</button>
                <button class="quiz-btn ghost" onclick="closeQuiz()">Fechar</button>
            </div>
        </div>`;
}

window.quizToFlashcards = function() {
    const wrong = _quizAnswers.filter(a => !a.ok);
    if (!wrong.length) { showToast('Nenhum erro para revisar.'); return; }
    wrong.forEach(w => {
        createFlashcard(w.question, w.explanation + ' (Resposta: ' + (ENEM_QUIZ_QUESTIONS.find(q => q.stem === w.question)?.options[w.correct_index] || '') + ')', null);
    });
    showToast(wrong.length + ' flashcards criados!');
    closeQuiz();
    showFlashcards();
};

window.ensureChartJs = async function() {
    if (typeof Chart !== 'undefined') return true;
    return new Promise((resolve) => {
        const s = document.createElement('script');
        s.src = 'https://cdn.jsdelivr.net/npm/chart.js';
        s.onload = () => resolve(true);
        s.onerror = () => resolve(false);
        document.head.appendChild(s);
    });
};

// ─── Settings: Appearance & Local Data ───────────────────────────

function changeThemeColor(colorHex) {
    document.documentElement.style.setProperty('--accent-primary', colorHex);
    document.documentElement.style.setProperty('--accent-blue', colorHex);
    document.documentElement.style.setProperty('--accent-purple', colorHex);
    localStorage.setItem('nexus_theme_color', colorHex);
    
    // Attempt to re-render charts to pick up new colors if active
    if (typeof renderFinanceCharts === 'function') renderFinanceCharts();
    if (typeof renderHabitCharts === 'function') renderHabitCharts();
    if (typeof renderStudyCharts === 'function') renderStudyCharts();
}

// Load saved theme on startup
document.addEventListener('DOMContentLoaded', () => {
    const savedColor = localStorage.getItem('nexus_theme_color');
    if (savedColor) changeThemeColor(savedColor);
});

function exportLocalDB() {
    const keys = Object.keys(localStorage);
    const dump = {};
    keys.forEach(k => {
        if (k.startsWith('nexus_') || k === 'habits' || k === 'tasks' || k === 'transactions' || k === 'notes') {
            dump[k] = localStorage.getItem(k);
        }
    });
    const blob = new Blob([JSON.stringify(dump, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nexus_backup_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
}

function importLocalDB(event) {
    const file = event.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const dump = JSON.parse(e.target.result);
            Object.keys(dump).forEach(k => {
                localStorage.setItem(k, dump[k]);
            });
            alert("Backup Restaurado com Sucesso! O aplicativo será recarregado.");
            window.location.reload();
        } catch (err) {
            alert("Erro ao importar arquivo JSON: Arquivo inválido.");
        }
    };
    reader.readAsText(file);
}

function clearLocalDB() {
    if (confirm("ATENÇÃO: Você está prestes a apagar TODOS os seus dados locais. Se eles não estiverem na nuvem, você os perderá para sempre. Tem certeza?")) {
        localStorage.clear();
        alert("Dados locais apagados.");
        window.location.reload();
    }
}

// ================================================================
