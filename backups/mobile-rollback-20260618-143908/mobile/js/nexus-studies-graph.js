/** Nexus Mobile — nexus-studies-graph.js */
// ================================================================
// STUDIES 3.0: NOTION COVERS & OBSIDIAN GRAPH VIEW
// ================================================================

// ─── Covers & Icons (Notion Style) ───────────────────────────────

function changeNoteCover() {
    // Create an invisible file input
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;
        if (file.size > 2 * 1024 * 1024) {
            alert('A capa deve ter no máximo 2MB.');
            return;
        }
        const reader = new FileReader();
        reader.onload = (ev) => {
            const dataUrl = ev.target.result;
            // Update UI
            document.getElementById('note-cover-container').style.display = 'block';
            document.getElementById('note-cover-container').style.backgroundImage = `url(${dataUrl})`;
            document.getElementById('add-cover-btn').style.display = 'none';
            // Save to LocalDB immediately if it's an existing note
            const titleEl = document.getElementById('note-title');
            if (titleEl && titleEl.dataset.noteId) {
                const notes = LocalDB.getAll('notes') || [];
                const n = notes.find(x => x.id === titleEl.dataset.noteId);
                if (n) {
                    n.coverImage = dataUrl;
                    LocalDB.saveAll('notes', notes);
                }
            } else {
                // If new note, save temporarily in a global var so saveNote grabs it
                window._tempCoverImage = dataUrl;
            }
        };
        reader.readAsDataURL(file);
    };
    input.click();
}

function removeNoteCover() {
    document.getElementById('note-cover-container').style.display = 'none';
    document.getElementById('note-cover-container').style.backgroundImage = 'none';
    document.getElementById('add-cover-btn').style.display = 'inline-block';
    
    const titleEl = document.getElementById('note-title');
    if (titleEl && titleEl.dataset.noteId) {
        const notes = LocalDB.getAll('notes') || [];
        const n = notes.find(x => x.id === titleEl.dataset.noteId);
        if (n) {
            delete n.coverImage;
            LocalDB.saveAll('notes', notes);
        }
    }
    window._tempCoverImage = null;
}

function changeNoteIcon() {
    const icon = prompt('Digite um Emoji para usar de ícone:');
    if (icon) {
        // Grab only the first character or emoji
        const firstEmoji = Array.from(icon)[0];
        document.getElementById('note-icon-display').textContent = firstEmoji;
        
        const titleEl = document.getElementById('note-title');
        if (titleEl && titleEl.dataset.noteId) {
            const notes = LocalDB.getAll('notes') || [];
            const n = notes.find(x => x.id === titleEl.dataset.noteId);
            if (n) {
                n.icon = firstEmoji;
                LocalDB.saveAll('notes', notes);
            }
        } else {
            window._tempIcon = firstEmoji;
        }
    }
}

// Hook into openNoteEditor to load covers and icons
const _origOpenNoteEditorForCover = window.openNoteEditor;
window.openNoteEditor = function(noteOrId, notebookId) {
    if (typeof _origOpenNoteEditorForCover === 'function') _origOpenNoteEditorForCover(noteOrId, notebookId);

    window._tempCoverImage = null;
    window._tempIcon = null;

    setTimeout(() => {
        let note = null;
        if (noteOrId && typeof noteOrId === 'object') note = noteOrId;
        else if (noteOrId) {
            const notes = LocalDB.get('study_notes') || [];
            note = notes.find(n => String(n.id) === String(noteOrId)) || null;
        }

        const titleEl = document.getElementById('note-title');
        if (titleEl) titleEl.dataset.noteId = note ? note.id : '';

        const coverContainer = document.getElementById('note-cover-container');
        const addBtn = document.getElementById('add-cover-btn');
        if (coverContainer) {
            if (note && note.coverImage) {
                coverContainer.style.display = 'block';
                coverContainer.style.backgroundImage = 'url(' + note.coverImage + ')';
                if (addBtn) addBtn.style.display = 'none';
            } else {
                coverContainer.style.display = 'none';
                coverContainer.style.backgroundImage = 'none';
                if (addBtn) addBtn.style.display = 'inline-block';
            }
        }

        const iconDisplay = document.getElementById('note-icon-display');
        if (iconDisplay) iconDisplay.textContent = (note && note.icon) ? note.icon : '📄';

        renderBacklinks(note ? note.id : null);
    }, 100);
};

// Hook into saveNote to include cover and icon
const _origSaveNoteForCover = window.saveNote;
window.saveNote = function() {
    // Before saving, ensure we don't lose the cover/icon on new notes
    if (typeof _origSaveNoteForCover === 'function') _origSaveNoteForCover();
    
    // After save, the note is in LocalDB. If it was new, it has no ID attached to titleEl yet,
    // but the saveNote function should have created it. We need to find the latest note.
    const notes = LocalDB.getAll('notes') || [];
    const titleEl = document.getElementById('note-title');
    let currentNote = null;
    
    if (titleEl && titleEl.dataset.noteId) {
        currentNote = notes.find(n => n.id === titleEl.dataset.noteId);
    } else {
        // It was a new note. Find it by title and content (heuristic)
        const t = titleEl ? titleEl.value : '';
        currentNote = notes.find(n => n.title === t);
        if (currentNote && titleEl) titleEl.dataset.noteId = currentNote.id;
    }
    
    if (currentNote) {
        let changed = false;
        if (window._tempCoverImage) { currentNote.coverImage = window._tempCoverImage; changed = true; window._tempCoverImage = null; }
        if (window._tempIcon) { currentNote.icon = window._tempIcon; changed = true; window._tempIcon = null; }
        if (changed) { LocalDB.saveAll('notes', notes); }
    }
};

// ─── Backlinks (Linked Mentions) ─────────────────────────────────

function renderBacklinks(noteId) {
    const panel = document.getElementById('backlinks-panel');
    const list = document.getElementById('backlinks-list');
    if (!panel || !list) return;
    
    if (!noteId) {
        panel.style.display = 'none';
        return;
    }
    
    const notes = LocalDB.getAll('notes') || [];
    // A backlink exists if another note's content contains our noteId in a data-note-id attribute
    const backlinks = notes.filter(n => n.id !== noteId && n.content && n.content.includes(noteId));
    
    if (backlinks.length === 0) {
        panel.style.display = 'none';
        return;
    }
    
    panel.style.display = 'block';
    list.innerHTML = '';
    
    backlinks.forEach(bl => {
        const item = document.createElement('div');
        item.style.padding = '12px';
        item.style.background = 'rgba(255,255,255,0.05)';
        item.style.borderRadius = '8px';
        item.style.border = '1px solid var(--border-glass)';
        item.style.cursor = 'pointer';
        item.innerHTML = `
            <div style="font-weight:bold;color:var(--accent-blue);margin-bottom:4px">${bl.icon || '📄'} ${bl.title || 'Sem título'}</div>
            <div style="font-size:0.8rem;color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(bl.content || '').replace(/<[^>]+>/g, ' ').substring(0, 100)}...</div>
        `;
        item.onclick = () => {
            closeNoteEditor();
            setTimeout(() => openNoteEditor(bl, bl.notebookId), 300);
        };
        list.appendChild(item);
    });
}

// ─── Graph View (Obsidian Style) ─────────────────────────────────

let _graphAnimation = null;
let _graphNodes = [];
let _graphEdges = [];
let _graphCamera = { x: 0, y: 0, zoom: 1 };
let _isDraggingGraph = false;
let _draggedNode = null;
let _lastMousePos = { x: 0, y: 0 };

function openGraphView() {
    const view = document.getElementById('graph-view');
    if (!view) return;
    view.style.display = 'block';
    initGraphData();
    startGraphPhysics();
}

function closeGraphView() {
    document.getElementById('graph-view').style.display = 'none';
    if (_graphAnimation) cancelAnimationFrame(_graphAnimation);
}

function initGraphData() {
    const notes = LocalDB.getAll('notes') || [];
    const canvas = document.getElementById('graph-canvas');
    if (!canvas) return;
    const w = window.innerWidth;
    const h = window.innerHeight;
    
    _graphNodes = notes.map(n => ({
        id: n.id,
        title: n.title || 'Nota',
        icon: n.icon || '📄',
        x: w/2 + (Math.random() - 0.5) * 200,
        y: h/2 + (Math.random() - 0.5) * 200,
        vx: 0, vy: 0,
        radius: 12
    }));
    
    _graphEdges = [];
    notes.forEach(n => {
        if (!n.content) return;
        notes.forEach(target => {
            if (n.id !== target.id && n.content.includes(target.id)) {
                _graphEdges.push({ source: n.id, target: target.id });
            }
        });
    });
    
    _graphCamera = { x: 0, y: 0, zoom: 1 };
    
    // Bind events
    canvas.width = w;
    canvas.height = h;
    canvas.onmousedown = handleGraphPointerDown;
    canvas.onmousemove = handleGraphPointerMove;
    canvas.onmouseup = handleGraphPointerUp;
    canvas.onmouseleave = handleGraphPointerUp;
    canvas.ontouchstart = (e) => handleGraphPointerDown(e.touches[0]);
    canvas.ontouchmove = (e) => handleGraphPointerMove(e.touches[0]);
    canvas.ontouchend = handleGraphPointerUp;
    
    // Canvas wheel zoom
    canvas.onwheel = (e) => {
        e.preventDefault();
        _graphCamera.zoom -= e.deltaY * 0.001;
        if (_graphCamera.zoom < 0.2) _graphCamera.zoom = 0.2;
        if (_graphCamera.zoom > 3) _graphCamera.zoom = 3;
    };
}

function startGraphPhysics() {
    const canvas = document.getElementById('graph-canvas');
    const ctx = canvas.getContext('2d');
    
    function draw() {
        // Physics Loop (Force Directed)
        const k = 0.05; // spring constant
        const repulse = 1000; // repulsion strength
        const damping = 0.85;
        
        // 1. Repulsion between nodes
        for (let i = 0; i < _graphNodes.length; i++) {
            for (let j = i + 1; j < _graphNodes.length; j++) {
                const n1 = _graphNodes[i];
                const n2 = _graphNodes[j];
                const dx = n2.x - n1.x;
                const dy = n2.y - n1.y;
                const distSq = dx*dx + dy*dy;
                if (distSq < 0.1) continue;
                const dist = Math.sqrt(distSq);
                const force = repulse / distSq;
                const fx = (dx/dist) * force;
                const fy = (dy/dist) * force;
                n1.vx -= fx; n1.vy -= fy;
                n2.vx += fx; n2.vy += fy;
            }
        }
        
        // 2. Attraction along edges
        _graphEdges.forEach(e => {
            const n1 = _graphNodes.find(n => n.id === e.source);
            const n2 = _graphNodes.find(n => n.id === e.target);
            if (!n1 || !n2) return;
            const dx = n2.x - n1.x;
            const dy = n2.y - n1.y;
            const dist = Math.sqrt(dx*dx + dy*dy);
            const force = (dist - 80) * k;
            const fx = (dx/dist) * force;
            const fy = (dy/dist) * force;
            n1.vx += fx; n1.vy += fy;
            n2.vx -= fx; n2.vy -= fy;
        });
        
        // 3. Central gravity
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        _graphNodes.forEach(n => {
            const dx = cx - n.x;
            const dy = cy - n.y;
            n.vx += dx * 0.005;
            n.vy += dy * 0.005;
            
            // Apply velocity
            if (_draggedNode !== n) {
                n.x += n.vx;
                n.y += n.vy;
            }
            // Damping
            n.vx *= damping;
            n.vy *= damping;
        });
        
        // Rendering
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        ctx.save();
        ctx.translate(canvas.width/2 + _graphCamera.x, canvas.height/2 + _graphCamera.y);
        ctx.scale(_graphCamera.zoom, _graphCamera.zoom);
        ctx.translate(-canvas.width/2, -canvas.height/2);
        
        // Draw edges
        ctx.strokeStyle = 'rgba(108, 92, 231, 0.4)';
        ctx.lineWidth = 1.5;
        _graphEdges.forEach(e => {
            const n1 = _graphNodes.find(n => n.id === e.source);
            const n2 = _graphNodes.find(n => n.id === e.target);
            if (!n1 || !n2) return;
            ctx.beginPath();
            ctx.moveTo(n1.x, n1.y);
            ctx.lineTo(n2.x, n2.y);
            ctx.stroke();
        });
        
        // Draw nodes
        ctx.font = '12px "Inter", sans-serif';
        _graphNodes.forEach(n => {
            // Node circle
            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
            ctx.fillStyle = _draggedNode === n ? '#fd79a8' : '#6c5ce7';
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // Icon
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#fff';
            ctx.fillText(n.icon, n.x, n.y);
            
            // Title
            ctx.fillStyle = 'rgba(255,255,255,0.85)';
            ctx.fillText(n.title.substring(0, 15), n.x, n.y + 22);
        });
        
        ctx.restore();
        
        _graphAnimation = requestAnimationFrame(draw);
    }
    
    draw();
}

function handleGraphPointerDown(e) {
    const canvas = document.getElementById('graph-canvas');
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    
    // Convert to world coordinates
    const wx = (mx - canvas.width/2 - _graphCamera.x) / _graphCamera.zoom + canvas.width/2;
    const wy = (my - canvas.height/2 - _graphCamera.y) / _graphCamera.zoom + canvas.height/2;
    
    _lastMousePos = { x: mx, y: my };
    
    // Check if clicked a node
    for (const n of _graphNodes) {
        const dx = wx - n.x;
        const dy = wy - n.y;
        if (dx*dx + dy*dy < 400) {
            _draggedNode = n;
            return;
        }
    }
    _isDraggingGraph = true;
}

function handleGraphPointerMove(e) {
    if (!_isDraggingGraph && !_draggedNode) return;
    
    const mx = e.clientX;
    const my = e.clientY;
    const dx = mx - _lastMousePos.x;
    const dy = my - _lastMousePos.y;
    _lastMousePos = { x: mx, y: my };
    
    if (_draggedNode) {
        _draggedNode.x += dx / _graphCamera.zoom;
        _draggedNode.y += dy / _graphCamera.zoom;
    } else if (_isDraggingGraph) {
        _graphCamera.x += dx;
        _graphCamera.y += dy;
    }
}

function handleGraphPointerUp(e) {
    if (_draggedNode && !e.movementX && !e.movementY && (!e.touches || e.touches.length === 0)) {
        // If not much movement, consider it a click
        closeGraphView();
        const note = LocalDB.getAll('notes').find(n => n.id === _draggedNode.id);
        if (note) openNoteEditor(note, note.notebookId);
    }
    _isDraggingGraph = false;
    _draggedNode = null;
}

function centerGraph() {
    _graphCamera = { x: 0, y: 0, zoom: 1 };
}
