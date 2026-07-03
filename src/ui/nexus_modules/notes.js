const boot = readBoot();
    if (boot.toast) showToastBanner(boot.toast);

    let activeId = null;
    let currentMedia = [];
    let activeSubject = '';
    let activeTag = '';
    let allNotes = [];
    let openNoteTabs = [];
    let currentView = 'editor';
    let currentColor = null;
    let searchQuery = '';

    const NOTE_COLORS = [
      { name: 'none', css: 'transparent' },
      { name: 'purple', css: '#8b5cf6' },
      { name: 'blue', css: '#3b82f6' },
      { name: 'cyan', css: '#06b6d4' },
      { name: 'green', css: '#10b981' },
      { name: 'yellow', css: '#eab308' },
      { name: 'orange', css: '#f97316' },
      { name: 'red', css: '#ef4444' },
      { name: 'pink', css: '#ec4899' },
    ];

    function getColorCSS(name) { return (NOTE_COLORS.find(c => c.name === name) || NOTE_COLORS[0]).css; }

    // Render Color Picker
    function renderColorPicker() {
      const picker = document.getElementById('colorPicker');
      picker.innerHTML = NOTE_COLORS.map(c =>
        '<button class="color-dot' + (currentColor === c.name ? ' active' : '') + '" style="background:' + c.css + (c.name === 'none' ? '; border: 1px dashed rgba(255,255,255,0.2)' : '') + ';" onclick="setNoteColor(\'' + c.name + '\')" title="' + c.name + '"></button>'
      ).join('');
    }

    async function setNoteColor(name) {
      currentColor = name === 'none' ? null : name;
      renderColorPicker();
      if (activeId) {
        await nxBridge('note_patch', { note_id: activeId, color: name === 'none' ? '' : name });
      }
    }

    // Favorites
    let favNotesIds = JSON.parse(localStorage.getItem('nexus_notes_fav') || '[]');

    document.getElementById('btnFav').onclick = () => {
      if(!activeId) return;
      const idx = favNotesIds.indexOf(activeId);
      if(idx > -1) { favNotesIds.splice(idx, 1); document.getElementById('btnFav').classList.remove('is-fav'); }
      else { favNotesIds.push(activeId); document.getElementById('btnFav').classList.add('is-fav'); }
      localStorage.setItem('nexus_notes_fav', JSON.stringify(favNotesIds));
      renderNav();
    };

    // Search
    document.getElementById('sidebarSearch').addEventListener('input', (e) => {
      searchQuery = e.target.value.trim().toLowerCase();
      renderNav();
      if (currentView === 'cards') renderCards();
    });

    // View Toggle
    function setView(v) {
      currentView = v;
      document.querySelectorAll('.view-toggle-btn').forEach(b => b.classList.toggle('active', b.dataset.view === v));
      document.getElementById('editorView').style.display = v === 'editor' ? 'flex' : 'none';
      document.getElementById('cardsView').classList.toggle('active', v === 'cards');
      if (v === 'cards') renderCards();
    }

    // Cards View
    function renderCards() {
      const grid = document.getElementById('cardsGrid');
      let notes = allNotes;
      if (activeSubject) notes = notes.filter(n => (n.subject || 'Geral').trim() === activeSubject);
      if (activeTag) notes = notes.filter(n => (n.content || '').includes(activeTag));
      if (searchQuery) notes = notes.filter(n => (n.title || '').toLowerCase().includes(searchQuery) || (n.content || '').toLowerCase().includes(searchQuery));

      if (!notes.length) {
        grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text-dim);font-size:13px;">Sem notas.</div>';
        return;
      }
      grid.innerHTML = notes.map(n => {
        const color = getColorCSS(n.color || 'none');
        const isFav = favNotesIds.includes(n.id);
        const preview = (n.content || '').replace(/^---[\s\S]*?---\n?/, '').replace(/[#*>\-\[\]`~=]/g, '').substring(0, 140);
        const date = (n.updated_at || '').substring(0, 10);
        return '<div class="note-card" onclick="setView(\'editor\'); openNote(' + n.id + ')" style="border-top-color:' + color + ';">' +
          '<div style="position:absolute;top:0;left:0;right:0;height:3px;background:' + color + ';border-radius:12px 12px 0 0;"></div>' +
          (isFav ? '<div class="note-card-fav">★</div>' : '') +
          '<div class="note-card-title">' + esc(n.title || 'Sem título') + '</div>' +
          '<div class="note-card-preview">' + esc(preview) + '</div>' +
          '<div class="note-card-footer">' +
            '<span class="note-card-subject">' + esc(n.subject || 'Geral') + '</span>' +
            '<span>' + date + '</span>' +
          '</div>' +
        '</div>';
      }).join('');
    }

    const nc = document.getElementById('nc');
    const ncRich = document.getElementById('ncRich');
    let currentFrontmatterBlock = '';
    let syncingRichEditor = false;
    let previewTimer = null;

    const BLOCK_LABELS = {
      h1: 'H1',
      h2: 'H2',
      h3: 'H3',
      h4: 'H4',
      p: '',
      blockquote: 'Quote',
      div: '',
      pre: 'Code',
      table: 'Table',
    };

    function splitFrontmatterBlock(text) {
      const match = String(text || '').match(/^(---\n[\s\S]*?\n---\n?)([\s\S]*)$/);
      return match ? { frontmatter: match[1], body: match[2] || '' } : { frontmatter: '', body: text || '' };
    }

    function markdownToRichHtml(markdown) {
      const lines = String(markdown || '').split(/\r?\n/);
      if (!lines.length || (lines.length === 1 && !lines[0])) return '';
      const blocks = [];
      let i = 0;

      const splitTableCells = (line) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
      const isTableSeparator = (line) => {
        const cells = splitTableCells(line);
        return cells.length > 1 && cells.every(c => /^:?-{3,}:?$/.test(c));
      };
      const renderTable = (tableLines) => {
        const rows = tableLines.filter(line => !isTableSeparator(line)).map(splitTableCells).filter(row => row.length);
        if (!rows.length) return '';
        const head = rows[0];
        const body = rows.slice(1);
        return '<table class="rich-table" data-label="Table"><thead><tr>' +
          head.map(c => '<th>' + inlineFormat(c) + '</th>').join('') +
          '</tr></thead><tbody>' +
          body.map(row => '<tr>' + row.map(c => '<td>' + inlineFormat(c) + '</td>').join('') + '</tr>').join('') +
          '</tbody></table>';
      };

      while (i < lines.length) {
        const text = lines[i].trimEnd();
        if (!text) { blocks.push('<p class="rich-empty" data-prefix="" data-label=""><br></p>'); i++; continue; }

        if (text.startsWith('```')) {
          const code = [];
          i++;
          while (i < lines.length && !lines[i].startsWith('```')) {
            code.push(lines[i]);
            i++;
          }
          if (i < lines.length) i++;
          blocks.push('<pre class="rich-code-block" data-prefix="```" data-label="Code"><code>' + esc(code.join('\n')) + '</code></pre>');
          continue;
        }

        if (text.startsWith('|') && text.includes('|')) {
          const tableLines = [];
          while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].includes('|')) {
            tableLines.push(lines[i]);
            i++;
          }
          blocks.push(renderTable(tableLines));
          continue;
        }

        const img = text.match(/^!\[(.*?)\]\((.*?)\)$/);
        const numbered = text.match(/^(\d+)\.\s+(.*)$/);
        const callout = text.match(/^>\s*\[!(\w+)\]\s*(.*)$/i);
        if (img) blocks.push('<div data-prefix="" data-label="Image"><img src="' + esc(img[2] || '') + '" alt="' + esc(img[1] || '') + '"></div>');
        else if (text === '---' || text === '***') blocks.push('<div class="rich-hr" data-prefix="---" data-label="Line"><hr></div>');
        else if (text.startsWith('#### ')) blocks.push('<h4 data-prefix="#### " data-label="H4">' + inlineFormat(text.slice(5)) + '</h4>');
        else if (text.startsWith('### ')) blocks.push('<h3 data-prefix="### " data-label="H3">' + inlineFormat(text.slice(4)) + '</h3>');
        else if (text.startsWith('## ')) blocks.push('<h2 data-prefix="## " data-label="H2">' + inlineFormat(text.slice(3)) + '</h2>');
        else if (text.startsWith('# ')) blocks.push('<h1 data-prefix="# " data-label="H1">' + inlineFormat(text.slice(2)) + '</h1>');
        else if (text.startsWith('- [x] ')) blocks.push('<div class="rich-task done" data-prefix="- [x] " data-label="Task"><input type="checkbox" class="task-toggle" checked><span class="task-text">' + inlineFormat(text.slice(6)) + '</span></div>');
        else if (text.startsWith('- [ ] ')) blocks.push('<div class="rich-task" data-prefix="- [ ] " data-label="Task"><input type="checkbox" class="task-toggle"><span class="task-text">' + inlineFormat(text.slice(6)) + '</span></div>');
        else if (numbered) blocks.push('<div class="rich-numbered" data-prefix="' + esc(numbered[1] + '. ') + '" data-number="' + esc(numbered[1]) + '" data-label="List">' + inlineFormat(numbered[2]) + '</div>');
        else if (text.startsWith('- ') || text.startsWith('* ')) blocks.push('<div class="rich-bullet" data-prefix="- " data-label="List">' + inlineFormat(text.slice(2)) + '</div>');
        else if (callout) blocks.push('<div class="rich-callout" data-prefix="> [!' + esc(callout[1].toLowerCase()) + '] " data-label="Callout">' + inlineFormat(callout[2] || '') + '</div>');
        else if (text.startsWith('> ')) blocks.push('<blockquote data-prefix="> " data-label="Quote">' + inlineFormat(text.slice(2)) + '</blockquote>');
        else blocks.push('<p data-prefix="" data-label="">' + inlineFormat(text) + '</p>');
        i++;
      }
      return blocks.join('');
    }

    function inlineMarkdownFromNode(node) {
      if (!node) return '';
      if (node.nodeType === Node.TEXT_NODE) return node.nodeValue || '';
      if (node.nodeType !== Node.ELEMENT_NODE) return '';
      const tag = node.tagName.toLowerCase();
      if (tag === 'br') return '';
      if (tag === 'img') return '![' + (node.getAttribute('alt') || 'Imagem') + '](' + (node.getAttribute('src') || '') + ')';
      const inner = Array.from(node.childNodes).map(inlineMarkdownFromNode).join('');
      if (tag === 'strong' || tag === 'b') return '**' + inner + '**';
      if (tag === 'em' || tag === 'i') return '*' + inner + '*';
      if (tag === 'code') return '`' + inner + '`';
      if (tag === 'mark') return '==' + inner + '==';
      if (tag === 'del' || tag === 's') return '~~' + inner + '~~';
      return inner;
    }

    function richBlockToMarkdown(block) {
      const tag = block.tagName ? block.tagName.toLowerCase() : '';
      let prefix = block.dataset ? (block.dataset.prefix || '') : '';
      if (prefix === '---' || tag === 'hr') return '---';
      if (tag === 'pre' || block.classList.contains('rich-code-block')) {
        return '```\n' + (block.textContent || '').replace(/\n+$/g, '') + '\n```';
      }
      if (tag === 'table' || block.classList.contains('rich-table')) {
        const rows = Array.from(block.querySelectorAll('tr')).map(row =>
          Array.from(row.children).map(cell => inlineMarkdownFromNode(cell).trim()).join(' | ')
        );
        if (!rows.length) return '';
        const cols = rows[0].split(' | ').length;
        const sep = Array.from({ length: cols }).map(() => '---').join(' | ');
        return '| ' + rows[0] + ' |\n| ' + sep + ' |\n' + rows.slice(1).map(row => '| ' + row + ' |').join('\n');
      }
      if (!prefix) {
        if (tag === 'h1') prefix = '# ';
        else if (tag === 'h2') prefix = '## ';
        else if (tag === 'h3') prefix = '### ';
        else if (tag === 'h4') prefix = '#### ';
        else if (tag === 'blockquote') prefix = '> ';
      }
      if (block.classList.contains('rich-task')) {
        const checked = block.classList.contains('done') || !!block.querySelector('.task-toggle:checked');
        prefix = checked ? '- [x] ' : '- [ ] ';
      } else if (block.classList.contains('rich-bullet')) {
        prefix = '- ';
      } else if (block.classList.contains('rich-numbered')) {
        prefix = prefix || ((block.dataset.number || '1') + '. ');
      } else if (block.classList.contains('rich-callout')) {
        prefix = prefix || '> [!note] ';
      }
      const image = block.querySelector && block.querySelector('img');
      if (image) return inlineMarkdownFromNode(image);
      const body = inlineMarkdownFromNode(block).trimEnd();
      return body ? prefix + body : '';
    }

    function decorateRichBlocks() {
      if (!ncRich) return;
      let numberedIndex = 1;
      Array.from(ncRich.children).forEach(block => {
        const tag = block.tagName ? block.tagName.toLowerCase() : '';
        if (block.classList.contains('rich-numbered')) {
          if (!block.dataset.number) block.dataset.number = String(numberedIndex);
          numberedIndex++;
        }
        if (block.classList.contains('rich-bullet')) block.dataset.label = 'List';
        else if (block.classList.contains('rich-task')) block.dataset.label = 'Task';
        else if (block.classList.contains('rich-callout')) block.dataset.label = 'Callout';
        else if (block.classList.contains('rich-code-block')) block.dataset.label = 'Code';
        else if (block.classList.contains('rich-table')) block.dataset.label = 'Table';
        else if (!block.dataset.label) block.dataset.label = BLOCK_LABELS[tag] || '';
      });
    }

    function getCurrentRichBlock() {
      const sel = window.getSelection();
      if (!sel || !sel.anchorNode || !ncRich.contains(sel.anchorNode)) return null;
      const node = sel.anchorNode.nodeType === Node.ELEMENT_NODE ? sel.anchorNode : sel.anchorNode.parentElement;
      return node ? node.closest('#ncRich > *') : null;
    }

    function updateActiveBlock() {
      const current = getCurrentRichBlock();
      Array.from(ncRich.children).forEach(block => block.classList.toggle('is-active-block', block === current));
    }

    function syncMarkdownFromRich() {
      if (syncingRichEditor || !ncRich) return;
      decorateRichBlocks();
      const blocks = Array.from(ncRich.children);
      const body = blocks.length ? blocks.map(richBlockToMarkdown).join('\n') : ncRich.textContent || '';
      nc.value = currentFrontmatterBlock + body;
    }

    function syncRichFromMarkdown() {
      if (!ncRich) return;
      syncingRichEditor = true;
      const split = splitFrontmatterBlock(nc.value || '');
      currentFrontmatterBlock = split.frontmatter;
      ncRich.innerHTML = markdownToRichHtml(split.body);
      decorateRichBlocks();
      syncingRichEditor = false;
    }

    function setEditorMarkdown(markdown) {
      nc.value = markdown || '';
      syncRichFromMarkdown();
      renderNotePreview();
    }

    function getEditorMarkdown() {
      syncMarkdownFromRich();
      return nc.value;
    }

    // Auto-save
    let saveTimer = null;
    function schedulePreviewRender(delay = 260) {
      clearTimeout(previewTimer);
      previewTimer = setTimeout(renderNotePreview, delay);
    }

    function syncCurrentNoteListMeta() {
      if (!activeId) return;
      const title = document.getElementById('nt').value.trim() || 'Sem titulo';
      const subject = document.getElementById('ns').value.trim() || 'Geral';
      const note = allNotes.find(n => Number(n.id) === Number(activeId));
      if (note) {
        note.title = title;
        note.subject = subject;
        note.content = nc.value || note.content || '';
      }
      const tab = openNoteTabs.find(t => Number(t.id) === Number(activeId));
      if (tab) tab.title = title;
      renderSubjectRail(allNotes);
      renderNav();
      if (currentView === 'cards') renderCards();
    }

    function triggerAutoSave() {
      syncMarkdownFromRich();
      clearTimeout(saveTimer);
      const ind = document.getElementById('saveIndicator');
      ind.className = 'save-indicator saving';
      ind.querySelector('.save-text').textContent = '...';
      saveTimer = setTimeout(saveNote, 900);
      schedulePreviewRender();
    }
    document.getElementById('nt').addEventListener('input', () => { syncCurrentNoteListMeta(); triggerAutoSave(); });
    document.getElementById('ns').addEventListener('input', () => { syncCurrentNoteListMeta(); triggerAutoSave(); });
    document.getElementById('nc').addEventListener('input', triggerAutoSave);
    ncRich.addEventListener('input', triggerAutoSave);
    ncRich.addEventListener('paste', (e) => {
      e.preventDefault();
      const text = (e.clipboardData || window.clipboardData).getData('text/plain');
      const trimmed = text.trim();
      if (/^https?:\/\/\S+\.(png|jpe?g|gif|webp|svg)(\?\S*)?$/i.test(trimmed)) insertImageBlock(trimmed, 'Imagem');
      else document.execCommand('insertText', false, text);
    });

    // Dropdown
    function toggleMenu(e) { e.stopPropagation(); document.getElementById('actionMenu').classList.toggle('show'); }
    document.addEventListener('click', () => { document.getElementById('actionMenu').classList.remove('show'); });

    // Sidebar Toggle
    function toggleSidebar() { document.getElementById('sidebar').classList.toggle('collapsed'); }

    // Zen Mode
    function enterZen() {
      document.getElementById('actionMenu').classList.remove('show');
      syncMarkdownFromRich();
      const zen = document.getElementById('zenOverlay');
      document.getElementById('zenTitle').value = document.getElementById('nt').value;
      document.getElementById('zenContent').value = document.getElementById('nc').value;
      zen.classList.add('active');
      document.getElementById('zenContent').focus();
    }
    function exitZen() {
      const zen = document.getElementById('zenOverlay');
      document.getElementById('nt').value = document.getElementById('zenTitle').value;
      setEditorMarkdown(document.getElementById('zenContent').value);
      zen.classList.remove('active');
      triggerAutoSave();
    }
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && document.getElementById('zenOverlay').classList.contains('active')) exitZen();
    });
    document.getElementById('zenContent').addEventListener('input', () => {
      nc.value = document.getElementById('zenContent').value;
    });
    document.getElementById('zenTitle').addEventListener('input', () => {
      document.getElementById('nt').value = document.getElementById('zenTitle').value;
    });

    // Floating Toolbar (WYSIWYG)
    const floatingToolbar = document.getElementById('floatingToolbar');

    ncRich.addEventListener('mouseup', showToolbarIfSelection);
    ncRich.addEventListener('keyup', (e) => { if (e.shiftKey) showToolbarIfSelection(); });
    document.addEventListener('mousedown', (e) => {
      if (!floatingToolbar.contains(e.target) && e.target !== ncRich) {
        floatingToolbar.classList.remove('active');
      }
    });

    function showToolbarIfSelection() {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !ncRich.contains(sel.anchorNode)) {
        floatingToolbar.classList.remove('active');
        return;
      }
      const range = sel.getRangeAt(0);
      const rect = range.getBoundingClientRect();
      const editorRect = ncRich.getBoundingClientRect();
      const top = Math.max(12, (rect.top || editorRect.top) + window.scrollY - 46);
      const left = Math.max(12, Math.min(window.innerWidth - 260, (rect.left || editorRect.left) + window.scrollX + ((rect.width || editorRect.width) / 2) - 120));
      floatingToolbar.style.top = top + 'px';
      floatingToolbar.style.left = left + 'px';
      floatingToolbar.classList.add('active');
    }

    function wrapSelection(before, after) {
      if (before === '`') {
        const sel = window.getSelection();
        if (sel && sel.rangeCount && !sel.isCollapsed) {
          const range = sel.getRangeAt(0);
          const code = document.createElement('code');
          code.textContent = sel.toString();
          range.deleteContents();
          range.insertNode(code);
        }
        ncRich.focus();
        floatingToolbar.classList.remove('active');
        triggerAutoSave();
        return;
      }
      const command = before === '**' ? 'bold' : before === '*' ? 'italic' : before === '~~' ? 'strikeThrough' : before === '`' ? 'formatBlock' : '';
      if (command) document.execCommand(command, false, null);
      else document.execCommand('insertText', false, before + (window.getSelection()?.toString() || '') + after);
      ncRich.focus();
      floatingToolbar.classList.remove('active');
      triggerAutoSave();
    }

    function prefixLine(prefix) {
      const block = prefix === '# ' ? 'h1' : prefix === '## ' ? 'h2' : prefix === '### ' ? 'h3' : prefix === '#### ' ? 'h4' : 'p';
      document.execCommand('formatBlock', false, block);
      ncRich.focus();
      floatingToolbar.classList.remove('active');
      triggerAutoSave();
    }

    // Slash Menu
    const slashMenu = document.getElementById('slashMenu');
    let slashActive = false;

    function enhanceSlashMenu() {
      const checkBtn = slashMenu.querySelector("button[onclick=\"execSlash('check')\"]");
      if (checkBtn && !slashMenu.dataset.enhanced) {
        checkBtn.insertAdjacentHTML('beforebegin',
          '<button class="slash-btn" onclick="execSlash(\'p\')"><span>P</span> Paragrafo</button>' +
          '<button class="slash-btn" onclick="execSlash(\'bullet\')"><span>-</span> Lista</button>' +
          '<button class="slash-btn" onclick="execSlash(\'number\')"><span>1.</span> Lista numerada</button>'
        );
        checkBtn.insertAdjacentHTML('afterend',
          '<button class="slash-btn" onclick="execSlash(\'callout\')"><span>i</span> Callout</button>' +
          '<button class="slash-btn" onclick="execSlash(\'code\')"><span>{ }</span> Codigo</button>' +
          '<button class="slash-btn" onclick="execSlash(\'table\')"><span>| |</span> Tabela</button>' +
          '<button class="slash-btn" onclick="execSlash(\'image\')"><span>img</span> Imagem por URL</button>' +
          '<button class="slash-btn" onclick="execSlash(\'clear\')"><span>Tx</span> Limpar formato</button>'
        );
        slashMenu.dataset.enhanced = '1';
      }
    }
    enhanceSlashMenu();

    ncRich.addEventListener('keydown', (e) => {
      if (e.key === ' ' && applyMarkdownShortcut()) {
        e.preventDefault();
        return;
      }
      if (slashActive && e.key === 'Escape') { slashActive = false; slashMenu.style.display = 'none'; e.preventDefault(); }
    });

    ncRich.addEventListener('keyup', (e) => {
      if (e.key === '/') {
        slashActive = true;
        positionSlashMenu();
        slashMenu.style.display = 'block';
      } else if (slashActive && e.key !== 'Shift') {
        const selText = window.getSelection()?.anchorNode?.textContent || '';
        if (!selText.includes('/')) { slashActive = false; slashMenu.style.display = 'none'; }
      }
      updateActiveBlock();
    });

    function positionSlashMenu() {
      const sel = window.getSelection();
      const rect = sel && sel.rangeCount ? sel.getRangeAt(0).getBoundingClientRect() : ncRich.getBoundingClientRect();
      const editorRect = ncRich.getBoundingClientRect();
      const parentRect = (slashMenu.offsetParent || document.body).getBoundingClientRect();
      const top = Math.min(Math.max(16, parentRect.height - 280), Math.max(16, (rect.top || editorRect.top) - parentRect.top + 24));
      const left = Math.min(Math.max(16, parentRect.width - 260), Math.max(16, (rect.left || editorRect.left) - parentRect.left));
      slashMenu.style.transform = 'none';
      slashMenu.style.top = top + 'px';
      slashMenu.style.left = left + 'px';
    }

    ncRich.addEventListener('click', (e) => {
      if (e.target && e.target.classList.contains('task-toggle')) {
        const block = e.target.closest('.rich-task');
        if (block) {
          block.classList.toggle('done', e.target.checked);
          block.dataset.prefix = e.target.checked ? '- [x] ' : '- [ ] ';
          triggerAutoSave();
        }
      }
      updateActiveBlock();
    });
    document.addEventListener('selectionchange', () => {
      if (document.activeElement === ncRich || ncRich.contains(document.activeElement)) updateActiveBlock();
    });

    function execSlash(cmd) {
      slashMenu.style.display = 'none'; slashActive = false;
      removeTrailingSlashFromRich();
      if (cmd === 'p') setCurrentBlock('p', '', '');
      else if (cmd === 'bullet') insertRichBlock('div', '- ', 'Novo item', 'rich-bullet');
      else if (cmd === 'number') insertRichBlock('div', '1. ', 'Novo item', 'rich-numbered');
      else if (cmd === 'callout') insertRichBlock('div', '> [!note] ', 'Nota importante', 'rich-callout');
      else if (cmd === 'code') insertCodeBlock();
      else if (cmd === 'table') insertTableBlock();
      else if (cmd === 'image') {
        const url = prompt('URL da imagem:');
        if (url) insertImageBlock(url.trim(), 'Imagem');
      }
      else if (cmd === 'clear') clearCurrentBlockFormat();
      if (cmd === 'h1') prefixLine('# ');
      else if (cmd === 'h2') prefixLine('## ');
      else if (cmd === 'h3') prefixLine('### ');
      else if (cmd === 'h4') prefixLine('#### ');
      else if (cmd === 'check') insertRichBlock('div', '- [ ] ', 'Nova tarefa', 'rich-task');
      else if (cmd === 'quote') insertRichBlock('blockquote', '> ', 'Citação');
      else if (cmd === 'hr') insertRichBlock('div', '---', '', 'rich-hr');
      else if (cmd === 'resumo') summarizeNote();
      else if (cmd === 'flashcard') generateFlashcards();
      else if (cmd === 'prof') { document.getElementById('teacherPanel').hidden = false; document.getElementById('teacherQuestion').focus(); }
    }

    function createRichBlock(tag, prefix, text, className) {
      const el = document.createElement(tag);
      el.dataset.prefix = prefix || '';
      if (className) el.className = className;
      if (className === 'rich-bullet' || className === 'rich-numbered') el.dataset.label = 'List';
      else if (className === 'rich-task') el.dataset.label = 'Task';
      else if (className === 'rich-callout') el.dataset.label = 'Callout';
      else if (className === 'rich-code-block') el.dataset.label = 'Code';
      else if (tag === 'blockquote') el.dataset.label = 'Quote';
      else el.dataset.label = BLOCK_LABELS[tag] || '';

      if (prefix === '---') el.innerHTML = '<hr>';
      else if (className === 'rich-task') {
        const checked = prefix === '- [x] ';
        el.classList.toggle('done', checked);
        el.dataset.prefix = checked ? '- [x] ' : '- [ ] ';
        el.innerHTML = '<input type="checkbox" class="task-toggle"' + (checked ? ' checked' : '') + '><span class="task-text">' + inlineFormat(text || '') + '</span>';
      } else if (className === 'rich-code-block') {
        el.innerHTML = '<code>' + esc(text || '') + '</code>';
      } else {
        el.textContent = text || '';
      }
      if (className === 'rich-numbered' && !el.dataset.number) el.dataset.number = '1';
      return el;
    }

    function placeCaretAtEnd(el) {
      const range = document.createRange();
      const sel = window.getSelection();
      range.selectNodeContents(el);
      range.collapse(false);
      sel.removeAllRanges();
      sel.addRange(range);
    }

    function insertElementAtSelection(el) {
      const sel = window.getSelection();
      if (sel && sel.rangeCount && ncRich.contains(sel.anchorNode)) {
        const range = sel.getRangeAt(0);
        range.deleteContents();
        range.insertNode(el);
        range.setStartAfter(el);
        range.collapse(true);
        sel.removeAllRanges();
        sel.addRange(range);
      } else {
        ncRich.appendChild(el);
      }
      decorateRichBlocks();
      ncRich.focus();
    }

    function setCurrentBlock(tag, prefix, className) {
      const current = getCurrentRichBlock();
      const text = current ? (current.textContent || '').replace(/^(\s*```|\s*#{1,4}|\s*[-*]|\s*\d+\.|\s*>\s*|\s*\[\s?\])\s*/, '').trim() : '';
      const next = createRichBlock(tag, prefix, text, className);
      if (current) current.replaceWith(next);
      else insertElementAtSelection(next);
      placeCaretAtEnd(next);
      triggerAutoSave();
    }

    function clearCurrentBlockFormat() {
      setCurrentBlock('p', '', '');
    }

    function insertCodeBlock() {
      insertRichBlock('pre', '```', 'codigo', 'rich-code-block');
    }

    function insertTableBlock() {
      const table = document.createElement('table');
      table.className = 'rich-table';
      table.dataset.label = 'Table';
      table.innerHTML = '<thead><tr><th>Conceito</th><th>Resumo</th></tr></thead><tbody><tr><td></td><td></td></tr><tr><td></td><td></td></tr></tbody>';
      insertElementAtSelection(table);
      triggerAutoSave();
    }

    function insertImageBlock(src, alt) {
      if (!src) return;
      const el = document.createElement('div');
      el.dataset.prefix = '';
      el.dataset.label = 'Image';
      el.innerHTML = '<img src="' + esc(src) + '" alt="' + esc(alt || 'Imagem') + '">';
      insertElementAtSelection(el);
      triggerAutoSave();
    }

    function applyMarkdownShortcut() {
      const block = getCurrentRichBlock();
      if (!block) return false;
      const marker = (block.textContent || '').trim();
      if (marker === '#') { setCurrentBlock('h1', '# ', ''); return true; }
      if (marker === '##') { setCurrentBlock('h2', '## ', ''); return true; }
      if (marker === '###') { setCurrentBlock('h3', '### ', ''); return true; }
      if (marker === '####') { setCurrentBlock('h4', '#### ', ''); return true; }
      if (marker === '-' || marker === '*') { setCurrentBlock('div', '- ', 'rich-bullet'); return true; }
      if (marker === '1.') { setCurrentBlock('div', '1. ', 'rich-numbered'); return true; }
      if (marker === '[]' || marker === '[ ]') { setCurrentBlock('div', '- [ ] ', 'rich-task'); return true; }
      if (marker === '>') { setCurrentBlock('blockquote', '> ', ''); return true; }
      if (marker === '```') { setCurrentBlock('pre', '```', 'rich-code-block'); return true; }
      return false;
    }

    function insertText(prefix) {
      document.execCommand('insertText', false, prefix);
      ncRich.focus(); triggerAutoSave();
    }

    function removeTrailingSlashFromRich() {
      const sel = window.getSelection();
      const node = sel && sel.anchorNode;
      if (!node || node.nodeType !== Node.TEXT_NODE) return;
      const offset = sel.anchorOffset || 0;
      const text = node.nodeValue || '';
      if (text.slice(Math.max(0, offset - 1), offset) !== '/') return;
      node.nodeValue = text.slice(0, offset - 1) + text.slice(offset);
      const range = document.createRange();
      range.setStart(node, Math.max(0, offset - 1));
      range.collapse(true);
      sel.removeAllRanges();
      sel.addRange(range);
    }

    function insertRichBlock(tag, prefix, text, className) {
      const el = createRichBlock(tag, prefix, text, className);
      insertElementAtSelection(el);
      triggerAutoSave();
    }

    // Drag and Drop
    ncRich.addEventListener('dragover', e => { e.preventDefault(); });
    ncRich.addEventListener('drop', e => {
      e.preventDefault();
      if(e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        if(file.type.startsWith('image/')) {
          const reader = new FileReader();
          reader.onload = (ev) => { insertImageBlock(ev.target.result, file.name || 'Imagem'); };
          reader.readAsDataURL(file);
        }
      }
    });

    function esc(value) { return String(value ?? '').replace(/[&<>"']/g, ch => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":"&#39;" }[ch])); }

    function renderNoteReceipt() {
      const r = boot.receipt || {};
      const animate = String(boot.animate || r.action || '').trim();
      if (!(r.kind === 'note' || ['note_summarize', 'teacher_mode', 'subject_teacher_mode', 'note_media_attach'].includes(animate))) return;
      document.getElementById('noteReceipt').hidden = false;
      document.getElementById('receiptNoteTitle').textContent = 'Ação IA concluída';
      document.getElementById('receiptNoteMeta').textContent = boot.toast || 'Operação realizada com sucesso.';
      setTimeout(() => document.getElementById('noteReceipt').hidden = true, 5000);
    }

    function parseMediaLinks(raw) { try { const p = JSON.parse(raw || '[]'); return Array.isArray(p) ? p : []; } catch(_) { return []; } }

    function renderMediaStrip() {
      const strip = document.getElementById('mediaStrip');
      strip.hidden = !currentMedia.length;
      strip.innerHTML = currentMedia.map(item => '<div style="background: rgba(0,0,0,0.2); border:1px solid rgba(255,255,255,0.05); padding: 4px; border-radius: 6px; display:flex; align-items:center; gap:8px;"><img src="' + esc(item.url || item.path) + '" style="height:28px; border-radius:4px; object-fit:cover;" /><span style="font-size:10px; color:var(--text);">' + esc(item.caption || 'Mídia') + '</span></div>').join('');
    }

    function addFrontmatter(key, value) {
      if(!value) return;
      syncMarkdownFromRich();
      let content = nc.value;
      if(content.startsWith('---\n')) {
        const end = content.indexOf('\n---\n', 4);
        if(end !== -1) {
          const fm = content.substring(4, end);
          const lines = fm.split('\n').filter(l => !l.startsWith(key + ':'));
          lines.push(key + ': ' + value);
          nc.value = '---\n' + lines.join('\n') + '\n---\n' + content.substring(end + 5);
        } else { nc.value = '---\n' + key + ': ' + value + '\n---\n\n' + content; }
      } else { nc.value = '---\n' + key + ': ' + value + '\n---\n\n' + content; }
      syncRichFromMarkdown();
      triggerAutoSave();
    }

    function parseFrontmatter(text) {
      const match = text.match(/^---\n([\s\S]*?)\n---/);
      if(!match) return { icon: null, cover: null, cleanContent: text };
      const fm = match[1]; let icon = null; let cover = null;
      fm.split('\n').forEach(line => {
        if(line.startsWith('icon:')) icon = line.replace('icon:', '').trim();
        if(line.startsWith('cover:')) cover = line.replace('cover:', '').trim();
      });
      return { icon, cover, cleanContent: text.replace(/^---\n[\s\S]*?\n---\n/, '') };
    }

    // Enhanced Markdown Preview with proper heading hierarchy
    function renderNotePreview() {
      const target = document.getElementById('notePreview');
      const toc = document.getElementById('tocContent');
      let rawContent = nc.value || '';

      const parsed = parseFrontmatter(rawContent);
      const coverEl = document.getElementById('pageCover');
      const iconEl = document.getElementById('pageIcon');

      if(parsed.cover) { coverEl.style.backgroundImage = 'url(' + esc(parsed.cover) + ')'; coverEl.classList.add('active'); }
      else { coverEl.classList.remove('active'); }
      if(parsed.icon) { iconEl.textContent = parsed.icon; iconEl.classList.add('active'); }
      else { iconEl.classList.remove('active'); }

      const lines = parsed.cleanContent.split(/\r?\n/);
      const parts = [];
      const tocItems = [];
      let headingId = 0;

      lines.forEach(line => {
        const text = line.trim();
        if (!text) { parts.push('<br/>'); return; }

        const img = text.match(/^!\[(.*?)\]\((.*?)\)$/);
        if (img) { parts.push('<img src="' + esc(img[2] || '') + '" alt="' + esc(img[1] || '') + '" />'); return; }

        if (text === '---' || text === '***') { parts.push('<hr/>'); return; }

        // Headings with proper visual hierarchy
        if (text.startsWith('#### ')) {
          headingId++;
          parts.push('<h4 id="head-' + headingId + '">' + inlineFormat(text.slice(5)) + '</h4>');
          tocItems.push('<a href="#head-' + headingId + '" class="toc-item level-4" onclick="document.getElementById(\'head-' + headingId + '\').scrollIntoView({behavior:\'smooth\'}); return false;">' + esc(text.slice(5)) + '</a>');
        }
        else if (text.startsWith('### ')) {
          headingId++;
          parts.push('<h3 id="head-' + headingId + '">' + inlineFormat(text.slice(4)) + '</h3>');
          tocItems.push('<a href="#head-' + headingId + '" class="toc-item level-3" onclick="document.getElementById(\'head-' + headingId + '\').scrollIntoView({behavior:\'smooth\'}); return false;">' + esc(text.slice(4)) + '</a>');
        }
        else if (text.startsWith('## ')) {
          headingId++;
          parts.push('<h2 id="head-' + headingId + '">' + inlineFormat(text.slice(3)) + '</h2>');
          tocItems.push('<a href="#head-' + headingId + '" class="toc-item level-2" onclick="document.getElementById(\'head-' + headingId + '\').scrollIntoView({behavior:\'smooth\'}); return false;">' + esc(text.slice(3)) + '</a>');
        }
        else if (text.startsWith('# ')) {
          headingId++;
          parts.push('<h1 id="head-' + headingId + '">' + inlineFormat(text.slice(2)) + '</h1>');
          tocItems.push('<a href="#head-' + headingId + '" class="toc-item" style="font-weight:700;" onclick="document.getElementById(\'head-' + headingId + '\').scrollIntoView({behavior:\'smooth\'}); return false;">' + esc(text.slice(2)) + '</a>');
        }
        else if (text.startsWith('- [ ]')) parts.push('<div><input type="checkbox" disabled style="margin-right:6px;">' + inlineFormat(text.slice(5)) + '</div>');
        else if (text.startsWith('- [x]')) parts.push('<div><input type="checkbox" disabled checked style="margin-right:6px;"><del>' + inlineFormat(text.slice(5)) + '</del></div>');
        else if (text.startsWith('- ') || text.startsWith('* ')) parts.push('<div>&bull; ' + inlineFormat(text.slice(2)) + '</div>');
        else if (text.startsWith('> ')) parts.push('<blockquote>' + inlineFormat(text.slice(2)) + '</blockquote>');
        else if (/^\d+\.\s/.test(text)) { const m = text.match(/^\d+\.\s(.*)$/); parts.push('<div style="padding-left:4px;">' + text.match(/^\d+/)[0] + '. ' + inlineFormat(m[1]) + '</div>'); }
        else parts.push('<p>' + inlineFormat(text) + '</p>');
      });

      target.innerHTML = parts.length ? parts.join('') : '<div style="color:var(--text-dim);opacity:0.3;padding:20px 0;">Escreva markdown para ver o preview...</div>';
      toc.innerHTML = tocItems.length ? tocItems.join('') : '<div style="font-size:10px; color:var(--text-dim); opacity:0.4;">Use # ## ### #### para títulos</div>';
    }

    // Inline formatting: bold, italic, code, strikethrough, highlight
    function inlineFormat(text) {
      let s = esc(text);
      s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
      s = s.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      s = s.replace(/\*(.+?)\*/g, '<em>$1</em>');
      s = s.replace(/~~(.+?)~~/g, '<del>$1</del>');
      s = s.replace(/==(.+?)==/g, '<mark style="background:rgba(250,204,21,0.25);color:var(--text);padding:1px 3px;border-radius:3px;">$1</mark>');
      return s;
    }

    function extractTags(notes) {
      const tagSet = new Set();
      notes.forEach(n => { const matches = (n.content || '').match(/#\w+/g); if(matches) matches.forEach(t => tagSet.add(t)); });
      return Array.from(tagSet).sort();
    }

    function renderSubjectRail(notes) {
      const rail = document.getElementById('subjectRail');
      const counts = {};
      (notes || []).forEach(n => { const s = String(n.subject || 'Geral').trim() || 'Geral'; counts[s] = (counts[s] || 0) + 1; });
      rail.innerHTML = '<button type="button" class="subject-chip' + (!activeSubject ? ' active' : '') + '" onclick="activeSubject=\'\';renderSubjectRail(allNotes);renderNav();if(currentView===\'cards\')renderCards();">📁 Todas <span class="count">' + (notes || []).length + '</span></button>' +
        Object.keys(counts).sort().map(s => '<button type="button" class="subject-chip' + (activeSubject === s ? ' active' : '') + '" onclick="activeSubject=\'' + esc(s) + '\';renderSubjectRail(allNotes);renderNav();if(currentView===\'cards\')renderCards();">📁 ' + esc(s) + ' <span class="count">' + counts[s] + '</span></button>').join('');

      const tags = extractTags(notes);
      const tagsRail = document.getElementById('tagsRail');
      if(tags.length === 0) { tagsRail.innerHTML = '<div style="font-size:10px;color:var(--text-dim);opacity:0.4;">Use #tags no texto</div>'; }
      else { tagsRail.innerHTML = tags.map(t => '<button class="tag-chip ' + (activeTag === t ? 'active' : '') + '" onclick="toggleTag(\'' + esc(t) + '\')">' + esc(t) + '</button>').join(''); }
    }

    function toggleTag(t) { activeTag = activeTag === t ? '' : t; renderSubjectRail(allNotes); renderNav(); if(currentView === 'cards') renderCards(); }

    function renderOpenTabs(activeOrTempId) {
      const tabs = document.getElementById('openTabs');
      let html = '<button class="icon-btn" onclick="toggleSidebar()" title="Sidebar" style="margin-right: 6px;">☰</button>';
      html += openNoteTabs.map(tab => '<div class="affine-tab' + ((Number(tab.id) === Number(activeId) || tab.id === activeOrTempId) ? ' active' : '') + '" data-tab-id="' + tab.id + '"><button class="affine-tab-title">' + esc(tab.title) + '</button><button class="affine-tab-close" data-close-id="' + tab.id + '">×</button></div>').join('');
      tabs.innerHTML = html;
      tabs.querySelectorAll('.affine-tab-title').forEach(btn => btn.onclick = () => {
        const tid = btn.parentElement.dataset.tabId;
        if(String(tid).startsWith('temp-')) return;
        openNote(parseInt(tid));
      });
      tabs.querySelectorAll('.affine-tab-close').forEach(btn => {
        btn.onclick = (e) => {
          e.stopPropagation();
          const id = String(btn.dataset.closeId);
          openNoteTabs = openNoteTabs.filter(tab => String(tab.id) !== id);
          if ((String(activeId) === id || activeOrTempId === id) && openNoteTabs.length > 0) {
            if(String(openNoteTabs[0].id).startsWith('temp-')) document.getElementById('btnNew').click();
            else openNote(openNoteTabs[0].id);
          }
          else if (openNoteTabs.length === 0) document.getElementById('btnNew').click();
          else renderOpenTabs();
        };
      });
    }

    function renderNav() {
      const nav = document.getElementById('nav');
      let notes = allNotes;
      if(activeSubject) notes = notes.filter(n => (n.subject || 'Geral').trim() === activeSubject);
      if(activeTag) notes = notes.filter(n => (n.content || '').includes(activeTag));
      if(searchQuery) notes = notes.filter(n => (n.title || '').toLowerCase().includes(searchQuery) || (n.content || '').toLowerCase().includes(searchQuery));

      const favs = notes.filter(n => favNotesIds.includes(n.id));
      const others = notes.filter(n => !favNotesIds.includes(n.id));

      let html = '';
      if(favs.length > 0) {
        html += '<div class="nav-group-title">Favoritas</div>';
        html += favs.map(n => {
          const dotColor = getColorCSS(n.color || 'none');
          return '<button type="button" class="note-btn' + (n.id === activeId ? ' active' : '') + '" onclick="openNote(' + n.id + ')">' +
            (dotColor !== 'transparent' ? '<span class="note-btn-dot" style="background:' + dotColor + ';"></span>' : '') +
            '<span class="note-btn-icon" style="color:#facc15;">★</span> ' + esc(n.title || 'Sem título') + '</button>';
        }).join('');
      }
      if(others.length > 0) {
        if(favs.length > 0) html += '<div class="nav-group-title">Todas</div>';
        html += others.map(n => {
          const dotColor = getColorCSS(n.color || 'none');
          return '<button type="button" class="note-btn' + (n.id === activeId ? ' active' : '') + '" onclick="openNote(' + n.id + ')">' +
            (dotColor !== 'transparent' ? '<span class="note-btn-dot" style="background:' + dotColor + ';"></span>' : '') +
            esc(n.title || 'Sem título') + '</button>';
        }).join('');
      }
      if(!notes.length) html = '<div style="font-size:11px;color:var(--text-dim);padding:8px;opacity:0.5;">Sem notas.</div>';
      nav.innerHTML = html;
      renderOpenTabs();
    }

    async function loadNav() { const r = await nxBridge('notes_list', {}); if (r.ok) { allNotes = r.data || []; renderSubjectRail(allNotes); renderNav(); } }

    async function openNote(id) {
      activeId = id;
      const r = await nxBridge('note_get', { note_id: id });
      if (!r.ok || !r.data) return;
      document.getElementById('nt').value = r.data.title || '';
      document.getElementById('ns').value = r.data.subject || 'Geral';
      setEditorMarkdown(r.data.content || '');
      currentColor = r.data.color || null;
      renderColorPicker();
      const ind = document.getElementById('saveIndicator');
      ind.className = 'save-indicator saved';
      ind.querySelector('.save-text').textContent = 'Salvo';

      if(favNotesIds.includes(id)) document.getElementById('btnFav').classList.add('is-fav');
      else document.getElementById('btnFav').classList.remove('is-fav');

      currentMedia = parseMediaLinks(r.data.media_links);
      const item = { id: Number(id), title: r.data.title || 'Sem título' };
      openNoteTabs = openNoteTabs.filter(tab => Number(tab.id) !== item.id);
      openNoteTabs.unshift(item); openNoteTabs = openNoteTabs.slice(0, 8);
      renderMediaStrip(); renderNotePreview(); loadNav();
      if (currentView === 'cards') setView('editor');
    }

    document.getElementById('btnNew').onclick = () => {
      activeId = null; currentMedia = []; currentColor = null;
      document.getElementById('nt').value = ''; document.getElementById('ns').value = activeSubject || 'Geral'; setEditorMarkdown('');
      const ind = document.getElementById('saveIndicator');
      ind.className = 'save-indicator'; ind.querySelector('.save-text').textContent = 'Nova';
      document.getElementById('btnFav').classList.remove('is-fav');
      renderColorPicker();
      const tempId = 'temp-' + Date.now();
      const item = { id: tempId, title: 'Nova Nota', isTemp: true };
      openNoteTabs = openNoteTabs.filter(t => !t.isTemp);
      openNoteTabs.unshift(item); openNoteTabs = openNoteTabs.slice(0, 8);
      renderMediaStrip(); renderNotePreview(); renderOpenTabs(tempId); loadNav();
      if (currentView === 'cards') setView('editor');
    };

    document.getElementById('btnNewSubject').onclick = () => {
      const subjectName = prompt('Nome da Nova Matéria:');
      if (!subjectName) return;
      activeSubject = subjectName.trim();
      document.getElementById('btnNew').click();
      document.getElementById('ns').value = activeSubject;
      document.getElementById('nt').focus();
      triggerAutoSave();
    };

    let isSaving = false;
    async function saveNote() {
      if (isSaving) return;
      isSaving = true;
      const wasNew = !activeId;
      const title = document.getElementById('nt').value.trim() || 'Sem título';
      const subject = document.getElementById('ns').value.trim() || 'Geral';
      const content = getEditorMarkdown();
      const ind = document.getElementById('saveIndicator');
      ind.className = 'save-indicator saving'; ind.querySelector('.save-text').textContent = 'Salvando';

      const args = activeId ? { note_id: activeId, title, subject, content, color: currentColor } : { subject, title, content, media: currentMedia, color: currentColor };
      const r = await nxBridge(activeId ? 'note_patch' : 'note_save', args);

      if (r.ok) {
        if (!activeId && r.data && r.data.id) { activeId = r.data.id; openNoteTabs = openNoteTabs.filter(t => !t.isTemp); }
        ind.className = 'save-indicator saved'; ind.querySelector('.save-text').textContent = 'Salvo';
        const item = { id: activeId, title };
        openNoteTabs = openNoteTabs.filter(t => Number(t.id) !== Number(item.id)); openNoteTabs.unshift(item); openNoteTabs = openNoteTabs.slice(0, 8);
        const cached = allNotes.find(n => Number(n.id) === Number(activeId));
        if (cached) {
          cached.title = title;
          cached.subject = subject;
          cached.content = content;
          cached.color = currentColor;
        } else if (activeId) {
          allNotes.unshift({ id: activeId, title, subject, content, color: currentColor, updated_at: new Date().toISOString() });
        }
        renderSubjectRail(allNotes);
        renderNav();
        if (currentView === 'cards') renderCards();
        if (wasNew) schedulePreviewRender(40);
      } else {
        ind.className = 'save-indicator error'; ind.querySelector('.save-text').textContent = 'Erro';
      }
      isSaving = false;
    }
    document.getElementById('btnSaveManual').onclick = saveNote;

    async function summarizeNote() {
      if (!activeId) return;
      document.getElementById('noteReceipt').hidden = false; document.getElementById('receiptNoteTitle').textContent = 'Resumindo...';
      const r = await nxBridge('note_summarize', { note_id: activeId, append_summary: true, max_sentences: 4 });
      if (r.ok) { const ref = await nxBridge('note_get', { note_id: activeId }); if (ref.ok && ref.data) { setEditorMarkdown(ref.data.content || ''); } }
    }

    function renderFlashcardPreview(cards, scope) {
      document.getElementById('flashcardPreview').hidden = false;
      document.getElementById('flashcardPreviewTitle').textContent = 'Flashcards · ' + scope;
      document.getElementById('flashcardPreviewMeta').textContent = cards.length + ' cards gerados pela IA';
      document.getElementById('studyStatus').textContent = cards.length ? 'Flashcards enviados para revisao.' : 'Nenhum flashcard gerado.';
      document.getElementById('flashcardPreviewList').innerHTML = cards.map(c =>
        '<div class="flashcard-card" style="padding:10px;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.05);"><div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:4px;">' + esc(c.front) + '</div><div style="font-size:11px;color:var(--text-dim);">' + esc(c.back) + '</div></div>'
      ).join('');
    }

    document.getElementById('btnFlashcards').onclick = () => { if(activeId) generateFlashcards(); };
    document.getElementById('btnSubjectFlashcards').onclick = () => { generateSubjectFlashcards(); };
    document.getElementById('btnSubjectTeacher').onclick = () => { askSubjectTeacher(); };
    document.getElementById('btnSummarize').onclick = summarizeNote;
    document.getElementById('btnTeacher').onclick = () => { if(activeId) { document.getElementById('teacherPanel').hidden = false; document.getElementById('teacherQuestion').focus(); } };
    document.getElementById('btnDel').onclick = async () => { if (!activeId || !confirm('Excluir esta nota?')) return; await nxBridge('note_delete', { note_id: activeId }); document.getElementById('btnNew').click(); };

    async function generateFlashcards() { const r = await nxBridge('flashcards_generate', { note_id: activeId, max_cards: 8 }); if (r.ok) renderFlashcardPreview((r.data && r.data.cards) || [], 'Nota atual'); }
    async function generateSubjectFlashcards() { const s = (activeSubject || document.getElementById('ns').value || '').trim(); if(!s) return; const r = await nxBridge('flashcards_generate', { subject: s, max_cards: 20 }); if (r.ok) renderFlashcardPreview((r.data && r.data.cards) || [], 'Matéria'); }
    function renderTeacherOutput(d) { document.getElementById('teacherOutput').innerHTML = '<p>' + esc(d.lesson || 'Pronto.') + '</p>' + ((d.key_points || []).map(p => '<li>' + esc(p) + '</li>').join('')); }
    async function askTeacher() { const q = document.getElementById('teacherQuestion').value.trim(); document.getElementById('teacherOutput').innerHTML = 'Processando...'; const r = await nxBridge('note_teach', { note_id: activeId, question: q, max_points: 4 }); if (r.ok && r.data) renderTeacherOutput(r.data); }
    async function askSubjectTeacher() { const s = (activeSubject || document.getElementById('ns').value || '').trim(); document.getElementById('teacherPanel').hidden = false; document.getElementById('teacherOutput').innerHTML = 'Processando...'; const q = document.getElementById('teacherQuestion').value.trim(); const r = await nxBridge('subject_teach', { subject: s, question: q, max_points: 6 }); if (r.ok && r.data) renderTeacherOutput(r.data); }
    async function attachMedia() { const url = document.getElementById('mediaUrl').value.trim(); const cap = document.getElementById('mediaCaption').value.trim(); if (!url) return; const r = await nxBridge('note_attach_media', { note_id: activeId, media_url: url, caption: cap }); if (r.ok) { const ref = await nxBridge('note_get', { note_id: activeId }); if (ref.ok && ref.data) currentMedia = parseMediaLinks(ref.data.media_links); document.getElementById('mediaPanel').hidden = true; renderMediaStrip(); } }
    document.getElementById('btnAttachMedia').onclick = attachMedia;
    async function captureNote() { const title = document.getElementById('captureTitle').value.trim(); const subject = document.getElementById('captureSubject').value.trim(); const url = document.getElementById('captureUrl').value.trim(); const content = document.getElementById('captureContent').value.trim(); if (!title || !content) return; const r = await nxBridge('note_capture', { title, subject, url, content }); if (r.ok) { document.getElementById('noteCaptureForm').hidden = true; if (r.data && r.data.note_id) openNote(r.data.note_id); } }

    renderColorPicker();
    renderNoteReceipt(); syncRichFromMarkdown(); renderNotePreview();
    loadNav().then(() => { if (boot.highlight_id) openNote(Number(boot.highlight_id)); });
    window.addEventListener('message', (e) => { if (e.data === 'nexus-tab-focus') loadNav(); });