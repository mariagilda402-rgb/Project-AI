# Mobile Studies + Jarvis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework Nexus Mobile Studies into a useful mobile-first study cockpit with visible SRS, subject workflows, note actions, and contextual Jarvis that does not depend on the desktop app being open.

**Architecture:** Keep the existing `mobile/` WebView SPA and avoid a broad rewrite. Add small helper functions near the active Studies 3.0 block in `mobile/app.js`, update targeted markup in `mobile/index.html`, and add focused CSS classes in `mobile/style.css`. Desktop/backend calls remain optional; local notes, subjects, flashcards, and review must keep working through `LocalDB`.

**Tech Stack:** Plain HTML/CSS/JavaScript, Android WebView, `LocalDB`, existing Font Awesome icons, ADB deployment through `scripts/push_mobile_bundle_adb.py`.

---

## File Structure

- Modify `mobile/index.html`
  - Replace the top portion of `view-studies` so the first fold is an action-oriented learning cockpit.
  - Add containers for study today summary, primary study actions, recent notes, and contextual Jarvis entry points.
  - Enrich `subject-detail-view` with subject summary, action buttons, and a flashcard count before the notes list.
  - Enrich the note editor bottom action row with study-specific actions.

- Modify `mobile/app.js`
  - Add `getStudyCollections()`, `getDueFlashcardsForNotebook()`, `getStudyTodaySummary()`, `renderStudyCockpit()`, `renderStudyRecentNotes()`, and `renderSubjectStudySummary()` near the active Studies 3.0 code.
  - Extend the final `window.loadStudies` wrapper at the bottom of the Studies 3.0 section so it renders the new cockpit after existing stats/grid/chart logic.
  - Update `loadSubjectsGrid()` and `openSubjectDetail()` to surface cards due, notes, last activity, and study actions.
  - Add explicit actions: `openStudyJarvis()`, `openSubjectJarvis()`, `openNoteJarvisAction()`, `reviewSubjectFlashcards()`, `generateFlashcardsFromCurrentNote()`, and `generateFlashcardsFromSubject()`.
  - Replace new `alert()`/`confirm()` usage with `showInAppNotification()`, `showToast()`, or `window.showConfirm()` where confirmation is needed.

- Modify `mobile/style.css`
  - Add classes for the study cockpit, primary action grid, subject progress chips, recent note cards, subject detail header, and editor Jarvis action strip.
  - Keep dimensions stable on 720px-wide Android screens and avoid nested cards.

- Use existing validation/deploy files
  - `scripts/push_mobile_bundle_adb.py` for final device deploy.
  - ADB commands for screenshots after deployment.

---

### Task 1: Baseline Checks And Device Snapshot

**Files:**
- Read: `mobile/index.html`
- Read: `mobile/app.js`
- Read: `mobile/style.css`
- Verify: connected Android device through ADB

- [ ] **Step 1: Confirm JavaScript parses before edits**

Run:

```powershell
node --check mobile/app.js
```

Expected: exit code `0` and no syntax errors.

- [ ] **Step 2: Confirm the connected Android package**

Run:

```powershell
$serial = (adb devices | Select-String -Pattern '^\S+\s+device$' | Select-Object -First 1).ToString().Split()[0]
adb -s $serial shell cmd package resolve-activity --brief com.nexus.mobile
```

Expected output includes:

```text
com.nexus.mobile/.MainActivity
```

- [ ] **Step 3: Capture current Studies screen as a before image**

Run:

```powershell
$serial = (adb devices | Select-String -Pattern '^\S+\s+device$' | Select-Object -First 1).ToString().Split()[0]
adb -s $serial shell screencap /sdcard/nexus_before_studies.raw
adb -s $serial pull /sdcard/nexus_before_studies.raw .superpowers\nexus_before_studies.raw
```

Expected: raw file is pulled successfully. Convert only if visual comparison is needed:

```powershell
@'
from pathlib import Path
import struct
from PIL import Image
raw = Path('.superpowers/nexus_before_studies.raw').read_bytes()
w,h,fmt = struct.unpack_from('<III', raw, 0)
Image.frombytes('RGBA', (w,h), raw[16:16+w*h*4]).save('.superpowers/nexus_before_studies.png')
print(f'{w}x{h} fmt={fmt}')
'@ | python -
```

Expected output:

```text
720x1600 fmt=1
```

---

### Task 2: Add Study Cockpit Markup

**Files:**
- Modify: `mobile/index.html`
- Test: `node --check mobile/app.js`

- [ ] **Step 1: Locate the active Studies stat block**

Open `mobile/index.html` around the `view-studies` section. The current order is:

```html
<div class="study-stats-bar">
...
</div>

<!-- Studies Analytics Dashboard -->
<div class="glass" style="margin-bottom:20px;padding:15px;border-radius:16px">
...
</div>
```

- [ ] **Step 2: Insert the cockpit containers between the stats bar and analytics chart**

Add this markup immediately after the closing `</div>` for `.study-stats-bar`:

```html
<section class="study-cockpit" id="study-cockpit">
    <div class="study-cockpit-head">
        <div>
            <span class="study-kicker">Hoje nos estudos</span>
            <h3 id="study-today-title">Pronto para estudar</h3>
        </div>
        <button class="study-jarvis-chip" onclick="openStudyJarvis()">
            <i class="fa-solid fa-wand-magic-sparkles"></i>
            Jarvis
        </button>
    </div>
    <p class="study-today-copy" id="study-today-copy">Carregando suas revisoes, notas e materias...</p>
    <div class="study-primary-actions">
        <button class="study-primary-action review" onclick="showFlashcards()">
            <i class="fa-solid fa-layer-group"></i>
            <span>Revisar agora</span>
            <small id="study-due-count">0 cards</small>
        </button>
        <button class="study-primary-action note" onclick="openNoteEditor(null,currentNotebookId)">
            <i class="fa-solid fa-pen-to-square"></i>
            <span>Nova nota</span>
            <small>capturar ideia</small>
        </button>
        <button class="study-primary-action capture" onclick="triggerOcrCamera()">
            <i class="fa-solid fa-camera"></i>
            <span>Capturar</span>
            <small>foto para nota</small>
        </button>
        <button class="study-primary-action quiz" onclick="openQuiz()">
            <i class="fa-solid fa-bolt"></i>
            <span>Quiz rapido</span>
            <small>praticar</small>
        </button>
    </div>
</section>

<section class="study-recent-panel" id="study-recent-panel">
    <div class="study-section-row">
        <h3 class="section-title">Continuar</h3>
        <button onclick="renderStudyNotesList('recent', null)">ver recentes</button>
    </div>
    <div id="study-recent-notes" class="study-recent-notes"></div>
</section>
```

- [ ] **Step 3: Move analytics below active learning**

Keep the existing analytics chart, but it should remain after the new cockpit and recent notes panel. Do not remove the chart in this task.

- [ ] **Step 4: Run parser check**

Run:

```powershell
node --check mobile/app.js
```

Expected: exit code `0`.

---

### Task 3: Add Study Cockpit Styling

**Files:**
- Modify: `mobile/style.css`
- Verify: visual screenshot on 720x1600 device after deploy

- [ ] **Step 1: Append cockpit styles near existing Studies styles**

Add this block after the existing `.study-stat-label` rules or near the `.subjects-grid` block:

```css
.study-cockpit {
    border: 1px solid rgba(255,255,255,0.09);
    background: linear-gradient(135deg, rgba(18,22,34,0.96), rgba(13,42,42,0.88));
    border-radius: 18px;
    padding: 16px;
    margin: 14px 0 16px;
    box-shadow: 0 18px 40px rgba(0,0,0,0.24);
}

.study-cockpit-head,
.study-section-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.study-kicker {
    display: block;
    color: var(--accent-green);
    font-size: 0.72rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0;
    margin-bottom: 4px;
}

.study-cockpit h3 {
    margin: 0;
    color: white;
    font-size: 1.08rem;
}

.study-today-copy {
    margin: 10px 0 14px;
    color: var(--text-secondary);
    font-size: 0.88rem;
    line-height: 1.45;
}

.study-jarvis-chip,
.study-section-row button {
    border: 1px solid rgba(108,92,231,0.55);
    background: rgba(108,92,231,0.16);
    color: #a99cff;
    border-radius: 999px;
    padding: 8px 12px;
    font: inherit;
    font-size: 0.8rem;
    font-weight: 800;
    cursor: pointer;
    white-space: nowrap;
}

.study-primary-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
}

.study-primary-action {
    min-height: 86px;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
    background: rgba(255,255,255,0.05);
    color: white;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: flex-start;
    padding: 12px;
    font: inherit;
    cursor: pointer;
    text-align: left;
}

.study-primary-action i {
    font-size: 1.1rem;
    color: var(--accent-blue);
}

.study-primary-action.review i { color: var(--accent-green); }
.study-primary-action.capture i { color: #fbbf24; }
.study-primary-action.quiz i { color: #fb7185; }

.study-primary-action span {
    font-size: 0.92rem;
    font-weight: 850;
}

.study-primary-action small {
    color: var(--text-secondary);
    font-size: 0.72rem;
}

.study-recent-panel {
    margin: 0 0 16px;
}

.study-recent-notes {
    display: flex;
    gap: 10px;
    overflow-x: auto;
    padding: 2px 0 4px;
    scroll-snap-type: x proximity;
}

.study-recent-note {
    min-width: 210px;
    max-width: 230px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.045);
    border-radius: 14px;
    padding: 12px;
    scroll-snap-align: start;
    cursor: pointer;
}

.study-recent-note b {
    display: block;
    color: white;
    font-size: 0.88rem;
    line-height: 1.25;
    margin-bottom: 8px;
}

.study-recent-note span {
    display: block;
    color: var(--text-secondary);
    font-size: 0.72rem;
    line-height: 1.35;
}
```

- [ ] **Step 2: Confirm CSS contains no negative letter spacing in new block**

Run:

```powershell
rg -n "letter-spacing:\\s*-" mobile/style.css
```

Expected: no matches from the new study cockpit block.

---

### Task 4: Add Study Data Helpers

**Files:**
- Modify: `mobile/app.js`
- Test: `node --check mobile/app.js`

- [ ] **Step 1: Insert helper functions before `function loadStudies()` in Studies 3.0**

Find this block:

```javascript
const MOOD_COLORS = ['', '#ef4444', '#f97316', '#6b7280', '#10b981', '#8b5cf6'];

function loadStudies() {
```

Insert:

```javascript
function getStudyCollections() {
    const notebooks = (LocalDB.get('study_notebooks') || []).filter(n => !n.is_deleted);
    const notes = (LocalDB.get('study_notes') || []).filter(n => !n.is_deleted);
    const cards = (LocalDB.getAll ? LocalDB.getAll('flashcards') : LocalDB.get('flashcards') || []).filter(c => !c.is_deleted);
    return { notebooks, notes, cards };
}

function getCardNotebookId(card, notesById) {
    const noteId = card.note_id || card.noteId || card.source_note_id || '';
    const note = notesById.get(String(noteId));
    return note ? String(note.notebook_id || '') : String(card.notebook_id || card.subject_id || '');
}

function getDueStudyCards(cards) {
    const now = new Date().toISOString();
    return cards.map(c => typeof normalizeFlashcard === 'function' ? normalizeFlashcard(c) : c)
        .filter(c => !c.is_deleted && (!c.nextReviewDate || c.nextReviewDate <= now));
}

function getDueFlashcardsForNotebook(notebookId) {
    const { notes, cards } = getStudyCollections();
    const notesById = new Map(notes.map(n => [String(n.id), n]));
    return getDueStudyCards(cards).filter(card => getCardNotebookId(card, notesById) === String(notebookId));
}

function getStudyTodaySummary() {
    const { notebooks, notes, cards } = getStudyCollections();
    const dueCards = getDueStudyCards(cards);
    const sortedNotes = [...notes].sort((a, b) => (b.updated_at || b.created_at || '').localeCompare(a.updated_at || a.created_at || ''));
    const activeNotebooks = notebooks.filter(nb => notes.some(n => String(n.notebook_id) === String(nb.id)));
    return {
        notebooks,
        notes,
        cards,
        dueCards,
        recentNotes: sortedNotes.slice(0, 6),
        activeNotebooks,
        latestNote: sortedNotes[0] || null
    };
}
```

- [ ] **Step 2: Run parser check**

Run:

```powershell
node --check mobile/app.js
```

Expected: exit code `0`.

---

### Task 5: Render Study Cockpit And Recent Notes

**Files:**
- Modify: `mobile/app.js`
- Test: `node --check mobile/app.js`

- [ ] **Step 1: Add render functions after the helpers from Task 4**

Add:

```javascript
function renderStudyCockpit() {
    const summary = getStudyTodaySummary();
    const title = document.getElementById('study-today-title');
    const copy = document.getElementById('study-today-copy');
    const dueCount = document.getElementById('study-due-count');
    if (dueCount) {
        dueCount.textContent = `${summary.dueCards.length} card${summary.dueCards.length === 1 ? '' : 's'}`;
    }
    if (title) {
        if (summary.dueCards.length) title.textContent = `${summary.dueCards.length} revisao${summary.dueCards.length === 1 ? '' : 'es'} para hoje`;
        else if (summary.latestNote) title.textContent = 'Continue seu segundo cerebro';
        else title.textContent = 'Monte sua primeira materia';
    }
    if (copy) {
        if (summary.dueCards.length) {
            copy.textContent = 'Comece pela revisao SRS. Depois use Jarvis para explicar pontos fracos ou gerar novos cards.';
        } else if (summary.latestNote) {
            copy.textContent = `Ultima nota: ${summary.latestNote.title || 'Sem titulo'}. Continue escrevendo ou transforme em flashcards.`;
        } else {
            copy.textContent = 'Crie uma materia, escreva a primeira nota e deixe o Jarvis transformar conteudo em revisao.';
        }
    }
}

function renderStudyRecentNotes() {
    const container = document.getElementById('study-recent-notes');
    if (!container) return;
    const { recentNotes } = getStudyTodaySummary();
    if (!recentNotes.length) {
        container.innerHTML = '<div class="study-recent-note"><b>Nenhuma nota ainda</b><span>Crie uma nota dentro de uma materia para comecar seu second brain.</span></div>';
        return;
    }
    container.innerHTML = recentNotes.map(note => {
        const excerpt = (note.content || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 96);
        return `<div class="study-recent-note" onclick="openNoteEditor('${note.id}', '${note.notebook_id || ''}')">
            <b>${escapeHtml(note.title || 'Sem titulo')}</b>
            <span>${escapeHtml(excerpt || note.subject || 'Abrir nota')}</span>
        </div>`;
    }).join('');
}
```

- [ ] **Step 2: Update the final `window.loadStudies` wrapper**

Find the final wrapper near the end of the Studies 3.0 section:

```javascript
window.loadStudies = function() {
    if (typeof _loadStudiesOrig === 'function') _loadStudiesOrig();
    loadSubjectsGrid();
    if (typeof loadNotebooksGrid === 'function') loadNotebooksGrid();
    if (typeof ensureChartJs === 'function') ensureChartJs().then(() => setTimeout(renderStudyCharts, 100));
};
```

Replace it with:

```javascript
window.loadStudies = function() {
    if (typeof _loadStudiesOrig === 'function') _loadStudiesOrig();
    renderStudyCockpit();
    renderStudyRecentNotes();
    loadSubjectsGrid();
    if (typeof loadNotebooksGrid === 'function') loadNotebooksGrid();
    if (typeof ensureChartJs === 'function') ensureChartJs().then(() => setTimeout(renderStudyCharts, 100));
};
```

- [ ] **Step 3: Run parser check**

Run:

```powershell
node --check mobile/app.js
```

Expected: exit code `0`.

---

### Task 6: Upgrade Subject Cards And Subject Detail

**Files:**
- Modify: `mobile/index.html`
- Modify: `mobile/app.js`
- Modify: `mobile/style.css`
- Test: `node --check mobile/app.js`

- [ ] **Step 1: Add subject detail summary markup**

In `mobile/index.html`, inside `#subject-detail-view`, place this immediately after the `.view-header`:

```html
<div class="subject-study-summary" id="subject-study-summary"></div>
<div class="subject-study-actions">
    <button onclick="openNoteEditor(null,currentNotebookId)">
        <i class="fa-solid fa-pen-to-square"></i>
        Nova nota
    </button>
    <button onclick="reviewSubjectFlashcards()">
        <i class="fa-solid fa-layer-group"></i>
        Revisar
    </button>
    <button onclick="openSubjectJarvis()">
        <i class="fa-solid fa-wand-magic-sparkles"></i>
        Jarvis
    </button>
</div>
```

- [ ] **Step 2: Replace `loadSubjectsGrid()` card body**

In `mobile/app.js`, update the `grid.innerHTML = notebooks.map(nb => { ... })` body in `loadSubjectsGrid()` so each card computes due cards and latest note:

```javascript
grid.innerHTML = notebooks.map(nb => {
    const subjectNotes = notes.filter(n => String(n.notebook_id) === String(nb.id));
    const dueCount = getDueFlashcardsForNotebook(nb.id).length;
    const latest = subjectNotes.sort((a, b) => (b.updated_at || b.created_at || '').localeCompare(a.updated_at || a.created_at || ''))[0];
    const coverStyle = nb.cover_image ? `background-image:url('${nb.cover_image}')` : 'background:linear-gradient(135deg,#6c5ce7,#a29bfe)';
    return `<div class="subject-card" onclick="openSubjectDetail('${nb.id}')">
        <div class="subject-card-cover" style="${coverStyle}"></div>
        <div class="subject-card-body">
            <div class="subject-card-name">${nb.icon || ''} ${escapeHtml(nb.name)}</div>
            <div class="subject-card-count">${subjectNotes.length} nota${subjectNotes.length !== 1 ? 's' : ''} · ${dueCount} card${dueCount !== 1 ? 's' : ''} hoje</div>
            <div class="subject-card-latest">${escapeHtml(latest ? latest.title || 'Sem titulo' : 'Sem notas ainda')}</div>
        </div>
    </div>`;
}).join('');
```

- [ ] **Step 3: Add `renderSubjectStudySummary()`**

Add near the Studies render helpers:

```javascript
function renderSubjectStudySummary(notebookId) {
    const target = document.getElementById('subject-study-summary');
    if (!target) return;
    const { notebooks, notes, cards } = getStudyCollections();
    const nb = notebooks.find(n => String(n.id) === String(notebookId));
    const subjectNotes = notes.filter(n => String(n.notebook_id) === String(notebookId));
    const dueCards = getDueFlashcardsForNotebook(notebookId);
    const totalCards = cards.filter(card => {
        const notesById = new Map(notes.map(n => [String(n.id), n]));
        return getCardNotebookId(card, notesById) === String(notebookId);
    }).length;
    target.innerHTML = `<div>
        <span>${nb ? escapeHtml(nb.name) : 'Materia'}</span>
        <strong>${subjectNotes.length} nota${subjectNotes.length === 1 ? '' : 's'}</strong>
    </div>
    <div>
        <span>Memorizacao</span>
        <strong>${dueCards.length}/${totalCards} hoje</strong>
    </div>`;
}
```

- [ ] **Step 4: Call summary renderer from `openSubjectDetail()`**

In `openSubjectDetail(notebookId)`, after `view.style.display = 'block';`, add:

```javascript
renderSubjectStudySummary(notebookId);
```

- [ ] **Step 5: Add subject styles**

Append to `mobile/style.css`:

```css
.subject-card-latest {
    color: var(--text-secondary);
    font-size: 0.68rem;
    margin-top: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.subject-study-summary {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    padding: 0 16px 12px;
}

.subject-study-summary > div {
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.045);
    border-radius: 14px;
    padding: 12px;
}

.subject-study-summary span {
    display: block;
    color: var(--text-secondary);
    font-size: 0.72rem;
    margin-bottom: 6px;
}

.subject-study-summary strong {
    color: white;
    font-size: 1rem;
}

.subject-study-actions {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    padding: 0 16px 14px;
}

.subject-study-actions button {
    border: 1px solid rgba(108,92,231,0.42);
    background: rgba(108,92,231,0.12);
    color: #b7adff;
    border-radius: 12px;
    padding: 10px 6px;
    font: inherit;
    font-size: 0.78rem;
    font-weight: 800;
    cursor: pointer;
}

.subject-study-actions i {
    display: block;
    margin-bottom: 5px;
}
```

- [ ] **Step 6: Run parser check**

Run:

```powershell
node --check mobile/app.js
```

Expected: exit code `0`.

---

### Task 7: Add Contextual Jarvis Actions

**Files:**
- Modify: `mobile/index.html`
- Modify: `mobile/app.js`
- Modify: `mobile/style.css`
- Test: `node --check mobile/app.js`

- [ ] **Step 1: Replace the editor bottom action row with study actions**

In `mobile/index.html`, replace the current "Bottom Action Row" buttons with:

```html
<div class="editor-study-actions">
    <button onclick="triggerOcrCamera()">
        <i class="fa-solid fa-camera"></i>
        Capturar
    </button>
    <button onclick="openNoteJarvisAction('summarize_text')">
        <i class="fa-solid fa-wand-magic-sparkles"></i>
        Resumir
    </button>
    <button onclick="generateFlashcardsFromCurrentNote()">
        <i class="fa-solid fa-layer-group"></i>
        Cards
    </button>
    <button onclick="richInsertNoteLink()">
        <i class="fa-solid fa-note-sticky"></i>
        Link
    </button>
</div>
```

- [ ] **Step 2: Add Jarvis action functions**

Add near the existing Jarvis panel functions:

```javascript
function getCurrentEditorPlainText() {
    const editor = document.getElementById('note-content-rich');
    return editor ? (editor.innerText || '').trim() : '';
}

window.openStudyJarvis = function() {
    openJarvisPanel('deep_search');
    const prompt = document.getElementById('jarvis-prompt');
    if (prompt) prompt.value = 'Monte meu proximo passo de estudo com base nas minhas notas, materias e flashcards pendentes.';
};

window.openSubjectJarvis = function() {
    const { notebooks } = getStudyCollections();
    const nb = notebooks.find(n => String(n.id) === String(currentNotebookId));
    openJarvisPanel('deep_search');
    const prompt = document.getElementById('jarvis-prompt');
    if (prompt) prompt.value = `Me ajude a estudar ${nb ? nb.name : 'esta materia'}: explique os pontos principais e sugira revisao.`;
};

window.openNoteJarvisAction = function(mode) {
    openJarvisPanel(mode || 'summarize_text');
    const text = getCurrentEditorPlainText();
    const prompt = document.getElementById('jarvis-prompt');
    if (prompt && text) prompt.value = text.slice(0, 6000);
};
```

- [ ] **Step 3: Add local flashcard generation helpers**

Add near `createFlashcard()` or the Jarvis action functions:

```javascript
function createBasicFlashcardsFromText(text, noteId, notebookId) {
    const clean = (text || '').replace(/\s+/g, ' ').trim();
    if (!clean) return [];
    const sentences = clean.split(/(?<=[.!?])\s+/).filter(s => s.length > 24).slice(0, 5);
    const cards = sentences.map((sentence, index) => ({
        front: `Explique: ${sentence.slice(0, 90)}${sentence.length > 90 ? '...' : ''}`,
        back: sentence,
        noteId,
        notebookId,
        index
    }));
    cards.forEach(card => {
        createFlashcard(card.front, card.back, noteId || null);
        const allCards = LocalDB.getAll ? LocalDB.getAll('flashcards') : LocalDB.get('flashcards') || [];
        const saved = allCards[allCards.length - 1];
        if (saved && notebookId) {
            saved.notebook_id = notebookId;
            LocalDB.upsert('flashcards', saved);
        }
    });
    return cards;
}

window.generateFlashcardsFromCurrentNote = async function() {
    const text = getCurrentEditorPlainText();
    if (!text) {
        showInAppNotification('Escreva a nota antes de gerar cards.', 'warn');
        return;
    }
    const ok = window.showConfirm ? await window.showConfirm('Gerar flashcards locais a partir desta nota?') : confirm('Gerar flashcards locais a partir desta nota?');
    if (!ok) return;
    const notebookId = document.getElementById('note-notebook')?.value || currentNotebookId || '';
    const cards = createBasicFlashcardsFromText(text, editingNoteId || null, notebookId);
    if (!cards.length) {
        showInAppNotification('Texto curto demais para gerar cards.', 'warn');
        return;
    }
    showInAppNotification(`${cards.length} cards criados para revisao.`, 'success');
    loadStudies();
};

window.generateFlashcardsFromSubject = async function() {
    if (!currentNotebookId) return;
    const notes = (LocalDB.get('study_notes') || []).filter(n => !n.is_deleted && String(n.notebook_id) === String(currentNotebookId));
    const text = notes.map(n => `${n.title || ''}. ${(n.content || '').replace(/<[^>]+>/g, ' ')}`).join(' ');
    if (!text.trim()) {
        showInAppNotification('Esta materia ainda nao tem conteudo para gerar cards.', 'warn');
        return;
    }
    const ok = window.showConfirm ? await window.showConfirm('Gerar flashcards locais desta materia?') : confirm('Gerar flashcards locais desta materia?');
    if (!ok) return;
    const cards = createBasicFlashcardsFromText(text, null, currentNotebookId);
    showInAppNotification(`${cards.length} cards criados para a materia.`, 'success');
    renderSubjectStudySummary(currentNotebookId);
    loadStudies();
};
```

- [ ] **Step 4: Add subject action hook for card generation**

In `mobile/index.html`, add one more subject action button if space remains acceptable:

```html
<button onclick="generateFlashcardsFromSubject()">
    <i class="fa-solid fa-plus"></i>
    Gerar cards
</button>
```

If four buttons feel cramped, keep three columns but let the fourth wrap to a second row; the CSS grid will handle it.

- [ ] **Step 5: Add editor action styles**

Append to `mobile/style.css`:

```css
.editor-study-actions {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
    padding: 8px 16px 12px;
    border-top: 1px solid rgba(255,255,255,0.06);
    background: rgba(0,0,0,0.18);
}

.editor-study-actions button {
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.055);
    color: var(--text-secondary);
    border-radius: 12px;
    min-height: 54px;
    font: inherit;
    font-size: 0.72rem;
    font-weight: 800;
    cursor: pointer;
}

.editor-study-actions i {
    display: block;
    color: var(--accent-purple);
    font-size: 1rem;
    margin-bottom: 5px;
}
```

- [ ] **Step 6: Run parser check**

Run:

```powershell
node --check mobile/app.js
```

Expected: exit code `0`.

---

### Task 8: Improve Flashcard Review Entry Points

**Files:**
- Modify: `mobile/app.js`
- Test: `node --check mobile/app.js`

- [ ] **Step 1: Allow subject-specific review queue**

Change the start of `window.showFlashcards` from:

```javascript
window.showFlashcards = function() {
    initFlashcardsDB();
    _flashcardQueue = getDueFlashcards();
```

to:

```javascript
window.showFlashcards = function(cardsOverride) {
    initFlashcardsDB();
    _flashcardQueue = Array.isArray(cardsOverride) ? cardsOverride : getDueFlashcards();
```

- [ ] **Step 2: Add subject review function**

Add near the flashcard functions:

```javascript
window.reviewSubjectFlashcards = function() {
    if (!currentNotebookId) return;
    const due = getDueFlashcardsForNotebook(currentNotebookId);
    if (!due.length) {
        showInAppNotification('Nenhum card pendente nesta materia hoje.', 'info');
        return;
    }
    showFlashcards(due);
};
```

- [ ] **Step 3: Keep empty-state behavior**

In `showFlashcards(cardsOverride)`, confirm the existing empty-deck checks still work for global review. For subject review, the `reviewSubjectFlashcards()` function handles empty state before calling `showFlashcards(due)`, so no additional branch is required.

- [ ] **Step 4: Run parser check**

Run:

```powershell
node --check mobile/app.js
```

Expected: exit code `0`.

---

### Task 9: Replace New Blocking Dialogs And Avoid Desktop Dependency

**Files:**
- Modify: `mobile/app.js`
- Test: `node --check mobile/app.js`

- [ ] **Step 1: Do not add any desktop-required guard**

Search newly added code for desktop or PC gating:

```powershell
rg -n "desktop|pc aberto|requireDesktop|localhost|127\\.0\\.0\\.1" mobile/app.js
```

Expected: no newly added code requires the desktop before local study actions run.

- [ ] **Step 2: Replace new `confirm()` fallbacks if project has `window.showConfirm()`**

For the two new generator functions, prefer:

```javascript
const ok = window.showConfirm ? await window.showConfirm('Gerar flashcards locais a partir desta nota?') : confirm('Gerar flashcards locais a partir desta nota?');
```

Do not introduce plain `window.confirm()` calls without the `showConfirm()` preference.

- [ ] **Step 3: Run parser check**

Run:

```powershell
node --check mobile/app.js
```

Expected: exit code `0`.

---

### Task 10: Deploy To Phone And Validate Main Flow

**Files:**
- Use: `scripts/push_mobile_bundle_adb.py`
- Verify: Android device running `com.nexus.mobile`

- [ ] **Step 1: Push the mobile bundle**

Run:

```powershell
python scripts/push_mobile_bundle_adb.py
```

Expected: script pushes `mobile/` into the app's `files/mobile_bundle/` directory and restarts `com.nexus.mobile`.

- [ ] **Step 2: Launch the app if the script did not leave it open**

Run:

```powershell
$serial = (adb devices | Select-String -Pattern '^\S+\s+device$' | Select-Object -First 1).ToString().Split()[0]
adb -s $serial shell am start -n com.nexus.mobile/.MainActivity
```

Expected: app opens on device.

- [ ] **Step 3: Capture the new Studies screen**

Run:

```powershell
$serial = (adb devices | Select-String -Pattern '^\S+\s+device$' | Select-Object -First 1).ToString().Split()[0]
adb -s $serial shell screencap /sdcard/nexus_after_studies.raw
adb -s $serial pull /sdcard/nexus_after_studies.raw .superpowers\nexus_after_studies.raw
@'
from pathlib import Path
import struct
from PIL import Image
raw = Path('.superpowers/nexus_after_studies.raw').read_bytes()
w,h,fmt = struct.unpack_from('<III', raw, 0)
Image.frombytes('RGBA', (w,h), raw[16:16+w*h*4]).save('.superpowers/nexus_after_studies.png')
print(f'{w}x{h} fmt={fmt}')
'@ | python -
```

Expected output:

```text
720x1600 fmt=1
```

- [ ] **Step 4: Manual flow checks on device**

Use taps/swipes on the device or ADB input. Confirm:

```text
Inicio still opens.
Estudos first fold shows the new study cockpit before the analytics chart.
Revisar agora opens flashcards when due cards exist or shows a clear no-cards message.
Nova nota opens the editor.
Capturar invokes the existing camera/OCR bridge path.
Jarvis opens the Jarvis panel without requiring the desktop app to be open.
Materia opens subject detail with note/card summary and actions.
Editor shows Capturar, Resumir, Cards, Link actions.
```

- [ ] **Step 5: Capture editor and subject detail screenshots**

Run captures after manually navigating to each screen:

```powershell
$serial = (adb devices | Select-String -Pattern '^\S+\s+device$' | Select-Object -First 1).ToString().Split()[0]
adb -s $serial shell screencap /sdcard/nexus_after_editor.raw
adb -s $serial pull /sdcard/nexus_after_editor.raw .superpowers\nexus_after_editor.raw
adb -s $serial shell screencap /sdcard/nexus_after_subject.raw
adb -s $serial pull /sdcard/nexus_after_subject.raw .superpowers\nexus_after_subject.raw
```

Expected: both raw files are pulled successfully for visual review.

---

### Task 11: Final Verification

**Files:**
- Verify: `mobile/app.js`
- Verify: deployed Android app

- [ ] **Step 1: Run final parser check**

Run:

```powershell
node --check mobile/app.js
```

Expected: exit code `0`.

- [ ] **Step 2: Search for accidental placeholders**

Run:

```powershell
rg -n "TODO|TBD|placeholder|implement later|desktop obrigatorio|PC aberto" mobile/index.html mobile/app.js mobile/style.css
```

Expected: no new placeholders or desktop-required wording from this implementation.

- [ ] **Step 3: Verify no broken function references were introduced**

Run:

```powershell
rg -n "openStudyJarvis|openSubjectJarvis|openNoteJarvisAction|reviewSubjectFlashcards|generateFlashcardsFromCurrentNote|generateFlashcardsFromSubject|renderStudyCockpit|renderStudyRecentNotes|renderSubjectStudySummary" mobile/index.html mobile/app.js
```

Expected: every referenced function appears in `mobile/app.js` and every handler referenced by markup is defined.

- [ ] **Step 4: Final device state**

Confirm the final app is installed on the connected phone through:

```powershell
adb devices
adb shell pidof com.nexus.mobile
```

Expected: connected device is listed, and `pidof` returns a process id after launching the app.

---

## Self-Review

- Spec coverage: The plan covers mobile-local Studies, visible SRS, subject workflows, editor actions, contextual Jarvis, optional desktop behavior, ADB validation, and final bundle deploy.
- Scope control: The plan does not rewrite the whole app, does not build native voice/camera, and does not migrate `mobile/app.js` to modules.
- Risk: `mobile/app.js` has multiple historical overrides of `loadStudies()` and `saveNote()`. The plan intentionally hooks into the final active `window.loadStudies` wrapper and avoids replacing core editor persistence.
- Git: This environment did not have `git` available in PATH during planning. Use commits only if a working Git executable is available in the implementation environment.
