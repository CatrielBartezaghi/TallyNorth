"use client";

import { useEffect, useMemo, useState } from "react";
import { currenciesApi, savingGoalsApi, type Currency, type SavingGoal, type SavingGoalPayload } from "@/lib/api";
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
  return `${currency?.symbol ?? "$"} ${amount.toLocaleString(lang === "es" ? "es-AR" : "en-US", { maximumFractionDigits: 2 })}`;
}

export default function SavingGoalsPage() {
  const [items, setItems] = useState<SavingGoal[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [form, setForm] = useState<SavingGoalPayload>(EMPTY);
  const [editing, setEditing] = useState<SavingGoal | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { lang, t } = useLanguage();
  const currencyMap = useMemo(() => new Map(currencies.map((item) => [item.id, item])), [currencies]);

  const load = async () => {
    try {
      setLoading(true);
      const [goalRows, currencyRows] = await Promise.all([savingGoalsApi.list(), currenciesApi.list()]);
      setItems(goalRows);
      setCurrencies(currencyRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.savingGoals.loadError);
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { void load(); }, []);

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
          <TableHeader><TableRow><TableHead>{t.common.name}</TableHead><TableHead>{t.common.currency}</TableHead><TableHead className="text-right">{t.savingGoals.currentAmount}</TableHead><TableHead className="text-right">{t.savingGoals.target}</TableHead><TableHead>{t.savingGoals.targetDate}</TableHead><TableHead className="text-right">{t.common.actions}</TableHead></TableRow></TableHeader>
          <TableBody>
            {loading ? <TableRow><TableCell colSpan={6}>{t.common.loading}</TableCell></TableRow> : items.length === 0 ? <TableRow><TableCell colSpan={6}>{t.savingGoals.noGoals}</TableCell></TableRow> : items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-medium"><span className="mr-2 inline-block h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />{item.name}</TableCell>
                <TableCell>{item.currency.code}</TableCell>
                <TableCell className="text-right font-mono">{formatAmount(item.current_amount, item.currency, lang)}</TableCell>
                <TableCell className="text-right font-mono">{formatAmount(item.target_amount, item.currency, lang)}</TableCell>
                <TableCell>{item.target_date ?? "-"}</TableCell>
                <TableCell className="space-x-2 text-right"><Button variant="ghost" size="sm" onClick={() => openEdit(item)}>{t.common.edit}</Button><Button variant="ghost" size="sm" className="text-red-400" onClick={() => remove(item.id)}>{t.common.delete}</Button></TableCell>
              </TableRow>
            ))}
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
              <Field label={t.savingGoals.currentAmount}><Input type="number" min="0" step="0.01" placeholder="0" value={form.current_amount === 0 ? "" : form.current_amount} onChange={(e) => setForm({ ...form, current_amount: parseFloat(e.target.value) || 0 })} /></Field>
              <Field label={t.savingGoals.target}><Input type="number" min="0" step="0.01" placeholder="0" value={form.target_amount === 0 ? "" : form.target_amount} onChange={(e) => setForm({ ...form, target_amount: parseFloat(e.target.value) || 0 })} /></Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label={t.savingGoals.targetDate}><Input type="date" value={form.target_date ?? ""} onChange={(e) => setForm({ ...form, target_date: e.target.value || null })} /></Field>
              <Field label={t.savingGoals.icon}><Input value={form.icon ?? ""} onChange={(e) => setForm({ ...form, icon: e.target.value })} /></Field>
            </div>
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setOpen(false)}>{t.common.cancel}</Button><Button onClick={save} disabled={!form.name || !form.currency_id || form.target_amount <= 0}>{t.common.save}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}
