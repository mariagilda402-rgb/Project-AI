import React, { useEffect, useState, useCallback } from 'react';

const MindPalaceEditor = () => {
  const [notes, setNotes] = useState([]);
  const [active, setActive] = useState(null);
  const [title, setTitle] = useState('');
  const [subject, setSubject] = useState('Geral');
  const [content, setContent] = useState('');
  const [saving, setSaving] = useState(false);

  const loadNotes = useCallback(() => {
    fetch('/api/nexus/notes')
      .then((r) => r.json())
      .then((d) => setNotes(d.notes || []))
      .catch(() => setNotes([]));
  }, []);

  useEffect(() => {
    loadNotes();
  }, [loadNotes]);

  const openNote = (n) => {
    setActive(n);
    setTitle(n.title || '');
    setSubject(n.subject || 'Geral');
    setContent(n.content || '');
    fetch('/api/nexus/active_note', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ note_id: n.id, title: n.title, subject: n.subject }),
    }).catch(() => {});
  };

  const saveNote = async () => {
    setSaving(true);
    try {
      if (active?.id) {
        await fetch(`/api/nexus/notes/${active.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, subject, content }),
        });
      } else {
        await fetch('/api/nexus/notes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title, subject, content }),
        });
      }
      await fetch('/api/nexus/active_note', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ note_id: active?.id || null, title, subject }),
      });
      loadNotes();
    } catch (_) {}
    setSaving(false);
  };

  return (
    <div className="w-full h-full flex gap-4 text-white">
      <div className="w-56 flex-shrink-0 bg-white/5 rounded-2xl border border-white/10 p-3 overflow-y-auto">
        <h3 className="text-[10px] font-black text-cyan-400 uppercase mb-2">Notas</h3>
        <button
          type="button"
          onClick={() => {
            setActive(null);
            setTitle('Nova nota');
            setSubject('Geral');
            setContent('');
          }}
          className="w-full mb-2 py-2 text-xs bg-cyan-600/30 rounded-lg"
        >
          + Nova
        </button>
        {notes.map((n) => (
          <button
            key={n.id}
            type="button"
            onClick={() => openNote(n)}
            className={`w-full text-left text-xs p-2 rounded mb-1 ${
              active?.id === n.id ? 'bg-white/15' : 'hover:bg-white/10'
            }`}
          >
            <div className="font-bold truncate">{n.title}</div>
            <div className="text-[10px] text-white/40">{n.subject}</div>
          </button>
        ))}
      </div>
      <div className="flex-1 flex flex-col bg-white/5 rounded-2xl border border-white/5 p-4 min-h-0">
        <div className="flex gap-2 mb-3">
          <input
            className="flex-1 bg-black/40 border border-white/10 rounded px-2 py-1 text-sm"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Matéria"
          />
          <input
            className="flex-[2] bg-black/40 border border-white/10 rounded px-2 py-1 text-sm"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Título"
          />
          <button
            type="button"
            onClick={saveNote}
            disabled={saving}
            className="px-4 py-1 bg-cyan-600 rounded text-xs font-bold"
          >
            {saving ? '...' : 'Salvar'}
          </button>
        </div>
        <textarea
          className="flex-1 w-full bg-black/30 border border-white/10 rounded-lg p-3 text-sm font-mono resize-none min-h-[280px]"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Markdown / texto..."
        />
      </div>
    </div>
  );
};

export default MindPalaceEditor;
