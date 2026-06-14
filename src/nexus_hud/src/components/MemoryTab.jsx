import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Lock, Unlock, Save, Trash2, Key } from 'lucide-react';

export default function MemoryTab({ theme }) {
  const [locked, setLocked] = useState(true);
  const [passwordInput, setPasswordInput] = useState('');
  const [setupPassword, setSetupPassword] = useState('');
  const [isSetup, setIsSetup] = useState(false);
  const [memories, setMemories] = useState(null);
  const [editKey, setEditKey] = useState(null);
  const [editCategory, setEditCategory] = useState(null);
  const [editValue, setEditValue] = useState('');

  useEffect(() => {
    // Check if password exists in localStorage
    const savedPassword = localStorage.getItem('nexus_desktop_password');
    if (!savedPassword) {
      setIsSetup(true);
    }
  }, []);

  const handleSetup = async () => {
    if (setupPassword.length < 4) {
      alert("Senha muito curta");
      return;
    }
    localStorage.setItem('nexus_desktop_password', setupPassword);
    setIsSetup(false);
    if (window.pywebview && window.pywebview.api) {
        await window.pywebview.api.unlock_structured_memory(setupPassword);
    }
  };

  const handleUnlock = async () => {
    const savedPassword = localStorage.getItem('nexus_desktop_password');
    if (passwordInput === savedPassword) {
      if (window.pywebview && window.pywebview.api) {
          const success = await window.pywebview.api.unlock_structured_memory(passwordInput);
          if (!success) {
              alert("Falha ao descriptografar banco de dados (senha incorreta no backend?).");
              return;
          }
      }
      setLocked(false);
      loadMemories();
    } else {
      alert("Senha Incorreta!");
    }
  };

  const loadMemories = async () => {
    if (window.pywebview && window.pywebview.api) {
      try {
        const mems = await window.pywebview.api.get_structured_memory();
        setMemories(mems);
      } catch (err) {
        console.error("Erro ao carregar memorias", err);
        setMemories({ notes: { error: "Falha na conexão com Python" } });
      }
    } else {
      // Mock for dev
      setMemories({
        notes: { "projeto_ai": "Em andamento" },
        preferences: { "tema": "dark" }
      });
    }
  };

  const handleSave = async (category, key) => {
    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.update_structured_memory_entry(category, key, editValue);
    }
    setEditKey(null);
    loadMemories();
  };

  const handleDelete = async (category, key) => {
    if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.delete_structured_memory_entry(category, key);
    }
    loadMemories();
  };

  if (isSetup) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-white/90 font-sans">
        <Key className={`w-16 h-16 mb-6 text-white`} style={{ color: theme.glow }} />
        <h2 className="text-2xl font-bold mb-2">Definir Senha do Gerenciador</h2>
        <p className="text-white/50 mb-8 text-sm">Crie uma senha para acessar as memórias do Jarvis.</p>
        <input 
          type="password" 
          placeholder="Digite uma nova senha"
          value={setupPassword}
          onChange={(e) => setSetupPassword(e.target.value)}
          className="bg-black/50 border border-white/20 rounded-lg px-4 py-3 text-white mb-4 outline-none focus:border-white/50 w-64 text-center"
        />
        <button 
          onClick={handleSetup}
          className="px-6 py-2 rounded-lg font-bold transition-all w-64"
          style={{ background: theme.glow, border: `1px solid ${theme.glow}` }}
        >
          Salvar Senha
        </button>
      </div>
    );
  }

  if (locked) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-white/90 font-sans">
        <Lock className={`w-16 h-16 mb-6 text-white`} style={{ color: theme.glow }} />
        <h2 className="text-2xl font-bold mb-2">Acesso Restrito</h2>
        <p className="text-white/50 mb-8 text-sm">Insira sua senha para gerenciar a memória do Jarvis.</p>
        <input 
          type="password" 
          placeholder="Senha"
          value={passwordInput}
          onChange={(e) => setPasswordInput(e.target.value)}
          className="bg-black/50 border border-white/20 rounded-lg px-4 py-3 text-white mb-4 outline-none focus:border-white/50 w-64 text-center"
        />
        <button 
          onClick={handleUnlock}
          className="px-6 py-2 rounded-lg font-bold transition-all w-64 flex items-center justify-center gap-2"
          style={{ background: theme.glow, border: `1px solid ${theme.glow}` }}
        >
          <Unlock className="w-4 h-4" /> Desbloquear
        </button>
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full flex flex-col font-sans">
      <div className="flex justify-between items-center mb-6">
        <h2 className={`text-xl font-black uppercase tracking-widest`} style={{ color: theme.glow }}>Gerenciador de Memória</h2>
        <button 
          onClick={() => { setLocked(true); setPasswordInput(''); }}
          className="text-xs bg-white/10 hover:bg-white/20 px-3 py-1 rounded-md text-white/70"
        >
          Bloquear
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto pr-2 space-y-6 pb-10">
        {memories ? Object.entries(memories).map(([category, items]) => (
          <div key={category} className="bg-white/5 border border-white/10 rounded-xl p-4">
            <h3 className="text-sm font-bold text-white/60 uppercase tracking-widest mb-4 border-b border-white/10 pb-2">{category}</h3>
            {Object.keys(items).length === 0 ? (
              <p className="text-white/30 text-xs italic">Nenhuma memória nesta categoria.</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(items).map(([key, value]) => {
                  const isEditing = editKey === key && editCategory === category;
                  return (
                    <div key={key} className="flex flex-col bg-black/40 rounded-lg p-3 border border-white/5">
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-xs font-mono text-white/50 bg-white/5 px-2 py-0.5 rounded">{key}</span>
                        <div className="flex gap-2">
                          {isEditing ? (
                            <button onClick={() => handleSave(category, key)} className="text-green-400 hover:text-green-300"><Save className="w-4 h-4"/></button>
                          ) : (
                            <button onClick={() => { setEditKey(key); setEditCategory(category); setEditValue(value); }} className="text-blue-400 hover:text-blue-300 text-xs uppercase font-bold">Editar</button>
                          )}
                          <button onClick={() => handleDelete(category, key)} className="text-red-400 hover:text-red-300"><Trash2 className="w-4 h-4"/></button>
                        </div>
                      </div>
                      {isEditing ? (
                        <textarea 
                          className="w-full bg-black border border-white/20 text-white text-sm p-2 rounded-md outline-none focus:border-cyan-500"
                          rows={3}
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                        />
                      ) : (
                        <p className="text-sm text-white/90 break-words">{typeof value === 'object' ? JSON.stringify(value) : value}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )) : (
          <div className="animate-pulse text-white/50 text-sm">Carregando memórias...</div>
        )}
      </div>
    </motion.div>
  );
}
