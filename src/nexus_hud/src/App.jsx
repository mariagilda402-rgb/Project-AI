import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Wallet, Trophy, BookOpen, Activity, BarChart3, Clock } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import MindPalaceEditor from './components/MindPalaceEditor';

const NexusHUD = () => {
  const [state, setState] = useState({
    visible: true,
    previewMode: true,
    lastUpdate: null,
    stats: { xp: 0, level: 1, points: 0 },
    rewards: [],
    habits: [],
    studyStats: [],
    goals: [],
    theme: 'cyan',
    activeTab: 'dashboard', // 'dashboard', 'notes', 'board'
    logs: []
  });

  const themes = {
    cyan: { primary: 'cyan-500', glow: 'rgba(6,182,212,0.5)', text: 'cyan-400' },
    red: { primary: 'red-500', glow: 'rgba(239,68,68,0.5)', text: 'red-400' },
    purple: { primary: 'purple-500', glow: 'rgba(168,85,247,0.5)', text: 'purple-400' },
    emerald: { primary: 'emerald-500', glow: 'rgba(16,185,129,0.5)', text: 'emerald-400' }
  };

  const currentTheme = themes[state.theme] || themes.cyan;

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'nexus_update') {
        const payload = data.payload;
        if (payload.type === 'nexus_sync') {
          setState(prev => ({ 
            ...prev, 
            stats: payload.stats, 
            rewards: payload.rewards,
            habits: payload.habits,
            studyStats: payload.study_stats || [],
            goals: payload.goals || [],
            lastUpdate: Date.now() 
          }));
        } else if (payload.type === 'log') {
           setState(prev => ({
             ...prev,
             logs: [payload.message, ...prev.logs].slice(0, 10)
           }));
        } else if (payload.type === 'theme_change') {
            setState(prev => ({ ...prev, theme: payload.theme }));
        } else if (payload.type === 'tab_change') {
            setState(prev => ({ ...prev, activeTab: payload.tab }));
        }
      }
    };
    return () => ws.close();
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none flex items-center justify-center font-sans text-white">
      <AnimatePresence>
        {state.visible && (
          <motion.div 
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className={`w-[950px] h-[650px] bg-black/70 border border-${currentTheme.primary}/30 rounded-3xl p-10 relative overflow-hidden pointer-events-auto shadow-[0_0_80px_rgba(0,0,0,0.5)] backdrop-blur-xl`}
            style={{ boxShadow: `0 0 80px ${currentTheme.glow}` }}
          >
            {/* Header */}
            <div className="flex justify-between items-start mb-12">
              <div>
                <motion.h1 layout className={`text-5xl font-black tracking-tighter text-${currentTheme.text}`}>
                  JARVIS <span className="text-white/40 font-light">NEXUS</span>
                </motion.h1>
                <div className="flex items-center gap-2 mt-2">
                    <div className={`w-2 h-2 rounded-full bg-${currentTheme.primary} animate-pulse`} />
                    <div className="flex gap-4 ml-6">
                        {['dashboard', 'notes', 'board'].map(tab => (
                            <button 
                                key={tab}
                                onClick={() => setState(prev => ({ ...prev, activeTab: tab }))}
                                className={`text-[10px] uppercase tracking-[0.2em] font-bold transition-all ${state.activeTab === tab ? `text-${currentTheme.text} border-b border-${currentTheme.primary}` : 'text-white/20 hover:text-white/40'}`}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>
                </div>
              </div>
              
              <div className="flex gap-4">
                <StatCard icon={<Trophy className="text-yellow-400 w-5 h-5" />} label="XP DISPONÍVEL" value={`${state.stats.points}`} theme={currentTheme} />
                <StatCard icon={<Activity className={`text-${currentTheme.text} w-5 h-5`} />} label="PROGRESSÃO" value={`LVL ${state.stats.level}`} theme={currentTheme} />
              </div>
            </div>

            <div className="h-[450px]">
              {state.activeTab === 'dashboard' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid grid-cols-12 gap-8 h-full">
                  {/* Painel Esquerdo: Módulos & Hábitos */}
                  <div className="col-span-8 flex flex-col gap-6">
                    <div className="grid grid-cols-2 gap-4">
                        <ModuleCard icon={<Wallet className="w-5 h-5" />} title="Aether" subtitle="Finance" value="In Sync" color={`from-${currentTheme.primary}`} />
                        <div className="bg-white/5 border border-white/5 rounded-2xl p-4 flex flex-col justify-between">
                            <div className="flex justify-between items-start">
                                <BookOpen className={`w-5 h-5 text-${currentTheme.text}`} />
                                <span className="text-[10px] font-bold text-white/20 uppercase tracking-widest">MindPalace</span>
                            </div>
                            <div className="h-20 w-full mt-2">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={state.studyStats}>
                                        <Bar dataKey="correct_answers" fill={currentTheme.glow} radius={[2, 2, 0, 0]} />
                                        <Bar dataKey="total_questions" fill="rgba(255,255,255,0.05)" radius={[2, 2, 0, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                            <p className="text-sm font-bold text-white/90 mt-2">Estudos ENEM</p>
                        </div>
                    </div>

                    <div className="bg-white/5 rounded-2xl p-6 border border-white/5 flex-1 flex flex-col overflow-hidden">
                        <h3 className={`text-[10px] font-black text-${currentTheme.text}/50 uppercase mb-4 tracking-[0.2em]`}>Protocolos de Rotina (Chronos)</h3>
                        <div className="space-y-3 overflow-y-auto pr-2">
                            {state.habits.map((h, i) => (
                                <div key={i} className="flex justify-between items-center bg-white/5 border border-white/5 rounded-xl p-4 group hover:bg-white/10 transition-all">
                                    <div className="flex items-center gap-4">
                                        <div className={`w-10 h-10 rounded-full border border-white/10 flex items-center justify-center text-${currentTheme.text} group-hover:border-${currentTheme.primary}/50 transition-colors`}>
                                            {h.current_streak > 0 ? <Activity className="w-5 h-5" /> : <BookOpen className="w-5 h-5" />}
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold text-white/90">{h.name}</p>
                                            <p className="text-[10px] text-white/30 uppercase font-bold tracking-wider">{h.description}</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className={`text-xs font-mono font-bold text-${currentTheme.text}`}>{h.current_streak}D STREAK</p>
                                        <p className="text-[8px] text-white/20 font-bold uppercase">Recorde: {h.max_streak}D</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                  </div>

                  {/* Painel Direito: Metas & Log */}
                  <div className="col-span-4 flex flex-col gap-6">
                    <div className="bg-black/40 border border-white/10 rounded-2xl p-6 h-[180px] overflow-hidden flex flex-col">
                        <h3 className={`text-[10px] font-black text-${currentTheme.text}/50 uppercase mb-4 tracking-[0.2em]`}>Grand Objectives</h3>
                        <div className="space-y-4 overflow-y-auto pr-2">
                            {state.goals.map((g, i) => (
                                <div key={i}>
                                    <div className="flex justify-between text-[10px] font-bold mb-1">
                                        <span className="text-white/70">{g.name}</span>
                                        <span className={`text-${currentTheme.text}`}>{g.progress}%</span>
                                    </div>
                                    <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                        <motion.div 
                                            initial={{ width: 0 }}
                                            animate={{ width: `${g.progress}%` }}
                                            className={`h-full bg-${currentTheme.primary} shadow-[0_0_10px_${currentTheme.glow}]`}
                                        />
                                    </div>
                                </div>
                            ))}
                            {state.goals.length === 0 && <p className="text-white/20 text-[10px] italic">Sem metas ativas, Sir...</p>}
                        </div>
                    </div>

                    <div className="bg-black/40 border border-white/10 rounded-2xl p-6 flex-1 font-mono text-[9px] flex flex-col relative overflow-hidden">
                        <div className={`absolute top-0 left-0 w-full h-1 bg-${currentTheme.primary}/20`} />
                        <h3 className="text-white/30 uppercase mb-3 font-bold tracking-widest">System Log</h3>
                        <div className={`flex-1 space-y-1 text-${currentTheme.text}/70 overflow-y-auto`}>
                            {state.logs.map((log, i) => (
                                <div key={i} className="animate-in fade-in slide-in-from-left-2">
                                    <span className="text-white/20">[{new Date().toLocaleTimeString()}]</span> {log}
                                </div>
                            ))}
                            <div className="animate-pulse">_ IDENT_CMD: SYNC_READY</div>
                        </div>
                    </div>
                  </div>
                </motion.div>
              )}

              {state.activeTab === 'board' && (
                <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="h-full flex gap-6 overflow-x-auto pb-4">
                   {['To Do', 'In Progress', 'Done'].map(status => (
                       <div key={status} className="w-80 flex-shrink-0 flex flex-col gap-4">
                           <div className="flex justify-between items-center px-2">
                               <h3 className="text-xs font-black uppercase tracking-widest text-white/40">{status}</h3>
                               <span className="text-[10px] font-mono text-cyan-500/50">02</span>
                           </div>
                           <div className="flex-1 bg-white/[0.02] border border-white/5 rounded-2xl p-4 space-y-4 overflow-y-auto">
                               {state.goals.filter(g => {
                                   if (status === 'To Do') return g.progress === 0;
                                   if (status === 'In Progress') return g.progress > 0 && g.progress < 100;
                                   return g.progress === 100;
                               }).map((goal, idx) => (
                                   <div key={idx} className="bg-white/5 border border-white/10 rounded-xl p-4 group hover:border-cyan-500/30 transition-all">
                                       <p className="text-sm font-bold text-white/90">{goal.name}</p>
                                       <div className="flex justify-between items-center mt-3">
                                           <div className="h-1 w-24 bg-white/5 rounded-full overflow-hidden">
                                               <div className="h-full bg-cyan-500" style={{ width: `${goal.progress}%` }} />
                                           </div>
                                           <span className="text-[10px] font-mono text-cyan-400">{goal.progress}%</span>
                                       </div>
                                   </div>
                               ))}
                           </div>
                       </div>
                   ))}
                </motion.div>
              )}

              {state.activeTab === 'notes' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full">
                    <MindPalaceEditor />
                </motion.div>
              )}
            </div>

            {/* Background Scanner Overlay */}
            <div className={`absolute inset-0 pointer-events-none opacity-20 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-${currentTheme.primary}/10 via-transparent to-transparent`} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const StatCard = ({ icon, label, value, theme }) => (
  <div className={`bg-white/5 border border-white/10 rounded-2xl p-4 flex items-center gap-4 min-w-[120px]`}>
    <div className={`w-10 h-10 rounded-xl bg-${theme.primary}/10 flex items-center justify-center`}>
      {icon}
    </div>
    <div>
      <p className="text-[8px] font-black text-white/20 uppercase tracking-widest">{label}</p>
      <p className={`text-lg font-black text-${theme.text} tabular-nums`}>{value}</p>
    </div>
  </div>
);

const ModuleCard = ({ icon, title, subtitle, value, color }) => (
  <div className="bg-white/5 border border-white/5 rounded-2xl p-6 flex flex-col justify-between group hover:bg-white/10 transition-all cursor-pointer">
    <div className="flex justify-between items-start">
      <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${color} to-transparent opacity-20 flex items-center justify-center text-white`}>
        {icon}
      </div>
      <div className="text-right">
        <p className="text-[10px] font-bold text-white/30 uppercase tracking-widest">{title}</p>
        <p className="text-xs font-bold text-white/90">{value}</p>
      </div>
    </div>
    <div className="mt-4">
      <p className="text-[9px] text-white/20 font-bold uppercase tracking-tighter">{subtitle}</p>
      <div className="h-1 w-full bg-white/5 rounded-full mt-1 overflow-hidden">
        <div className={`h-full bg-gradient-to-r ${color} to-transparent w-2/3`} />
      </div>
    </div>
  </div>
);

export default NexusHUD;
