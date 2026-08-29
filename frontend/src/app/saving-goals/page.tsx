"use client";

import { useEffect, useMemo, useState } from "react";
import {
  accountsApi,
  currenciesApi,
  investmentsApi,
  savingGoalsApi,
  type Account,
  type Currency,
  type Investment,
  type SavingGoal,
  type SavingGoalAllocation,
  type SavingGoalPayload,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useLanguage } from "@/lib/LanguageContext";
import type { Language } from "@/lib/translations";

const EMPTY: SavingGoalPayload = {
  name: "",
  currency_id: "",
  target_amount: 0,
  current_amount: 0,
  target_date: null,
  color: "#22c55e",
  icon: "",
};

function formatAmount(amount: number, currency: Currency | undefined, lang: Language) {
  return `${currency?.symbol ?? "$"} ${Number(amount).toLocaleString(lang === "es" ? "es-AR" : "en-US", { maximumFractionDigits: 2 })}`;
}

export default function SavingGoalsPage() {
  const [items, setItems] = useState<SavingGoal[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [investments, setInvestments] = useState<Investment[]>([]);
  const [allocationCounts, setAllocationCounts] = useState<Record<string, number>>({});
  const [form, setForm] = useState<SavingGoalPayload>(EMPTY);
  const [editing, setEditing] = useState<SavingGoal | null>(null);
  const [open, setOpen] = useState(false);
  const [allocationGoal, setAllocationGoal] = useState<SavingGoal | null>(null);
  const [allocations, setAllocations] = useState<SavingGoalAllocation[]>([]);
  const [allocationOpen, setAllocationOpen] = useState(false);
  const [sourceType, setSourceType] = useState<"account" | "investment">("investment");
  const [sourceId, setSourceId] = useState("");
  const [allocationPercent, setAllocationPercent] = useState(100);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { lang, t } = useLanguage();
  const currencyMap = useMemo(() => new Map(currencies.map((item) => [item.id, item])), [currencies]);

  const ui = lang === "es" ? {
    allocations: "Asignaciones",
    automatic: "Automático",
    manual: "Manual",
    tracking: "Seguimiento",
    source: "Origen",
    percentage: "Porcentaje",
    addAllocation: "Asignar patrimonio",
    account: "Cuenta",
    investment: "Inversión",
    noAllocations: "Todavía no hay patrimonio asignado. Mientras no haya asignaciones, el avance sigue siendo manual.",
    allocationHint: "Cuando una meta tiene asignaciones, el dashboard calcula su avance desde esas cuentas/inversiones. La meta no se suma otra vez al patrimonio.",
  } : {
    allocations: "Allocations",
    automatic: "Automatic",
    manual: "Manual",
    tracking: "Tracking",
    source: "Source",
    percentage: "Percentage",
    addAllocation: "Allocate assets",
    account: "Account",
    investment: "Investment",
    noAllocations: "No assets are allocated yet. Until there are allocations, progress remains manual.",
    allocationHint: "When a goal has allocations, the dashboard derives progress from those accounts/investments. The goal is not added to wealth again.",
  };

  const load = async () => {
    try {
      setLoading(true);
      const [goalRows, currencyRows, accountRows, investmentRows] = await Promise.all([
        savingGoalsApi.list(),
        currenciesApi.list(),
        accountsApi.list(),
        investmentsApi.list(),
      ]);
      const allocationRows = await Promise.all(goalRows.map((goal) => savingGoalsApi.listAllocations(goal.id)));
      setItems(goalRows);
      setCurrencies(currencyRows);
      setAccounts(accountRows);
      setInvestments(investmentRows);
      setAllocationCounts(Object.fromEntries(goalRows.map((goal, index) => [goal.id, allocationRows[index].length])));
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.savingGoals.loadError);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY, currency_id: currencies[0]?.id ?? "" });
    setOpen(true);
  };

  const openEdit = (item: SavingGoal) => {
    setEditing(item);
    setForm({
      name: item.name,
      currency_id: item.currency_id,
      target_amount: item.target_amount,
      current_amount: item.current_amount,
      target_date: item.target_date,
      color: item.color,
      icon: item.icon ?? "",
    });
    setOpen(true);
  };

  const save = async () => {
    const payload = { ...form, target_date: form.target_date || null, icon: form.icon || null };
    if (editing) await savingGoalsApi.update(editing.id, payload);
    else await savingGoalsApi.create(payload);
    setOpen(false);
    await load();
  };

  const remove = async (id: string) => {
    if (!confirm(t.savingGoals.confirmDelete)) return;
    await savingGoalsApi.delete(id);
    await load();
  };

  const openAllocations = async (goal: SavingGoal) => {
    const rows = await savingGoalsApi.listAllocations(goal.id);
    setAllocationGoal(goal);
    setAllocations(rows);
    setSourceType("investment");
    const firstInvestment = investments.find((item) => item.currency_id === goal.currency_id);
    setSourceId(firstInvestment?.id ?? "");
    setAllocationPercent(100);
    setAllocationOpen(true);
  };

  const availableSources = allocationGoal
    ? sourceType === "account"
      ? accounts.filter((item) => item.currency_id === allocationGoal.currency_id)
      : investments.filter((item) => item.currency_id === allocationGoal.currency_id)
    : [];

  const createAllocation = async () => {
    if (!allocationGoal || !sourceId || allocationPercent <= 0) return;
    await savingGoalsApi.createAllocation(allocationGoal.id, {
      account_id: sourceType === "account" ? sourceId : null,
      investment_id: sourceType === "investment" ? sourceId : null,
      allocation_percent: allocationPercent,
    });
    const rows = await savingGoalsApi.listAllocations(allocationGoal.id);
    setAllocations(rows);
    await load();
  };

  const deleteAllocation = async (allocationId: string) => {
    if (!allocationGoal) return;
    await savingGoalsApi.deleteAllocation(allocationGoal.id, allocationId);
    const rows = await savingGoalsApi.listAllocations(allocationGoal.id);
    setAllocations(rows);
    await load();
  };

  const sourceName = (allocation: SavingGoalAllocation) => {
    if (allocation.account_id) return accounts.find((item) => item.id === allocation.account_id)?.name ?? allocation.account_id;
    return investments.find((item) => item.id === allocation.investment_id)?.name ?? allocation.investment_id ?? "-";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.savingGoals.title}</h1>
          <p className="mt-1 text-muted-foreground">{t.savingGoals.subtitle}</p>
        </div>
        <Button onClick={openCreate} disabled={currencies.length === 0}>{t.savingGoals.add}</Button>
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t.common.name}</TableHead>
              <TableHead>{t.common.currency}</TableHead>
              <TableHead>{ui.tracking}</TableHead>
              <TableHead className="text-right">{t.savingGoals.currentAmount}</TableHead>
              <TableHead className="text-right">{t.savingGoals.target}</TableHead>
              <TableHead>{t.savingGoals.targetDate}</TableHead>
              <TableHead className="text-right">{t.common.actions}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={7}>{t.common.loading}</TableCell></TableRow>
            ) : items.length === 0 ? (
              <TableRow><TableCell colSpan={7}>{t.savingGoals.noGoals}</TableCell></TableRow>
            ) : items.map((item) => {
              const automatic = (allocationCounts[item.id] ?? 0) > 0;
              return (
                <TableRow key={item.id}>
                  <TableCell className="font-medium"><span className="mr-2 inline-block h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />{item.name}</TableCell>
                  <TableCell>{item.currency.code}</TableCell>
                  <TableCell>{automatic ? ui.automatic : ui.manual}</TableCell>
                  <TableCell className="text-right font-mono">{automatic ? "—" : formatAmount(item.current_amount, item.currency, lang)}</TableCell>
                  <TableCell className="text-right font-mono">{formatAmount(item.target_amount, item.currency, lang)}</TableCell>
                  <TableCell>{item.target_date ?? "-"}</TableCell>
                  <TableCell className="space-x-2 text-right">
                    <Button variant="outline" size="sm" onClick={() => void openAllocations(item)}>{ui.allocations}</Button>
                    <Button variant="ghost" size="sm" onClick={() => openEdit(item)}>{t.common.edit}</Button>
                    <Button variant="ghost" size="sm" className="text-red-400" onClick={() => void remove(item.id)}>{t.common.delete}</Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? t.savingGoals.editDialog : t.savingGoals.addDialog}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <Field label={t.common.name}><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label={t.common.currency}>
                <Select value={form.currency_id} onValueChange={(v) => setForm({ ...form, currency_id: v ?? "" })}>
                  <SelectTrigger><span className="text-sm">{currencyMap.get(form.currency_id)?.code ?? t.common.select}</span></SelectTrigger>
                  <SelectContent>{currencies.map((item) => <SelectItem key={item.id} value={item.id}>{item.code}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label={t.common.color}><Input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} /></Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label={t.savingGoals.currentAmount}><Input type="number" min="0" step="0.01" value={form.current_amount || ""} onChange={(e) => setForm({ ...form, current_amount: parseFloat(e.target.value) || 0 })} /></Field>
              <Field label={t.savingGoals.target}><Input type="number" min="0" step="0.01" value={form.target_amount || ""} onChange={(e) => setForm({ ...form, target_amount: parseFloat(e.target.value) || 0 })} /></Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label={t.savingGoals.targetDate}><Input type="date" value={form.target_date ?? ""} onChange={(e) => setForm({ ...form, target_date: e.target.value || null })} /></Field>
              <Field label={t.savingGoals.icon}><Input value={form.icon ?? ""} onChange={(e) => setForm({ ...form, icon: e.target.value })} /></Field>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>{t.common.cancel}</Button>
            <Button onClick={() => void save()} disabled={!form.name || !form.currency_id || form.target_amount <= 0}>{t.common.save}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={allocationOpen} onOpenChange={setAllocationOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{allocationGoal?.name} · {ui.allocations}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <p className="text-sm text-muted-foreground">{ui.allocationHint}</p>
            <div className="grid grid-cols-3 gap-3">
              <Field label={ui.source}>
                <Select value={sourceType} onValueChange={(v) => {
                  const next = (v ?? "investment") as "account" | "investment";
                  setSourceType(next);
                  const candidates = next === "account"
                    ? accounts.filter((item) => item.currency_id === allocationGoal?.currency_id)
                    : investments.filter((item) => item.currency_id === allocationGoal?.currency_id);
                  setSourceId(candidates[0]?.id ?? "");
                }}>
                  <SelectTrigger><span className="text-sm">{sourceType === "account" ? ui.account : ui.investment}</span></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="account">{ui.account}</SelectItem>
                    <SelectItem value="investment">{ui.investment}</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label={sourceType === "account" ? ui.account : ui.investment}>
                <Select value={sourceId} onValueChange={(v) => setSourceId(v ?? "")}>
                  <SelectTrigger><span className="text-sm">{availableSources.find((item) => item.id === sourceId)?.name ?? t.common.select}</span></SelectTrigger>
                  <SelectContent>{availableSources.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label={ui.percentage}><Input type="number" min="0.01" max="100" step="0.01" value={allocationPercent} onChange={(e) => setAllocationPercent(parseFloat(e.target.value) || 0)} /></Field>
            </div>
            <Button onClick={() => void createAllocation()} disabled={!sourceId || allocationPercent <= 0 || allocationPercent > 100}>{ui.addAllocation}</Button>

            <div className="rounded-lg border">
              <Table>
                <TableHeader><TableRow><TableHead>{ui.source}</TableHead><TableHead className="text-right">{ui.percentage}</TableHead><TableHead className="text-right">{t.common.actions}</TableHead></TableRow></TableHeader>
                <TableBody>
                  {allocations.length === 0 ? (
                    <TableRow><TableCell colSpan={3}>{ui.noAllocations}</TableCell></TableRow>
                  ) : allocations.map((allocation) => (
                    <TableRow key={allocation.id}>
                      <TableCell>{sourceName(allocation)}</TableCell>
                      <TableCell className="text-right font-mono">{allocation.allocation_percent}%</TableCell>
                      <TableCell className="text-right"><Button variant="ghost" size="sm" className="text-red-400" onClick={() => void deleteAllocation(allocation.id)}>{t.common.delete}</Button></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}
