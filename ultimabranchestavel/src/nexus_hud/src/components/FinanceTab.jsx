/**
 * UI de finanças inspirada em padrões do projeto MIT
 * https://github.com/ymykhal/expense-tracker-demo-app (cartões-resumo, linha transação em colunas).
 * Gráfico por categoria no espírito do dashboard desse demo (Chart.js lá → Recharts aqui).
 */
import React, { useMemo, useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ChevronLeft,
  ChevronRight,
  Wallet,
  TrendingDown,
  TrendingUp,
  Scale,
  AlertTriangle,
  Plus,
  Loader2,
  PieChart,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

const brl = (n) =>
  new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(n) || 0);

const monthTitle = (y, m) => {
  try {
    return new Intl.DateTimeFormat('pt-BR', { month: 'long', year: 'numeric' }).format(
      new Date(y, m - 1, 1)
    );
  } catch {
    return `${y}-${String(m).padStart(2, '0')}`;
  }
};

function groupByDay(transactions) {
  const map = new Map();
  for (const tx of transactions || []) {
    const raw = tx.occurred_at || (tx.created_at || '').slice(0, 10) || '—';
    const day = typeof raw === 'string' ? raw.slice(0, 10) : '—';
    if (!map.has(day)) map.set(day, []);
    map.get(day).push(tx);
  }
  const keys = [...map.keys()].sort((a, b) => b.localeCompare(a));
  return keys.map((k) => ({ day: k, items: map.get(k) }));
}

function formatTxDate(iso) {
  if (!iso || typeof iso !== 'string') return '—';
  const d = iso.slice(0, 10);
  try {
    return new Intl.DateTimeFormat('pt-BR', { day: 'numeric', month: 'short' }).format(new Date(d));
  } catch {
    return d;
  }
}

function SummaryStatCard({ title, value, icon: Icon, variant, valueClassName }) {
  const styles = {
    balance: 'from-sky-950/80 to-slate-950/90 border-sky-500/20 text-sky-300',
    income: 'from-emerald-950/70 to-slate-950/90 border-emerald-500/20 text-emerald-300',
    expense: 'from-rose-950/70 to-slate-950/90 border-rose-500/20 text-rose-300',
  };
  const iconBg = {
    balance: 'bg-sky-500/20 text-sky-200',
    income: 'bg-emerald-500/20 text-emerald-200',
    expense: 'bg-rose-500/20 text-rose-200',
  };
  return (
    <div
      className={`rounded-2xl border bg-gradient-to-br p-4 shadow-lg shadow-black/25 ${styles[variant]}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl ${iconBg[variant]}`}
        >
          <Icon className="h-5 w-5" strokeWidth={1.75} />
        </div>
      </div>
      <p className="mt-3 text-[10px] font-bold uppercase tracking-[0.2em] text-white/40">{title}</p>
      <p
        className={`mt-1 font-mono text-xl font-bold tabular-nums tracking-tight ${valueClassName || 'text-white/95'}`}
      >
        {value}
      </p>
    </div>
  );
}

function defaultOccurredAt(y, m) {
  const now = new Date();
  const cy = now.getFullYear();
  const cm = now.getMonth() + 1;
  const cd = now.getDate();
  const pad = (n) => String(n).padStart(2, '0');
  if (y < cy || (y === cy && m < cm)) {
    const last = new Date(y, m, 0).getDate();
    return `${y}-${pad(m)}-${pad(last)}`;
  }
  if (y > cy || (y === cy && m > cm)) {
    return `${y}-${pad(m)}-01`;
  }
  return `${y}-${pad(m)}-${pad(cd)}`;
}

export default function FinanceTab({ year, month, snapshot, onMonthDelta, onRefresh }) {
  const fin = snapshot?.monthly;
  const debt = Number(snapshot?.total_marked_debt || 0);
  const groups = useMemo(() => groupByDay(snapshot?.transactions), [snapshot?.transactions]);

  const [amount, setAmount] = useState('');
  const [type, setType] = useState('expense');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('Geral');
  const [markDebt, setMarkDebt] = useState(false);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState(null);

  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(null), 2800);
    return () => clearTimeout(t);
  }, [toast]);

  const net = Number(fin?.net || 0);
  const income = Number(fin?.income || 0);
  const expense = Number(fin?.expense || 0);
  const expenseShare = income + expense > 0 ? Math.min(100, (expense / (income + expense)) * 100) : 50;

  const expenseByCategory = useMemo(() => {
    const m = {};
    for (const tx of snapshot?.transactions || []) {
      if (tx.type !== 'expense') continue;
      const c = (tx.category || 'Outros').trim() || 'Outros';
      m[c] = (m[c] || 0) + Number(tx.amount);
    }
    return Object.entries(m)
      .map(([name, value]) => ({ name: name.length > 14 ? `${name.slice(0, 14)}…` : name, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [snapshot?.transactions]);

  const chartColors = ['#22d3ee', '#a78bfa', '#fb923c', '#fb7185', '#34d399', '#fbbf24', '#94a3b8', '#f472b6'];

  const submit = async (e) => {
    e.preventDefault();
    const raw = amount.replace(',', '.').trim();
    const amt = parseFloat(raw);
    if (!raw || Number.isNaN(amt) || amt <= 0) {
      setToast({ kind: 'err', text: 'Indica um valor válido.' });
      return;
    }
    setBusy(true);
    setToast(null);
    const od = defaultOccurredAt(year, month);
    try {
      const r = await fetch('/api/nexus/finance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'finance_add',
          type,
          amount: amt,
          category: category.trim() || 'Geral',
          description: description.trim() || 'Registo rápido',
          occurred_at: od,
          is_debt: type === 'expense' && markDebt ? 1 : 0,
          necessity: 5,
        }),
      });
      const j = await r.json().catch(() => ({}));
      if (!r.ok || j.ok === false) throw new Error(j.message || 'Falha ao gravar');
      setAmount('');
      setDescription('');
      setMarkDebt(false);
      setToast({ kind: 'ok', text: 'Movimento registado.' });
      onRefresh?.();
    } catch (err) {
      setToast({ kind: 'err', text: String(err.message || err) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex h-full flex-col gap-4 overflow-hidden text-[13px] leading-snug">
      <div className="flex flex-shrink-0 items-center justify-between gap-3 rounded-xl border border-white/[0.08] bg-gradient-to-r from-slate-900/90 to-slate-950/95 px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-cyan-500/15 ring-1 ring-cyan-400/20">
            <Wallet className="h-5 w-5 text-cyan-300" strokeWidth={1.75} />
          </div>
          <div className="min-w-0">
            <p className="text-[9px] font-semibold uppercase tracking-[0.2em] text-white/35">Aether</p>
            <h2 className="truncate text-base font-bold capitalize text-white/95">{monthTitle(year, month)}</h2>
          </div>
        </div>
        <div className="flex items-center gap-0.5 rounded-lg border border-white/10 bg-black/35 p-0.5">
          <button
            type="button"
            onClick={() => onMonthDelta(-1)}
            className="rounded-md p-2 text-white/45 transition hover:bg-white/10 hover:text-white"
            aria-label="Mês anterior"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <button
            type="button"
            onClick={() => onMonthDelta(1)}
            className="rounded-md p-2 text-white/45 transition hover:bg-white/10 hover:text-white"
            aria-label="Mês seguinte"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </div>

      <div className="grid flex-shrink-0 grid-cols-3 gap-2 sm:gap-3">
        <SummaryStatCard
          title="Saldo"
          value={brl(net)}
          icon={Scale}
          variant="balance"
          valueClassName={net >= 0 ? 'text-emerald-400' : 'text-rose-400'}
        />
        <SummaryStatCard title="Receitas" value={brl(income)} icon={TrendingUp} variant="income" />
        <SummaryStatCard title="Gastos" value={brl(expense)} icon={TrendingDown} variant="expense" />
      </div>

      <div className="flex-shrink-0">
        <div className="mb-1 flex justify-between text-[10px] text-white/35">
          <span>Partilha de volume (gastos / receitas + gastos)</span>
          <span>{income + expense > 0 ? `${expenseShare.toFixed(0)}%` : '—'}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-rose-500/85 to-amber-500/55"
            initial={false}
            animate={{ width: `${expenseShare}%` }}
            transition={{ type: 'spring', stiffness: 120, damping: 20 }}
          />
        </div>
      </div>

      {debt > 0 && (
        <div className="flex flex-shrink-0 items-start gap-2 rounded-xl border border-amber-500/25 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-100/90">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-400" />
          <div>
            <span className="font-semibold text-amber-200/95">Dívidas marcadas (acumulado):</span>{' '}
            <span className="font-mono text-amber-100">{brl(debt)}</span>
          </div>
        </div>
      )}

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(260px,320px)]">
        <div className="flex min-h-0 flex-col overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.03]">
          <div className="flex flex-shrink-0 items-center justify-between border-b border-white/[0.06] px-4 py-3">
            <div className="flex items-center gap-2 text-white/50">
              <PieChart className="h-4 w-4 text-violet-400/90" />
              <span className="text-[11px] font-semibold uppercase tracking-wider">Gastos por categoria</span>
            </div>
          </div>
          {expenseByCategory.length > 0 ? (
            <div className="h-36 flex-shrink-0 border-b border-white/[0.06] px-2 py-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={expenseByCategory} layout="vertical" margin={{ left: 4, right: 8, top: 4, bottom: 4 }}>
                  <XAxis type="number" hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={72}
                    tick={{ fill: 'rgba(255,255,255,0.45)', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                    contentStyle={{
                      background: 'rgba(15,23,42,0.95)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    formatter={(v) => brl(v)}
                  />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]} maxBarSize={14}>
                    {expenseByCategory.map((_, i) => (
                      <Cell key={i} fill={chartColors[i % chartColors.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="flex-shrink-0 border-b border-white/[0.06] px-4 py-3 text-[11px] text-white/30">
              Sem gastos com categoria neste mês.
            </div>
          )}
          <div className="flex flex-shrink-0 items-center justify-between border-b border-white/[0.06] px-4 py-2.5">
            <div className="flex items-center gap-2 text-white/50">
              <Scale className="h-4 w-4 text-cyan-400/80" />
              <span className="text-[11px] font-semibold uppercase tracking-wider">Movimentos</span>
            </div>
            <span className="font-mono text-[10px] text-white/30">
              {snapshot?.transactions?.length ?? 0} linhas
            </span>
          </div>
          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-3 py-3 pr-2">
            {groups.length === 0 && (
              <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
                <p className="text-sm font-medium text-white/45">Sem movimentos neste mês</p>
                <p className="max-w-xs text-[11px] text-white/30">
                  Usa o registo rápido ao lado ou diz ao assistente quanto gastaste ou recebeste.
                </p>
              </div>
            )}
            {groups.map(({ day, items }) => (
              <div key={day}>
                <p className="sticky top-0 z-[1] mb-2 bg-[#0a0a0c]/90 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-500/70 backdrop-blur-sm">
                  {day}
                </p>
                <ul className="space-y-2">
                  {items.map((tx) => {
                    const inc = tx.type === 'income';
                    const dateStr = formatTxDate(tx.occurred_at || tx.created_at);
                    return (
                      <motion.li
                        layout
                        key={tx.id}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-2 rounded-xl border border-white/[0.06] bg-black/25 px-3 py-2.5 transition hover:border-white/12 hover:bg-white/[0.04] sm:gap-4"
                      >
                        <div className="min-w-0">
                          <p className="truncate font-medium text-white/88">
                            {tx.description || tx.category || '—'}
                          </p>
                          <p className="truncate text-[11px] text-white/35">
                            {tx.category}
                            {tx.is_debt ? (
                              <span className="ml-2 rounded bg-amber-500/20 px-1.5 py-0.5 text-[9px] font-bold uppercase text-amber-200/90">
                                dívida
                              </span>
                            ) : null}
                            {tx.notes ? ` · ${tx.notes}` : ''}
                          </p>
                        </div>
                        <p className="hidden text-center font-mono text-[11px] text-white/40 sm:block whitespace-nowrap">
                          {dateStr}
                        </p>
                        <span
                          className={`text-right font-mono text-sm font-semibold tabular-nums ${
                            inc ? 'text-emerald-400' : 'text-rose-300'
                          }`}
                        >
                          {inc ? '+' : '−'}
                          {brl(tx.amount)}
                        </span>
                      </motion.li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Registo rápido */}
        <div className="flex flex-col gap-3 rounded-2xl border border-cyan-500/15 bg-gradient-to-b from-cyan-950/40 to-black/40 p-4 shadow-[inset_0_1px_0_rgba(34,211,238,0.08)]">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-400/80">
            Registo rápido
          </p>
          <form onSubmit={submit} className="flex flex-1 flex-col gap-3">
            <div className="flex rounded-lg border border-white/10 bg-black/40 p-0.5">
              {[
                { id: 'expense', label: 'Gasto' },
                { id: 'income', label: 'Receita' },
              ].map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => {
                    setType(t.id);
                    if (t.id === 'income') setMarkDebt(false);
                  }}
                  className={`flex-1 rounded-md py-2 text-xs font-semibold transition ${
                    type === t.id
                      ? 'bg-cyan-500/25 text-cyan-100 shadow-sm'
                      : 'text-white/40 hover:text-white/65'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-white/35">
                Valor (R$)
              </label>
              <input
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0,00"
                inputMode="decimal"
                className="w-full rounded-lg border border-white/10 bg-black/50 px-3 py-2.5 font-mono text-base text-white outline-none ring-cyan-500/30 placeholder:text-white/25 focus:border-cyan-500/40 focus:ring-2"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-white/35">
                Descrição
              </label>
              <input
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Ex.: supermercado, freelance…"
                className="w-full rounded-lg border border-white/10 bg-black/50 px-3 py-2 text-sm text-white outline-none ring-cyan-500/30 placeholder:text-white/25 focus:border-cyan-500/40 focus:ring-2"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-white/35">
                Categoria
              </label>
              <input
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                placeholder="Geral"
                className="w-full rounded-lg border border-white/10 bg-black/50 px-3 py-2 text-sm text-white outline-none ring-cyan-500/30 placeholder:text-white/25 focus:border-cyan-500/40 focus:ring-2"
              />
            </div>
            {type === 'expense' && (
              <label className="flex cursor-pointer items-center gap-2 text-[12px] text-white/55">
                <input
                  type="checkbox"
                  checked={markDebt}
                  onChange={(e) => setMarkDebt(e.target.checked)}
                  className="rounded border-white/20 bg-black/50 text-cyan-500 focus:ring-cyan-500/40"
                />
                Marcar como dívida
              </label>
            )}
            <button
              type="submit"
              disabled={busy}
              className="mt-auto flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-cyan-500 py-3 text-sm font-bold text-slate-950 shadow-lg shadow-cyan-900/30 transition hover:from-cyan-500 hover:to-cyan-400 disabled:opacity-50"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Registar
            </button>
          </form>
          {toast && (
            <motion.p
              key={toast.text}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className={`text-center text-[11px] font-medium ${
                toast.kind === 'ok' ? 'text-emerald-400/90' : 'text-rose-400/90'
              }`}
            >
              {toast.text}
            </motion.p>
          )}
        </div>
      </div>
    </div>
  );
}
