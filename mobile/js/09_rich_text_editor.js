// RICH TEXT EDITOR — Notion-Style v2
// ================================================================

let _jarvisMode = 'summarize_text';
let _jarvisLastResult = '';
let _savedSelectionRange = null;

// ─── Core Rich Commands ──────────────────────────────────────────

function richCmd(cmd, value) {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    document.execCommand(cmd, false, value || null);
    updateToolbarState();
}

function richHeading(level) {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    if (level === 0) {
        document.execCommand('formatBlock', false, 'p');
    } else {
        document.execCommand('formatBlock', false, `h${level}`);
    }
}

function richInsertChecklist() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    const item = document.createElement('div');
    item.className = 'rich-check-item';
    item.contentEditable = 'false';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.onchange = function() {
        span.style.textDecoration = cb.checked ? 'line-through' : 'none';
        span.style.opacity = cb.checked ? '0.5' : '1';
        saveNoteDebounced();
    };
    const span = document.createElement('span');
    span.contentEditable = 'true';
    span.textContent = '';
    span.style.flex = '1';
    span.style.outline = 'none';
    item.appendChild(cb);
    item.appendChild(span);
    insertNodeAtCursor(item);
    // Add a blank line after
    const br = document.createElement('p');
    br.innerHTML = '<br>';
    item.after(br);
    // Focus the span
    const sel = window.getSelection();
    const range = document.createRange();
    range.setStart(span, 0);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
}

function richInsertDivider() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    document.execCommand('insertHTML', false, '<hr><p><br></p>');
}

function richInsertCode() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    document.execCommand('insertHTML', false, '<pre><code>// código aqui</code></pre><p><br></p>');
}

function richInsertQuote() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    document.execCommand('formatBlock', false, 'blockquote');
}

function richInsertLink() {
    const url = prompt('URL do link:');
    if (!url) return;
    const text = prompt('Texto do link:', url);
    if (text === null) return;
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    document.execCommand('insertHTML', false, `<a href="${url}" target="_blank" rel="noopener">${text || url}</a>&nbsp;`);
}

function insertNodeAtCursor(node) {
    const sel = window.getSelection();
    if (!sel.rangeCount) return;
    const range = sel.getRangeAt(0);
    range.deleteContents();
    range.insertNode(node);
    range.setStartAfter(node);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
}

// ─── Color Picker ────────────────────────────────────────────────

function toggleColorPicker(e) {
    e.stopPropagation();
    const popup = document.getElementById('color-picker-popup');
    if (!popup) return;
    if (popup.style.display === 'none' || !popup.style.display) {
        const rect = e.currentTarget.getBoundingClientRect();
        popup.style.display = 'block';
        popup.style.left = Math.min(rect.left, window.innerWidth - 180) + 'px';
        popup.style.top = (rect.bottom + 6) + 'px';
        // Save selection before click hides it
        const sel = window.getSelection();
        if (sel && sel.rangeCount) _savedSelectionRange = sel.getRangeAt(0).cloneRange();
    } else {
        popup.style.display = 'none';
    }
}

function applyTextColor(color) {
    const popup = document.getElementById('color-picker-popup');
    if (popup) popup.style.display = 'none';
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    // Restore saved selection
    if (_savedSelectionRange) {
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(_savedSelectionRange);
        _savedSelectionRange = null;
    }
    if (!color) {
        document.execCommand('removeFormat', false, null);
    } else {
        document.execCommand('foreColor', false, color);
    }
    // Update indicator
    const ind = document.getElementById('color-indicator');
    if (ind) ind.style.background = color || '#fff';
}

document.addEventListener('click', function(e) {
    const popup = document.getElementById('color-picker-popup');
    const btn = document.getElementById('color-picker-btn');
    if (popup && btn && !btn.contains(e.target) && !popup.contains(e.target)) {
        popup.style.display = 'none';
    }
});

// ─── Slash Menu ──────────────────────────────────────────────────

let _slashRange = null;
let _slashStartOffset = 0;

function openSlashMenu() {
    const editor = document.getElementById('note-content-rich');
    const menu = document.getElementById('slash-menu');
    if (!menu || !editor) return;
    // Position at center bottom of editor
    const rect = editor.getBoundingClientRect();
    menu.style.display = 'block';
    const menuWidth = 260;
    const left = Math.min(rect.left + 16, window.innerWidth - menuWidth - 8);
    menu.style.left = left + 'px';
    menu.style.top = (rect.top + 80) + 'px';
    // Trap outside clicks
    setTimeout(() => {
        document.addEventListener('click', closeSlashMenuOnClickOutside, { once: true });
    }, 50);
}

function closeSlashMenuOnClickOutside(e) {
    const menu = document.getElementById('slash-menu');
    if (menu && !menu.contains(e.target)) closeSlashMenu();
}

function closeSlashMenu() {
    const menu = document.getElementById('slash-menu');
    if (menu) menu.style.display = 'none';
    // Remove leftover '/' trigger character if present
    if (_slashRange) {
        try {
            _slashRange.deleteContents();
        } catch(e) {}
        _slashRange = null;
    }
}

// Keyboard listener on the rich editor for '/' trigger
function initRichEditorKeyListeners() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;

    editor.addEventListener('keyup', function(e) {
        if (e.key === '/') {
            const sel = window.getSelection();
            if (!sel.rangeCount) return;
            const range = sel.getRangeAt(0).cloneRange();
            // Walk back 1 char to select the '/'
            range.setStart(range.endContainer, Math.max(0, range.endOffset - 1));
            _slashRange = range;
            openSlashMenu();
        }
        if (e.key === 'Escape') closeSlashMenu();
        updateToolbarState();
    });

    editor.addEventListener('input', function() {
        saveNoteDebounced();
        updateToolbarState();
    });

    // Prevent default tab behaviour
    editor.addEventListener('keydown', function(e) {
        if (e.key === 'Tab') {
            e.preventDefault();
            document.execCommand('insertHTML', false, '&nbsp;&nbsp;&nbsp;&nbsp;');
        }
    });
}

// ─── YouTube Embed ───────────────────────────────────────────────

function openYouTubeModal() {
    const modal = document.getElementById('yt-modal');
    if (modal) {
        modal.style.display = 'flex';
        const inp = document.getElementById('yt-url-input');
        if (inp) { inp.value = ''; setTimeout(() => inp.focus(), 100); }
    }
}

function closeYouTubeModal() {
    const modal = document.getElementById('yt-modal');
    if (modal) modal.style.display = 'none';
}

function getYouTubeEmbedOrigin() {
    const origin = window.location.origin;
    if (origin && origin !== 'null' && origin.startsWith('https://')) {
        return origin;
    }
    return null;
}

function getYouTubeEmbedSrc(videoId) {
    const origin = getYouTubeEmbedOrigin();
    if (origin) {
        const params = new URLSearchParams({
            rel: '0',
            playsinline: '1',
            origin: origin,
        });
        return `https://www.youtube-nocookie.com/embed/${videoId}?${params.toString()}`;
    }
    const remotePlayerUrl = 'https://mariagilda402-rgb.github.io/Project-AI/mobile/youtube-player.html';
    const configuredPlayerUrl = window.NEXUS_YOUTUBE_PLAYER_BASE;
    const playerBaseUrl = configuredPlayerUrl || remotePlayerUrl;
    return `${playerBaseUrl}?video=${encodeURIComponent(videoId)}`;
}

function insertYouTubeEmbed() {
    const url = document.getElementById('yt-url-input')?.value?.trim();
    if (!url) return;
    const videoId = extractYouTubeId(url);
    if (!videoId) {
        alert('URL do YouTube inválida!');
        return;
    }
    closeYouTubeModal();
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();
    const embedSrc = getYouTubeEmbedSrc(videoId);
    const embedHTML = `<div class="yt-embed-block" contenteditable="false">
        <iframe
            src="${embedSrc}"
            title="YouTube video player"
            loading="lazy"
            referrerpolicy="strict-origin-when-cross-origin"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen></iframe>
    </div><p><br></p>`;
    document.execCommand('insertHTML', false, embedHTML);
}

function extractYouTubeId(url) {
    const patterns = [
        /(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})/,
        /(?:youtu\.be\/)([a-zA-Z0-9_-]{11})/,
        /(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})/,
        /(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})/,
    ];
    for (const p of patterns) {
        const m = url.match(p);
        if (m) return m[1];
    }
    return null;
}

// ─── Image Picker ────────────────────────────────────────────────

function openImagePicker() {
    const inp = document.getElementById('note-image-input');
    if (inp) inp.click();
}

function handleImageFile(event) {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
        alert('Imagem muito grande (máx 2MB). Redimensione antes de inserir.');
        return;
    }
    const reader = new FileReader();
    reader.onload = function(e) {
        const editor = document.getElementById('note-content-rich');
        if (!editor) return;
        editor.focus();
        document.execCommand('insertHTML', false,
            `<img src="${e.target.result}" class="rich-image-block" alt="imagem"><p><br></p>`);
        saveNoteDebounced();
    };
    reader.readAsDataURL(file);
    // Reset input so same file can be picked again
    event.target.value = '';
}

// ─── Note Link Picker ────────────────────────────────────────────

function richInsertNoteLink() {
    const modal = document.getElementById('note-link-modal');
    if (!modal) return;
    modal.style.display = 'flex';
    // Populate list
    const search = document.getElementById('note-link-search');
    if (search) { search.value = ''; }
    filterNoteLinkList('');
}

function closeNoteLinkModal() {
    const modal = document.getElementById('note-link-modal');
    if (modal) modal.style.display = 'none';
}

function filterNoteLinkList(query) {
    const container = document.getElementById('note-link-list');
    if (!container) return;
    const notes = LocalDB.getAll('notes') || [];
    const filtered = query
        ? notes.filter(n => (n.title || '').toLowerCase().includes(query.toLowerCase()))
        : notes;
    container.innerHTML = '';
    if (!filtered.length) {
        container.innerHTML = '<div style="text-align:center;color:var(--text-secondary);padding:20px;font-size:0.9rem">Nenhuma nota encontrada</div>';
        return;
    }
    filtered.forEach(note => {
        const el = document.createElement('div');
        el.className = 'slash-item';
        el.innerHTML = `<span class="slash-icon">📎</span><div><b>${note.title || 'Sem título'}</b><div style="font-size:0.75rem;color:var(--text-secondary)">${note.subject || note.tags || ''}</div></div>`;
        el.onclick = () => {
            const editor = document.getElementById('note-content-rich');
            if (editor) {
                editor.focus();
                document.execCommand('insertHTML', false,
                    `<a class="note-link-block" onclick="openNoteById('${note.id}')" href="#" data-note-id="${note.id}">📎 ${note.title || 'Nota'}</a>&nbsp;`);
            }
            closeNoteLinkModal();
        };
        container.appendChild(el);
    });
}

function openNoteById(id) {
    const notes = LocalDB.getAll('notes') || [];
    const note = notes.find(n => n.id === id);
    if (note) openNoteEditor(note, note.notebookId || null);
}

// ─── Toolbar State ───────────────────────────────────────────────

function updateToolbarState() {
    const btns = document.querySelectorAll('.rt-btn');
    btns.forEach(btn => btn.classList.remove('active'));
}

// ─── Jarvis AI Panel ─────────────────────────────────────────────

function openJarvisPanel(mode) {
    if (!requireWifiForJarvis('IA nas notas')) return;
    const panel = document.getElementById('jarvis-panel');
    if (!panel) return;
    panel.style.display = 'flex';
    if (mode) setJarvisMode(mode, null);
    // Pre-fill with selected text if summarizing
    if (_jarvisMode === 'summarize_text') {
        const editor = document.getElementById('note-content-rich');
        const sel = window.getSelection();
        if (sel && sel.toString().trim()) {
            const prompt = document.getElementById('jarvis-prompt');
            if (prompt) prompt.value = sel.toString().trim();
        }
    }
    // Reset result
    document.getElementById('jarvis-result').style.display = 'none';
    document.getElementById('jarvis-loading').style.display = 'none';
    document.getElementById('jarvis-input-area').style.display = 'block';
}

function closeJarvisPanel() {
    const panel = document.getElementById('jarvis-panel');
    if (panel) panel.style.display = 'none';
}

function setJarvisMode(mode, btn) {
    _jarvisMode = mode;
    document.querySelectorAll('.jarvis-tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    // Update placeholder
    const prompt = document.getElementById('jarvis-prompt');
    if (!prompt) return;
    const placeholders = {
        summarize_text: 'Cole ou escreva o texto para resumir...',
        summarize_video: 'Cole a URL do vídeo do YouTube aqui...',
        deep_search: 'Qual assunto você quer pesquisar na web?',
        generate_image: 'Descreva a imagem que quer gerar...',
        expand_text: 'Cole o texto para expandir/detalhar...',
        translate: 'Cole o texto para traduzir para Português...',
    };
    prompt.placeholder = placeholders[mode] || 'Digite o prompt...';
    prompt.value = '';
    document.getElementById('jarvis-result').style.display = 'none';
}

async function runJarvisAction() {
    const prompt = document.getElementById('jarvis-prompt')?.value?.trim();
    if (!prompt) {
        alert('Por favor, insira um texto ou URL.');
        return;
    }
    if (!requireWifiForJarvis('IA nas notas')) {
        return;
    }
    document.getElementById('jarvis-input-area').style.display = 'none';
    document.getElementById('jarvis-loading').style.display = 'block';
    document.getElementById('jarvis-result').style.display = 'none';

    try {
        let result = '';
        // Try calling backend Jarvis API
        const payload = { action: _jarvisMode, content: prompt };

        if (_jarvisMode === 'summarize_video') {
            payload.youtube_url = prompt;
        }

        let apiResponse = null;
        try {
            const res = await fetch('/api/nexus/jarvis/note-action', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
                signal: AbortSignal.timeout(30000)
            });
            if (res.ok) {
                const data = await res.json();
                result = data.result || data.text || JSON.stringify(data);
                apiResponse = data;
            }
        } catch(fetchErr) {
            result = 'Jarvis indisponível. Verifique Wi-Fi e se o Nexus desktop está ligado.';
        }

        _jarvisLastResult = result;
        _jarvisLastApiResponse = apiResponse;

        document.getElementById('jarvis-loading').style.display = 'none';
        document.getElementById('jarvis-result').style.display = 'block';
        document.getElementById('jarvis-result-text').innerHTML =
            _jarvisMode === 'generate_image' && apiResponse?.image_url
                ? `<img src="${apiResponse.image_url}" style="max-width:100%;border-radius:10px">`
                : escapeHtmlLight(result).replace(/\n/g, '<br>');
        document.getElementById('jarvis-input-area').style.display = 'block';

    } catch(e) {
        document.getElementById('jarvis-loading').style.display = 'none';
        document.getElementById('jarvis-input-area').style.display = 'block';
        alert('Erro ao processar com Jarvis: ' + e.message);
    }
}

function jarvisSimulate(mode, content) {
    const simulations = {
        summarize_text: `📋 **Resumo do Texto:**\n\n${content.slice(0, 200)}...\n\n**Pontos principais:**\n• Conteúdo relevante identificado\n• Informações estruturadas\n• Pronto para revisão\n\n_[Conecte o backend Jarvis para resumos reais]_`,
        summarize_video: `🎬 **Resumo do Vídeo YouTube:**\n\nURL: ${content}\n\n**Tópicos do vídeo:**\n1. Introdução ao assunto\n2. Desenvolvimento dos conceitos\n3. Conclusões e insights\n\n_[Conecte o backend para transcrições reais]_`,
        deep_search: `🔍 **Pesquisa Web: "${content}"**\n\n**Fontes consultadas:**\n• Wikipedia, artigos acadêmicos e blogs especializados\n\n**Resumo:**\n${content} é um tema que abrange diversas perspectivas. Conecte o Jarvis ao backend para resultados reais da web.\n\n_[Backend necessário para pesquisa real]_`,
        generate_image: `✨ Imagem gerada para: "${content}"\n\n_[Conecte o backend Gemini para gerar imagens reais]_`,
        expand_text: `📝 **Texto Expandido:**\n\n${content}\n\nPara elaborar ainda mais este conteúdo, considere aprofundar cada ponto com exemplos práticos, dados e referências relevantes ao contexto estudado.\n\n_[Backend necessário para expansão avançada]_`,
        translate: `🌐 **Tradução para Português:**\n\n${content}\n\n_[Backend necessário para tradução real]_`,
    };
    return simulations[mode] || 'Resultado simulado. Conecte o backend Jarvis.';
}

function escapeHtmlLight(text) {
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function insertJarvisResult() {
    const editor = document.getElementById('note-content-rich');
    if (!editor) return;
    editor.focus();

    // Check if it's an image response
    if (_jarvisLastApiResponse?.image_url) {
        document.execCommand('insertHTML', false,
            `<img src="${_jarvisLastApiResponse.image_url}" class="rich-image-block ai-image-block" alt="Imagem gerada por IA">
            <p class="ai-image-label">✨ Gerado pelo Gemini</p><p><br></p>`);
    } else {
        // Insert as formatted quote block
        const formatted = `<blockquote><strong>🤖 Jarvis:</strong><br>${escapeHtmlLight(_jarvisLastResult).replace(/\n/g, '<br>')}</blockquote><p><br></p>`;
        document.execCommand('insertHTML', false, formatted);
    }
    closeJarvisPanel();
    saveNoteDebounced();
}

function copyJarvisResult() {
    if (!_jarvisLastResult) return;
    navigator.clipboard.writeText(_jarvisLastResult).then(() => {
        showToast('Copiado para a área de transferência!');
    });
}

let _jarvisLastApiResponse = null;

// ─── Save & Load (Rich Editor) ───────────────────────────────────

let _saveNoteTimeout = null;
function saveNoteDebounced() {
    clearTimeout(_saveNoteTimeout);
    _saveNoteTimeout = setTimeout(() => {
        const editor = document.getElementById('note-content-rich');
        const hidden = document.getElementById('note-content');
        if (editor && hidden) {
            hidden.value = editor.innerHTML;
        }
    }, 1000);
}

// Override saveNote to grab from rich editor
const _origSaveNote = window.saveNote;
window.saveNote = function() {
    const editor = document.getElementById('note-content-rich');
    const hidden = document.getElementById('note-content');
    if (editor && hidden) {
        hidden.value = editor.innerHTML;
    }
    if (typeof _origSaveNote === 'function') _origSaveNote();
};

// ─── openNoteEditor override — populate rich editor ──────────────

const _origOpenNoteEditor = window.openNoteEditor;
window.openNoteEditor = function(note, notebookId) {
    // Call original
    if (typeof _origOpenNoteEditor === 'function') _origOpenNoteEditor(note, notebookId);

    // Now populate rich editor
    setTimeout(() => {
        const editor = document.getElementById('note-content-rich');
        const hidden = document.getElementById('note-content');
        if (!editor) return;

        let content = '';
        if (hidden) content = hidden.value || '';

        // If content looks like plain markdown (no HTML tags), convert it
        if (content && !content.includes('<') && content.includes('\n')) {
            content = markdownToHtml(content);
        }

        editor.innerHTML = content || '';
        initRichEditorKeyListeners();
    }, 80);
};

// ─── Basic Markdown → HTML converter (for legacy notes) ─────────

function markdownToHtml(md) {
    if (!md) return '';
    let html = md
        // Headings
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        // Bold / italic
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Code
        .replace(/`(.+?)`/g, '<code>$1</code>')
        // Blockquote
        .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
        // HR
        .replace(/^---$/gm, '<hr>')
        // Checklist
        .replace(/^- \[x\] (.+)$/gm, '<div class="rich-check-item"><input type="checkbox" checked onchange="this.nextSibling.style.textDecoration=this.checked?\'line-through\':\'none\'"><span style="flex:1;text-decoration:line-through;opacity:0.5">$1</span></div>')
        .replace(/^- \[ \] (.+)$/gm, '<div class="rich-check-item"><input type="checkbox" onchange="this.nextSibling.style.textDecoration=this.checked?\'line-through\':\'none\'"><span style="flex:1">$1</span></div>')
        // Unordered list
        .replace(/^[-*] (.+)$/gm, '<li>$1</li>')
        // Numbered list
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
        // Paragraphs
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>');

    // Wrap loose <li> in <ul>
    html = html.replace(/(<li>.*?<\/li>)+/gs, '<ul>$&</ul>');
    return `<p>${html}</p>`;
}

// ─── Init on DOMContentLoaded ────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Close modals on backdrop click
    const ytModal = document.getElementById('yt-modal');
    if (ytModal) ytModal.addEventListener('click', function(e) {
        if (e.target === ytModal) closeYouTubeModal();
    });

    const jarvisPanel = document.getElementById('jarvis-panel');
    if (jarvisPanel) jarvisPanel.addEventListener('click', function(e) {
        if (e.target === jarvisPanel) closeJarvisPanel();
    });

    const noteLinkModal = document.getElementById('note-link-modal');
    if (noteLinkModal) noteLinkModal.addEventListener('click', function(e) {
        if (e.target === noteLinkModal) closeNoteLinkModal();
    });

    // Init if editor view is open
    const editorView = document.getElementById('note-editor-view');
    if (editorView && editorView.style.display !== 'none') {
        initRichEditorKeyListeners();
    }
});


document.addEventListener('DOMContentLoaded', () => {
    applyUiPrefs();
});

// ----------------------------------------------------
