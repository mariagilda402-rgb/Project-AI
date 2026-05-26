import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Wallet, Trophy, BookOpen, Activity, BarChart3, Clock } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import MindPalaceEditor from './components/MindPalaceEditor';
import FinanceTab from './components/FinanceTab';

/** Tailwind JIT só vê classes literais no código — nunca use `text-${x}`. */
const THEME_UI = {
  cyan: {
    glow: 'rgba(6,182,212,0.5)',
    shellBorder: 'border-cyan-500/30',
    title: 'text-cyan-400',
    pulseDot: 'bg-cyan-500',
    tabActive: 'text-cyan-400 border-b border-cyan-500',
    statIconBg: 'bg-cyan-500/10',
    statIconText: 'text-cyan-400',
    statValue: 'text-cyan-400',
    moduleGradient: 'from-cyan-500',
    sectionMuted: 'text-cyan-400/50',
    habitAccent: 'text-cyan-400',
    habitHoverRing: 'group-hover:border-cyan-500/50',
    streak: 'text-cyan-400',
    goalPct: 'text-cyan-400',
    goalBar: 'bg-cyan-500',
    logText: 'text-cyan-400/70',
    logTopBar: 'bg-cyan-500/20',
    progressFill: 'bg-cyan-500',
  },
  red: {
    glow: 'rgba(239,68,68,0.5)',
    shellBorder: 'border-red-500/30',
    title: 'text-red-400',
    pulseDot: 'bg-red-500',
    tabActive: 'text-red-400 border-b border-red-500',
    statIconBg: 'bg-red-500/10',
    statIconText: 'text-red-400',
    statValue: 'text-red-400',
    moduleGradient: 'from-red-500',
    sectionMuted: 'text-red-400/50',
    habitAccent: 'text-red-400',
    habitHoverRing: 'group-hover:border-red-500/50',
    streak: 'text-red-400',
    goalPct: 'text-red-400',
    goalBar: 'bg-red-500',
    logText: 'text-red-400/70',
    logTopBar: 'bg-red-500/20',
    progressFill: 'bg-red-500',
  },
  purple: {
    glow: 'rgba(168,85,247,0.5)',
    shellBorder: 'border-purple-500/30',
    title: 'text-purple-400',
    pulseDot: 'bg-purple-500',
    tabActive: 'text-purple-400 border-b border-purple-500',
    statIconBg: 'bg-purple-500/10',
    statIconText: 'text-purple-400',
    statValue: 'text-purple-400',
    moduleGradient: 'from-purple-500',
    sectionMuted: 'text-purple-400/50',
    habitAccent: 'text-purple-400',
    habitHoverRing: 'group-hover:border-purple-500/50',
    streak: 'text-purple-400',
    goalPct: 'text-purple-400',
    goalBar: 'bg-purple-500',
    logText: 'text-purple-400/70',
    logTopBar: 'bg-purple-500/20',
    progressFill: 'bg-purple-500',
  },
  emerald: {
    glow: 'rgba(16,185,129,0.5)',
    shellBorder: 'border-emerald-500/30',
    title: 'text-emerald-400',
    pulseDot: 'bg-emerald-500',
    tabActive: 'text-emerald-400 border-b border-emerald-500',
    statIconBg: 'bg-emerald-500/10',
    statIconText: 'text-emerald-400',
    statValue: 'text-emerald-400',
    moduleGradient: 'from-emerald-500',
    sectionMuted: 'text-emerald-400/50',
    habitAccent: 'text-emerald-400',
    habitHoverRing: 'group-hover:border-emerald-500/50',
    streak: 'text-emerald-400',
    goalPct: 'text-emerald-400',
    goalBar: 'bg-emerald-500',
    logText: 'text-emerald-400/70',
    logTopBar: 'bg-emerald-500/20',
    progressFill: 'bg-emerald-500',
  },
};

function StudyFlashTab() {
  const [cards, setCards] = useState([]);
  useEffect(() => {
    fetch('/api/nexus/flashcards/due?limit=20')
      .then((r) => r.json())
      .then((d) => setCards(d.cards || []))
      .catch(() => setCards([]));
  }, []);
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full min-h-0 overflow-y-auto space-y-3 text-sm text-white/90"
    >
      <h3 className="text-xs font-black uppercase text-cyan-400">Flashcards devidos (SRS)</h3>
      {cards.length === 0 && <p className="text-white/30 text-xs">Nenhum card pendente.</p>}
      {cards.map((c) => (
        <div key={c.id} className="bg-white/5 border border-white/10 rounded-lg p-3">
          <div className="text-white/90 font-bold text-xs mb-1">{c.front}</div>
          <div className="text-white/50 text-[11px] mb-2">{c.back}</div>
          <div className="flex gap-1 flex-wrap">
            {[0,1,2,3,4,5].map((q) => (
              <button
                key={q}
                type="button"
                className="px-2 py-0.5 bg-cyan-900/40 rounded text-[10px]"
                onClick={() => {
                  fetch('/api/nexus/flashcards/review', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ card_id: c.id, quality: q }),
                  }).then(() => {
                    setCards((prev) => prev.filter((x) => x.id !== c.id));
                  });
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      ))}
    </motion.div>
  );
}

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
    activeTab: 'dashboard',
    logs: [],
    financeSnapshot: null,
    globalStreak: 0,
    tasks: [],
    financeYear: new Date().getFullYear(),
    financeMonth: new Date().getMonth() + 1,
  });

  const currentTheme = THEME_UI[state.theme] || THEME_UI.cyan;

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ws`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'nexus_update') {
        const payload = data.payload;
        if (payload.type === 'nexus_sync') {
          setState(prev => ({
            ...prev,
            stats: payload.stats || prev.stats,
            rewards: payload.rewards || [],
            habits: payload.habits || [],
            studyStats: payload.study_stats || [],
            goals: payload.goals || [],
            financeSnapshot: payload.finance_snapshot ?? prev.financeSnapshot,
            globalStreak: payload.global_streak ?? prev.globalStreak,
            tasks: payload.tasks || prev.tasks,
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

  useEffect(() => {
    const y = state.financeYear;
    const m = state.financeMonth;
    fetch(`/api/nexus/finance?year=${y}&month=${m}`)
      .then((r) => r.json())
      .then((data) => {
        setState((prev) => ({ ...prev, financeSnapshot: data }));
      })
      .catch(() => {});
  }, [state.financeYear, state.financeMonth, state.lastUpdate]);

  const fin = state.financeSnapshot?.monthly;
  const aetherLabel = fin ? `R$ ${(fin.net || 0).toFixed(0)} net` : '—';

  const bumpMonth = (delta) => {
    setState((prev) => {
      let m = prev.financeMonth + delta;
      let y = prev.financeYear;
      while (m > 12) {
        m -= 12;
        y += 1;
      }
      while (m < 1) {
        m += 12;
        y -= 1;
      }
      return { ...prev, financeMonth: m, financeYear: y };
    });
  };

  return (
    <div className="fixed inset-0 pointer-events-none flex items-center justify-center font-sans text-white">
      <AnimatePresence>
        {state.visible && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className={`pointer-events-auto relative flex h-[650px] w-[950px] flex-col overflow-hidden rounded-3xl border bg-black/80 p-10 shadow-[0_0_80px_rgba(0,0,0,0.5)] backdrop-blur-xl ${currentTheme.shellBorder}`}
            style={{ boxShadow: `0 0 80px ${currentTheme.glow}` }}
          >
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 z-0 opacity-[0.14]"
              style={{
                background: `radial-gradient(circle at 50% 20%, ${currentTheme.glow} 0%, transparent 55%)`,
              }}
            />
            <div className="relative z-10 flex min-h-0 flex-1 flex-col">
            {/* Header */}
            <div className="mb-8 flex flex-shrink-0 justify-between items-start">
              <div>
                <motion.h1 layout className={`text-5xl font-black tracking-tighter ${currentTheme.title}`}>
                  JARVIS <span className="text-white/40 font-light">NEXUS</span>
                </motion.h1>
                <div className="flex items-center gap-2 mt-2">
                    <div className={`h-2 w-2 animate-pulse rounded-full ${currentTheme.pulseDot}`} />
                    <div className="ml-6 flex gap-4">
                        {['dashboard', 'notes', 'board', 'finance', 'study', 'progress'].map(tab => (
                            <button
                                key={tab}
                                type="button"
                                onClick={() => setState(prev => ({ ...prev, activeTab: tab }))}
                                className={`border-b border-transparent pb-0.5 text-[10px] font-bold uppercase tracking-[0.2em] transition-all ${state.activeTab === tab ? currentTheme.tabActive : 'text-white/25 hover:text-white/45'}`}
                            >
                                {tab}
                            </button>
                        ))}
                    </div>
                </div>
              </div>

              <div className="flex gap-4">
                <StatCard icon={<Trophy className="h-5 w-5 text-yellow-400" />} label="XP DISPONÍVEL" value={`${state.stats.points}`} t={currentTheme} />
                <StatCard icon={<Activity className={`h-5 w-5 ${currentTheme.statIconText}`} />} label="PROGRESSÃO" value={`LVL ${state.stats.level}`} t={currentTheme} />
              </div>
            </div>

            <div className="flex min-h-0 flex-1 flex-col">
              {state.activeTab === 'dashboard' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid h-full min-h-0 grid-cols-12 gap-8">
                  <div className="col-span-8 flex flex-col gap-6">
                    <div className="text-[10px] text-white/50">
                      Streak global (todos hábitos no dia):{' '}
                      <span className="text-cyan-300 font-mono font-bold">{state.globalStreak}d</span>
                      {state.tasks?.length > 0 && (
                        <span className="ml-4">Tarefas abertas: {state.tasks.length}</span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <ModuleCard icon={<Wallet className="w-5 h-5" />} title="Aether" subtitle="Finance" value={aetherLabel} gradientFrom={currentTheme.moduleGradient} />
                        <div className="bg-white/5 border border-white/5 rounded-2xl p-4 flex flex-col justify-between">
                            <div className="flex justify-between items-start">
                                <BookOpen className={`w-5 h-5 ${currentTheme.statIconText}`} />
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
                        <h3 className={`text-[10px] font-black uppercase mb-4 tracking-[0.2em] ${currentTheme.sectionMuted}`}>Protocolos de Rotina (Chronos)</h3>
                        <div className="space-y-3 overflow-y-auto pr-2">
                            {/* Cartões hábito: gradiente/sombra inspirados em daily-habit-tracker (MIT) github.com/IhorAntiukhov/daily-habit-tracker */}
                            {state.habits.length === 0 && (
                              <p className="text-center text-[11px] text-white/35">Sem hábitos na BD — usa o agente ou a API Nexus para criar.</p>
                            )}
                            {state.habits.map((h, i) => (
                                <div key={i} className="group flex justify-between items-center rounded-xl border border-white/10 bg-gradient-to-br from-slate-800/85 to-slate-950/90 px-4 py-4 shadow-lg shadow-black/30 transition hover:border-cyan-500/25 hover:from-slate-800 hover:to-slate-900/95">
                                    <div className="flex items-center gap-4">
                                        <div className={`flex h-10 w-10 items-center justify-center rounded-full border border-white/10 transition-colors ${currentTheme.habitAccent} ${currentTheme.habitHoverRing}`}>
                                            {h.current_streak > 0 ? <Activity className="w-5 h-5" /> : <BookOpen className="w-5 h-5" />}
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold text-white/90">{h.name}</p>
                                            <p className="text-[10px] text-white/30 uppercase font-bold tracking-wider">{h.description}</p>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <p className={`text-xs font-mono font-bold ${currentTheme.streak}`}>{h.current_streak}D STREAK</p>
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
                        <h3 className={`text-[10px] font-black uppercase mb-4 tracking-[0.2em] ${currentTheme.sectionMuted}`}>Grand Objectives</h3>
                        <div className="space-y-4 overflow-y-auto pr-2">
                            {state.goals.map((g, i) => (
                                <div key={i}>
                                    <div className="flex justify-between text-[10px] font-bold mb-1">
                                        <span className="text-white/70">{g.name}</span>
                                        <span className={currentTheme.goalPct}>{g.progress}%</span>
                                    </div>
                                    <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
                                        <motion.div
                                            initial={{ width: 0 }}
                                            animate={{ width: `${g.progress}%` }}
                                            className={`h-full ${currentTheme.progressFill}`}
                                            style={{ boxShadow: `0 0 10px ${currentTheme.glow}` }}
                                        />
                                    </div>
                                </div>
                            ))}
                            {state.goals.length === 0 && <p className="text-white/20 text-[10px] italic">Sem metas ativas, Sir...</p>}
                        </div>
                    </div>

                    <div className="bg-black/40 border border-white/10 rounded-2xl p-6 flex-1 font-mono text-[9px] flex flex-col relative overflow-hidden">
                        <div className={`absolute top-0 left-0 w-full h-1 ${currentTheme.logTopBar}`} />
                        <h3 className="text-white/30 uppercase mb-3 font-bold tracking-widest">System Log</h3>
                        <div className={`flex-1 space-y-1 overflow-y-auto ${currentTheme.logText}`}>
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
                <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="flex h-full min-h-0 gap-6 overflow-x-auto pb-4">
                   {['To Do', 'In Progress', 'Done'].map(status => (
                       <div key={status} className="w-80 flex-shrink-0 flex flex-col gap-4">
                           <div className="flex justify-between items-center px-2">
                               <h3 className="text-xs font-black uppercase tracking-widest text-white/40">{status}</h3>
                               <span className="text-[10px] font-mono text-cyan-500/50">02</span>
                           </div>
                           <div className="flex-1 space-y-4 overflow-y-auto rounded-2xl border border-white/5 bg-white/[0.02] p-4">
                               {(() => {
                                 const col = state.goals.filter((g) => {
                                   if (status === 'To Do') return g.progress === 0;
                                   if (status === 'In Progress') return g.progress > 0 && g.progress < 100;
                                   return g.progress === 100;
                                 });
                                 if (col.length === 0) {
                                   return (
                                     <p className="text-[11px] leading-relaxed text-white/30">
                                       Sem metas nesta coluna. O board usa as metas (goals) do Nexus.
                                     </p>
                                   );
                                 }
                                 return col.map((goal, idx) => (
                                   <div key={idx} className="rounded-xl border border-white/10 bg-white/5 p-4 transition-all hover:border-cyan-500/30">
                                       <p className="text-sm font-bold text-white/90">{goal.name}</p>
                                       <div className="mt-3 flex items-center justify-between">
                                           <div className="h-1 w-24 overflow-hidden rounded-full bg-white/5">
                                               <div className="h-full bg-cyan-500" style={{ width: `${goal.progress}%` }} />
                                           </div>
                                           <span className="font-mono text-[10px] text-cyan-400">{goal.progress}%</span>
                                       </div>
                                   </div>
                                 ));
                               })()}
                           </div>
                       </div>
                   ))}
                </motion.div>
              )}

              {state.activeTab === 'notes' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full min-h-0">
                    <MindPalaceEditor />
                </motion.div>
              )}

              {state.activeTab === 'finance' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full min-h-0">
                  <FinanceTab
                    year={state.financeYear}
                    month={state.financeMonth}
                    snapshot={state.financeSnapshot}
                    onMonthDelta={bumpMonth}
                    onRefresh={() => setState((prev) => ({ ...prev, lastUpdate: Date.now() }))}
                  />
                </motion.div>
              )}

              {state.activeTab === 'study' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="h-full min-h-0">
                  <StudyFlashTab />
                </motion.div>
              )}

              {state.activeTab === 'progress' && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex h-full min-h-0 flex-col gap-4">
                  <h3 className="text-xs font-black uppercase text-white/40">Desempenho por área</h3>
                  {(!state.studyStats || state.studyStats.length === 0) && (
                    <p className="text-[11px] text-white/35">
                      Sem estatísticas ainda. Responde a questões ENEM (simulado / quiz) para preencher este gráfico.
                    </p>
                  )}
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={state.studyStats}>
                        <XAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                        <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                        <Tooltip />
                        <Bar dataKey="correct_answers" fill="rgba(34,211,238,0.8)" name="Acertos" />
                        <Bar dataKey="total_questions" fill="rgba(255,255,255,0.08)" name="Total" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="text-[10px] text-white/40">Simulados: use o assistente com nexus_command quiz_random ou abra a API /api/nexus/quiz/sample</p>
                </motion.div>
              )}
            </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const StatCard = ({ icon, label, value, t }) => (
  <div className="flex min-w-[120px] items-center gap-4 rounded-2xl border border-white/10 bg-white/5 p-4">
    <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${t.statIconBg}`}>
      {icon}
    </div>
    <div>
      <p className="text-[8px] font-black uppercase tracking-widest text-white/20">{label}</p>
      <p className={`text-lg font-black tabular-nums ${t.statValue}`}>{value}</p>
    </div>
  </div>
);

const ModuleCard = ({ icon, title, subtitle, value, gradientFrom }) => (
  <div className="group cursor-pointer rounded-2xl border border-white/5 bg-white/5 p-6 transition-all hover:bg-white/10">
    <div className="flex justify-between items-start">
      <div className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${gradientFrom} to-transparent text-white opacity-20`}>
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
        <div className={`h-full w-2/3 bg-gradient-to-r ${gradientFrom} to-transparent`} />
      </div>
    </div>
  </div>
);

export default NexusHUD;
