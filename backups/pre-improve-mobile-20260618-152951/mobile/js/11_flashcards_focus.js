// FLASHCARDS (SRS - Anki Style) & POMODORO TIMER
// ================================================================

let _pomoInterval = null;
let _pomoTimeLeft = 25 * 60;
let _isPomoRunning = false;

// ─── Pomodoro Timer ──────────────────────────────────────────────

function initPomodoroUI() {
    const timeEl = document.getElementById('pomo-time');
    if (timeEl) {
        const m = Math.floor(_pomoTimeLeft / 60).toString().padStart(2, '0');
        const s = (_pomoTimeLeft % 60).toString().padStart(2, '0');
        timeEl.textContent = `${m}:${s}`;
    }
}

function startPomodoro() {
    if (_isPomoRunning) return;
    _isPomoRunning = true;
    document.getElementById('pomo-btn-start').style.display = 'none';
    document.getElementById('pomo-btn-pause').style.display = 'block';

    _pomoInterval = setInterval(() => {
        _pomoTimeLeft--;
        initPomodoroUI();
        if (_pomoTimeLeft <= 0) {
            finishPomodoro();
        }
    }, 1000);
}

function pausePomodoro() {
    _isPomoRunning = false;
    clearInterval(_pomoInterval);
    document.getElementById('pomo-btn-start').style.display = 'block';
    document.getElementById('pomo-btn-pause').style.display = 'none';
}

function resetPomodoro() {
    pausePomodoro();
    _pomoTimeLeft = 25 * 60;
    initPomodoroUI();
}

function finishPomodoro() {
    pausePomodoro();
    _pomoTimeLeft = 5 * 60;
    initPomodoroUI();
    const label = document.getElementById('pomo-mode-label');
    if (label) label.textContent = 'DESCANSO';

    LocalDB.upsert('pomo_sessions', {
        id: Date.now(),
        type: 'focus',
        duration_minutes: 25,
        session_date: new Date().toISOString().split('T')[0]
    });
    awardXP(20, 'Sessao Pomodoro completa');
    showToast('Pomodoro concluido! +20 XP');
    renderPomodoroHistory();
}

function renderPomodoroHistory() {
    const list = document.getElementById('pomo-history');
    if (!list) return;
    const ph = LocalDB.getAll('pomodoros') || [];
    const today = new Date().toISOString().split('T')[0];
    const todayPomos = ph.filter(p => p.date.startsWith(today));
    
    list.innerHTML = '';
    if (!todayPomos.length) {
        list.innerHTML = '<div style="color:var(--text-secondary);font-size:0.85rem">Nenhum pomodoro hoje ainda.</div>';
        return;
    }
    todayPomos.forEach((p, i) => {
        list.innerHTML += `<div style="background:rgba(255,255,255,0.05);padding:8px 12px;border-radius:8px;font-size:0.85rem;color:white;display:flex;justify-content:space-between">
            <span>🍅 Sessão ${i+1}</span>
            <span style="color:var(--accent-green)">+50 XP</span>
        </div>`;
    });
    const dots = document.getElementById('pomo-dots');
    if (dots) {
        dots.innerHTML = todayPomos.map(() => '<i class="fa-solid fa-circle" style="color:var(--accent-pink);font-size:0.6rem"></i>').join('');
    }
}

function closePomodoro() {
    document.getElementById('pomodoro-view').style.display = 'none';
}

// Intercept old showPomodoro if exists
const _oldShowPomodoro = window.showPomodoro;
window.showPomodoro = function() {
    document.getElementById('pomodoro-view').style.display = 'flex';
    initPomodoroUI();
    renderPomodoroHistory();
};

// ─── Flashcards (SuperMemo-2 SRS) ────────────────────────────────

let _flashcardQueue = [];
let _currentCardIndex = 0;
let _fcKnown = 0;
let _fcUnknown = 0;
let _fcShowingBack = false;

function initFlashcardsDB() {
    if (!localStorage.getItem('flashcards')) {
        LocalDB.saveAll('flashcards', []);
    }
}

function createFlashcard(front, back, noteId = null) {
    LocalDB.upsert('flashcards', {
        id: 'fc_' + Date.now() + Math.floor(Math.random() * 1000),
        note_id: noteId,
        noteId: noteId,
        front: front,
        back: back,
        interval: 0,
        repetition: 0,
        repetitions: 0,
        efactor: 2.5,
        ease_factor: 2.5,
        next_review: new Date().toISOString(),
        nextReviewDate: new Date().toISOString()
    });
}

function normalizeFlashcard(card) {
    if (!card.nextReviewDate && card.next_review) card.nextReviewDate = card.next_review;
    if (!card.next_review && card.nextReviewDate) card.next_review = card.nextReviewDate;
    return card;
}

function getDueFlashcards() {
    const cards = (LocalDB.getAll('flashcards') || []).map(normalizeFlashcard);
    const now = new Date().toISOString();
    return cards.filter(c => !c.is_deleted && (!c.nextReviewDate || c.nextReviewDate <= now));
}

window.showFlashcards = function() {
    initFlashcardsDB();
    _flashcardQueue = getDueFlashcards();

    if (!LocalDB.getAll('flashcards').filter(c => !c.is_deleted).length) {
        showToast('Nenhum flashcard. Crie via notas ou Quiz ENEM.');
        return;
    }
    if (!_flashcardQueue.length) {
        showToast('Nenhum card pendente hoje. Volte amanhã!');
        return;
    }

    _currentCardIndex = 0;
    _fcKnown = 0;
    _fcUnknown = 0;
    
    document.getElementById('flashcard-view').style.display = 'flex';
    renderCurrentFlashcard();
};

window.closeFlashcards = function() {
    document.getElementById('flashcard-view').style.display = 'none';
};

function renderCurrentFlashcard() {
    const frontEl = document.getElementById('fc-front');
    const backEl = document.getElementById('fc-back');
    const counter = document.getElementById('fc-counter');
    
    document.getElementById('fc-known-count').textContent = _fcKnown;
    document.getElementById('fc-unknown-count').textContent = _fcUnknown;
    
    if (_currentCardIndex >= _flashcardQueue.length) {
        frontEl.innerHTML = "🎉<br><br>Você revisou todos os flashcards pendentes!";
        backEl.style.display = 'none';
        counter.textContent = "Finalizado";
        return;
    }
    
    const card = _flashcardQueue[_currentCardIndex];
    counter.textContent = `${_currentCardIndex + 1} / ${_flashcardQueue.length}`;
    
    frontEl.innerHTML = card.front.replace(/\n/g, '<br>');
    backEl.innerHTML = card.back.replace(/\n/g, '<br>');
    backEl.style.display = 'none';
    _fcShowingBack = false;
    
    // Reset card UI
    const cardDiv = document.getElementById('flashcard-card');
    cardDiv.style.transform = 'none';
    cardDiv.style.border = '1px solid var(--accent-purple)';
}

window.flipFlashcard = function() {
    if (_currentCardIndex >= _flashcardQueue.length) return;
    const backEl = document.getElementById('fc-back');
    const cardDiv = document.getElementById('flashcard-card');
    
    if (!_fcShowingBack) {
        _fcShowingBack = true;
        backEl.style.display = 'block';
        cardDiv.style.transform = 'scale(1.02)';
        cardDiv.style.border = '1px solid var(--accent-blue)';
    }
};

window.answerFlashcard = function(isCorrect) {
    if (_currentCardIndex >= _flashcardQueue.length) return;
    if (!_fcShowingBack) {
        // Must flip before answering
        window.flipFlashcard();
        return;
    }
    
    const card = _flashcardQueue[_currentCardIndex];
    
    // SM-2 Algorithm Implementation
    let quality = isCorrect ? 4 : 0; // Simplified quality (0=blackout, 4=good)
    
    if (quality >= 3) {
        if (card.repetition === 0) {
            card.interval = 1;
        } else if (card.repetition === 1) {
            card.interval = 6;
        } else {
            card.interval = Math.round(card.interval * card.efactor);
        }
        card.repetition++;
        _fcKnown++;
        if (typeof addXP === 'function') addXP(5); // +5 XP for correct
    } else {
        card.repetition = 0;
        card.interval = 1;
        _fcUnknown++;
    }
    
    card.efactor = card.efactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02));
    if (card.efactor < 1.3) card.efactor = 1.3;
    
    // Calculate next review date
    const nextDate = new Date();
    nextDate.setDate(nextDate.getDate() + card.interval);
    card.nextReviewDate = nextDate.toISOString();
    card.next_review = card.nextReviewDate;
    card.ease_factor = card.efactor;
    card.repetitions = card.repetition;
    LocalDB.upsert('flashcards', card);

    const cardDiv = document.getElementById('flashcard-card');
    cardDiv.classList.add(isCorrect ? 'fc-swipe-right' : 'fc-swipe-left');
    
    setTimeout(() => {
        cardDiv.classList.remove('fc-swipe-right', 'fc-swipe-left');
        _currentCardIndex++;
        renderCurrentFlashcard();
    }, 300);
};

// ─── Generate Flashcards via Jarvis ──────────────────────────────

function insertGenerateFlashcardsButton() {
    const jarvisTabs = document.querySelector('#jarvis-panel .jarvis-tab') ? document.querySelector('#jarvis-panel .jarvis-tab').parentElement : null;
    if (jarvisTabs && !document.getElementById('btn-jarvis-fc')) {
        const btn = document.createElement('button');
        btn.id = 'btn-jarvis-fc';
        btn.className = 'jarvis-tab';
        btn.innerHTML = '<i class="fa-solid fa-clone"></i> Criar Cards';
        btn.onclick = () => {
            setJarvisMode('generate_flashcards', btn);
        };
        jarvisTabs.appendChild(btn);
    }
}

// Intercept runJarvisAction to handle flashcard generation
const _origRunJarvisAction = window.runJarvisAction;
window.runJarvisAction = async function() {
    if (typeof _jarvisMode !== 'undefined' && _jarvisMode === 'generate_flashcards') {
        const prompt = document.getElementById('jarvis-prompt')?.value?.trim();
        if (!prompt) { alert('Insira o texto base para gerar os flashcards.'); return; }
        
        document.getElementById('jarvis-input-area').style.display = 'none';
        document.getElementById('jarvis-loading').style.display = 'block';
        
        // MOCK AI GENERATION
        setTimeout(() => {
            const cards = [
                { f: `O que é: "${prompt.slice(0,10)}..."?`, b: "Conceito chave extraído do texto." },
                { f: "Quais os 3 pontos principais?", b: "1. Ponto A\n2. Ponto B\n3. Ponto C" }
            ];
            
            cards.forEach(c => createFlashcard(c.f, c.b));
            
            document.getElementById('jarvis-loading').style.display = 'none';
            document.getElementById('jarvis-result').style.display = 'block';
            document.getElementById('jarvis-result-text').innerHTML = `✅ ${cards.length} Flashcards gerados e adicionados ao seu baralho!`;
            document.getElementById('jarvis-input-area').style.display = 'block';
        }, 2000);
        return;
    }
    
    if (typeof _origRunJarvisAction === 'function') {
        _origRunJarvisAction();
    }
};

// ─── Notifications & Startup ──────────────────────────────────────

function checkPendingFlashcards() {
    const due = getDueFlashcards();
    if (due.length > 0) {
        showToast(`📚 Você tem ${due.length} flashcards pendentes para revisar!`, 5000);
        if ("Notification" in window && Notification.permission === 'granted') {
            new Notification('Nexus Studies', { body: `Você tem ${due.length} flashcards para revisar hoje!` });
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initFlashcardsDB();
    insertGenerateFlashcardsButton();
    
    // Request notification permission if not asked
    if ("Notification" in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
    
    setTimeout(checkPendingFlashcards, 3000);
});


// ================================================================
