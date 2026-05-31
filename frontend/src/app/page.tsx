"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowDownRight,
  ArrowUpRight,
  Banknote,
  Landmark,
  Repeat2,
  Target,
  Wallet,
} from "lucide-react";
import { dashboardApi, type FullDashboardSummary } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { useLanguage } from "@/lib/LanguageContext";
import type { Language, Translations } from "@/lib/translations";

const chartText = "#94a3b8";
const chartGrid = "#1f2937";
const DASHBOARD_CURRENCIES = ["USD", "ARS"] as const;
type DashboardCurrency = (typeof DASHBOARD_CURRENCIES)[number];
const DASHBOARD_CURRENCY_STORAGE_KEY = "dashboard_currency";

function initialDashboardCurrency(): DashboardCurrency {
  if (typeof window === "undefined") return "USD";
  const stored = window.localStorage.getItem(DASHBOARD_CURRENCY_STORAGE_KEY);
  return DASHBOARD_CURRENCIES.includes(stored as DashboardCurrency) ? stored as DashboardCurrency : "USD";
}

function localeFor(lang: Language) {
  return lang === "es" ? "es-AR" : "en-US";
}

function toNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined) return null;
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function isoDate(value: Date) {
  return value.toISOString().slice(0, 10);
}

function defaultRange() {
  const to = new Date();
  const from = new Date(to.getFullYear(), to.getMonth() - 5, 1);
  return { from: isoDate(from), to: isoDate(to) };
}

function formatMoney(
  value: number | string | null | undefined,
  lang: Language,
  noQuote: string,
  currency = "USD",
) {
  const numeric = toNumber(value);
  if (numeric === null) return noQuote;
  return new Intl.NumberFormat(localeFor(lang), {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(numeric);
}

function formatPct(value: number | string | null, noPreviousPeriod: string) {
  const numeric = toNumber(value);
  if (numeric === null) return noPreviousPeriod;
  return `${numeric >= 0 ? "+" : ""}${numeric.toFixed(1)}%`;
}

function formatFixed(value: number | string | null | undefined, digits: number) {
  return (toNumber(value) ?? 0).toFixed(digits);
}

function shortMonth(value: string, lang: Language) {
  const [year, month] = value.split("-").map(Number);
  return new Date(year, month - 1, 1).toLocaleDateString(localeFor(lang), {
    month: "short",
    year: "2-digit",
  });
}

export default function DashboardPage() {
  const [range] = useState(defaultRange);
  const [currency, setCurrency] = useState<DashboardCurrency>(initialDashboardCurrency);
  const [data, setData] = useState<FullDashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { user, isLoading: authLoading } = useAuth();
  const { lang, t } = useLanguage();

  useEffect(() => {
    if (authLoading || !user) return;

    let mounted = true;
    const load = async () => {
      try {
        setLoading(true);
        const summary = await dashboardApi.summary({ from: range.from, to: range.to, currency });
        if (mounted) {
          setData(summary);
          setError(null);
        }
      } catch (e: unknown) {
        if (mounted) setError(e instanceof Error ? e.message : t.dashboard.loadError);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    void load();
    return () => {
      mounted = false;
    };
  }, [authLoading, currency, range, t.dashboard.loadError, user]);

  const changeCurrency = (value: string | null) => {
    if (!DASHBOARD_CURRENCIES.includes(value as DashboardCurrency)) return;
    const nextCurrency = value as DashboardCurrency;
    setCurrency(nextCurrency);
    window.localStorage.setItem(DASHBOARD_CURRENCY_STORAGE_KEY, nextCurrency);
  };

  const monthly = useMemo(
    () => data?.monthly_flow.map((item) => ({
      ...item,
      income: toNumber(item.income) ?? 0,
      expenses: toNumber(item.expenses) ?? 0,
      net: toNumber(item.net) ?? 0,
      label: shortMonth(item.month, lang),
    })) ?? [],
    [data, lang],
  );

  if (authLoading || !user || loading) {
    return <p className="text-sm text-muted-foreground">{t.dashboard.loading}</p>;
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
        {error ?? t.dashboard.noData}
      </div>
    );
  }

  const money = (value: number | string | null | undefined, moneyCurrency = data.currency) =>
    formatMoney(value, lang, t.dashboard.noQuote, moneyCurrency);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.dashboard.title}</h1>
          <p className="text-sm text-muted-foreground">
            {t.dashboard.subtitle} {data.currency}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={data.currency} onValueChange={changeCurrency}>
            <SelectTrigger className="min-w-28 border-cyan-400/30 text-cyan-300">
              <Repeat2 size={14} />
              <span>{data.currency}</span>
            </SelectTrigger>
            <SelectContent>
              {DASHBOARD_CURRENCIES.map((item) => (
                <SelectItem key={item} value={item}>{item}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Badge variant="outline" className="border-cyan-400/30 text-cyan-300">
            {data.date_from} / {data.date_to}
          </Badge>
        </div>
      </div>

      {data.warnings.length > 0 && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          {data.warnings.join(" / ")}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard title={t.dashboard.income} icon={<ArrowUpRight size={22} />} value={data.kpis.income.value} change={data.kpis.income.change_pct} tone="green" lang={lang} t={t} currency={data.currency} />
        <KpiCard title={t.dashboard.expenses} icon={<ArrowDownRight size={22} />} value={data.kpis.expenses.value} change={data.kpis.expenses.change_pct} tone="red" lang={lang} t={t} currency={data.currency} />
        <KpiCard title={t.dashboard.netSavings} icon={<Wallet size={22} />} value={data.kpis.net_savings.value} change={data.kpis.net_savings.change_pct} tone="blue" lang={lang} t={t} currency={data.currency} />
        <KpiCard title={t.dashboard.wealth} icon={<Landmark size={22} />} value={data.kpis.wealth.value} change={data.kpis.wealth.change_pct} tone="cyan" lang={lang} t={t} currency={data.currency} />
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1.35fr_0.85fr_0.9fr]">
        <Panel title={t.dashboard.monthlyFlow} className="min-h-[270px]">
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={monthly}>
              <CartesianGrid stroke={chartGrid} vertical={false} />
              <XAxis dataKey="label" stroke={chartText} fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke={chartText} fontSize={12} tickLine={false} axisLine={false} tickFormatter={(v) => compactMoney(Number(v), lang, data.currency)} />
              <Tooltip formatter={(v) => money(Number(v))} contentStyle={{ background: "#020617", border: "1px solid #1f2937" }} />
              <Line type="monotone" dataKey="income" stroke="#22c55e" strokeWidth={2} dot={false} name={t.dashboard.income} />
              <Line type="monotone" dataKey="expenses" stroke="#ef4444" strokeWidth={2} dot={false} name={t.dashboard.expenses} />
              <Line type="monotone" dataKey="net" stroke="#38bdf8" strokeWidth={2} strokeDasharray="5 5" dot={false} name={t.dashboard.netSavings} />
            </LineChart>
          </ResponsiveContainer>
        </Panel>

        <Panel title={t.dashboard.expensesByCategory} className="min-h-[270px]">
          {data.expenses_by_category.length === 0 ? (
            <EmptyState text={t.dashboard.noExpensesInPeriod} />
          ) : (
            <div className="grid grid-cols-[140px_1fr] items-center gap-3">
              <ResponsiveContainer width="100%" height={170}>
                <PieChart>
                  <Pie data={data.expenses_by_category} dataKey="amount" nameKey="category" innerRadius={44} outerRadius={68} paddingAngle={2}>
                    {data.expenses_by_category.map((entry) => (
                      <Cell key={entry.category} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v) => money(Number(v))} contentStyle={{ background: "#020617", border: "1px solid #1f2937" }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2">
                {data.expenses_by_category.slice(0, 6).map((item) => (
                  <div key={item.category} className="grid grid-cols-[1fr_auto] gap-2 text-xs">
                    <span className="truncate" style={{ color: item.color }}>{item.category}</span>
                    <span className="text-muted-foreground">{formatFixed(item.percent, 1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Panel>

        <Panel title={t.dashboard.accountBalances} className="min-h-[270px]">
          <div className="space-y-3">
            {data.account_balances.length === 0 ? (
              <EmptyState text={t.dashboard.noAccounts} />
            ) : data.account_balances.slice(0, 6).map((account) => (
              <div key={account.account_id} className="grid grid-cols-[auto_1fr_auto] items-center gap-3 text-sm">
                <span className="rounded-md bg-emerald-500/15 p-1.5 text-emerald-300"><Banknote size={16} /></span>
                <div className="min-w-0">
                  <p className="truncate font-medium">{account.name}</p>
                  <div className="mt-1 h-1.5 rounded-full bg-white/10">
                    <div className="h-1.5 rounded-full bg-emerald-400" style={{ width: `${Math.min(Math.abs(toNumber(account.converted_balance) ?? 0) / Math.max(toNumber(data.kpis.wealth.value) ?? 1, 1) * 100, 100)}%` }} />
                  </div>
                </div>
                <span className="font-mono text-xs">{money(account.converted_balance)}</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1.1fr_0.95fr_1.05fr]">
        <Panel title={t.dashboard.installmentsDue}>
          <TableLike rows={data.upcoming_installments.slice(0, 5).map((item) => [
            `${item.description} (${item.current_installment}/${item.total_installments})`,
            item.due_date,
            money(item.converted_amount),
          ])} empty={t.dashboard.noInstallments} />
        </Panel>

        <Panel title={t.dashboard.investmentPerformance}>
          <div className="mb-3 h-16">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.investments.map((item) => ({ name: item.name, value: toNumber(item.converted_current_value) ?? toNumber(item.current_value) ?? 0 }))}>
                <Area type="monotone" dataKey="value" stroke="#22c55e" fill="#22c55e22" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <TableLike rows={data.investments.slice(0, 5).map((item) => [
            item.name,
            money(item.converted_current_value),
            `${formatFixed(item.return_pct, 1)}%`,
          ])} empty={t.dashboard.noInvestments} />
        </Panel>

        <Panel title={t.dashboard.recentMovements}>
          <TableLike rows={data.recent_movements.slice(0, 7).map((item) => [
            item.description,
            item.category ?? "-",
            `${item.type === "income" ? "+" : "-"}${money(item.converted_amount)}`,
          ])} empty={t.dashboard.noMovements} />
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[1fr_1.1fr]">
        <Panel title={t.dashboard.budgetVsActual}>
          {data.budgets.length === 0 ? (
            <EmptyState text={t.dashboard.noBudgets} />
          ) : (
            <div className="space-y-3">
              {data.budgets.slice(0, 5).map((budget) => (
                <ProgressRow
                  key={budget.budget_id}
                  label={budget.category}
                  value={`${money(budget.actual_amount)} / ${money(budget.budget_amount)}`}
                  percent={budget.percent_used}
                  color={budget.color}
                />
              ))}
            </div>
          )}
        </Panel>

        <Panel title={t.dashboard.savingGoals}>
          <div className="grid gap-3 md:grid-cols-2">
            {data.saving_goals.length === 0 ? (
              <EmptyState text={t.dashboard.noSavingGoals} />
            ) : data.saving_goals.slice(0, 4).map((goal) => (
              <div key={goal.goal_id} className="rounded-lg border border-border p-4">
                <div className="mb-3 flex items-center gap-3">
                  <span className="rounded-full p-2" style={{ backgroundColor: `${goal.color}22`, color: goal.color }}>
                    <Target size={20} />
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{goal.name}</p>
                    <p className="text-xs text-muted-foreground">{money(goal.converted_current_amount)} / {money(goal.converted_target_amount)}</p>
                  </div>
                </div>
                <ProgressRow label={goal.target_date ?? t.dashboard.noTargetDate} value={`${formatFixed(goal.progress_pct, 0)}%`} percent={goal.progress_pct} color={goal.color} compact />
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function compactMoney(value: number, lang: Language, currency: string) {
  return new Intl.NumberFormat(localeFor(lang), {
    style: "currency",
    currency,
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function KpiCard({ title, value, change, icon, tone, lang, t, currency }: { title: string; value: number | string; change: number | string | null; icon: React.ReactNode; tone: "green" | "red" | "blue" | "cyan"; lang: Language; t: Translations; currency: string }) {
  const tones = {
    green: "bg-emerald-500/15 text-emerald-300",
    red: "bg-red-500/15 text-red-300",
    blue: "bg-sky-500/15 text-sky-300",
    cyan: "bg-cyan-500/15 text-cyan-300",
  };
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <span className={`rounded-full p-3 ${tones[tone]}`}>{icon}</span>
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{title}</p>
          <p className="truncate text-2xl font-bold">{formatMoney(value, lang, t.dashboard.noQuote, currency)}</p>
          <p className={`text-xs ${(toNumber(change) ?? 0) < 0 ? "text-red-300" : "text-emerald-300"}`}>
            {formatPct(change, t.dashboard.noPreviousPeriod)} {t.dashboard.previousPeriod}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

function Panel({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function EmptyState({ text }: { text: string }) {
  return <p className="py-8 text-center text-sm text-muted-foreground">{text}</p>;
}

function TableLike({ rows, empty }: { rows: string[][]; empty: string }) {
  if (rows.length === 0) return <EmptyState text={empty} />;
  return (
    <div className="space-y-2">
      {rows.map((row, index) => (
        <div key={`${row[0]}-${index}`} className="grid grid-cols-[1.2fr_0.8fr_auto] gap-2 border-b border-border/70 pb-2 text-xs last:border-0">
          <span className="truncate font-medium">{row[0]}</span>
          <span className="truncate text-muted-foreground">{row[1]}</span>
          <span className="font-mono">{row[2]}</span>
        </div>
      ))}
    </div>
  );
}

function ProgressRow({ label, value, percent, color, compact = false }: { label: string; value: string; percent: number | string; color: string; compact?: boolean }) {
  return (
    <div className={compact ? "space-y-1" : "space-y-1.5"}>
      <div className="flex items-center justify-between gap-3 text-xs">
        <span className="truncate">{label}</span>
        <span className="shrink-0 text-muted-foreground">{value}</span>
      </div>
      <div className="h-2 rounded-full bg-white/10">
        <div className="h-2 rounded-full" style={{ width: `${Math.min(toNumber(percent) ?? 0, 100)}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}
