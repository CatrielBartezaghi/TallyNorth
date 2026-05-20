"use client";

import { useEffect, useMemo, useState } from "react";
import { budgetsApi, categoriesApi, currenciesApi, type Budget, type BudgetPayload, type Category, type Currency } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useLanguage } from "@/lib/LanguageContext";
import type { Language } from "@/lib/translations";

const monthStart = () => new Date().toISOString().slice(0, 7) + "-01";

const EMPTY: BudgetPayload = {
  category_id: "",
  currency_id: "",
  period_start: monthStart(),
  amount: 0,
  notes: "",
};

function formatAmount(amount: number, currency: Currency | undefined, lang: Language) {
  return `${currency?.symbol ?? "$"} ${amount.toLocaleString(lang === "es" ? "es-AR" : "en-US", { maximumFractionDigits: 2 })}`;
}

export default function BudgetsPage() {
  const [items, setItems] = useState<Budget[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [form, setForm] = useState<BudgetPayload>(EMPTY);
  const [editing, setEditing] = useState<Budget | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { lang, t } = useLanguage();

  const categoryMap = useMemo(() => new Map(categories.map((item) => [item.id, item])), [categories]);
  const currencyMap = useMemo(() => new Map(currencies.map((item) => [item.id, item])), [currencies]);

  const load = async () => {
    try {
      setLoading(true);
      const [budgetRows, categoryRows, currencyRows] = await Promise.all([
        budgetsApi.list(),
        categoriesApi.list(),
        currenciesApi.list(),
      ]);
      setItems(budgetRows);
      setCategories(categoryRows.filter((item) => item.type !== "income"));
      setCurrencies(currencyRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.budgets.loadError);
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { void load(); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY, category_id: categories[0]?.id ?? "", currency_id: currencies[0]?.id ?? "" });
    setOpen(true);
  };

  const openEdit = (item: Budget) => {
    setEditing(item);
    setForm({
      category_id: item.category_id,
      currency_id: item.currency_id,
      period_start: item.period_start,
      amount: item.amount,
      notes: item.notes ?? "",
    });
    setOpen(true);
  };

  const save = async () => {
    const payload = { ...form, notes: form.notes || null };
    if (editing) await budgetsApi.update(editing.id, payload);
    else await budgetsApi.create(payload);
    setOpen(false);
    await load();
  };

  const remove = async (id: string) => {
    if (!confirm(t.budgets.confirmDelete)) return;
    await budgetsApi.delete(id);
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.budgets.title}</h1>
          <p className="mt-1 text-muted-foreground">{t.budgets.subtitle}</p>
        </div>
        <Button onClick={openCreate} disabled={categories.length === 0 || currencies.length === 0}>{t.budgets.add}</Button>
      </div>
      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader><TableRow><TableHead>{t.budgets.month}</TableHead><TableHead>{t.common.category}</TableHead><TableHead>{t.common.currency}</TableHead><TableHead className="text-right">{t.common.amount}</TableHead><TableHead>{t.common.notes}</TableHead><TableHead className="text-right">{t.common.actions}</TableHead></TableRow></TableHeader>
          <TableBody>
            {loading ? <TableRow><TableCell colSpan={6}>{t.common.loading}</TableCell></TableRow> : items.length === 0 ? <TableRow><TableCell colSpan={6}>{t.budgets.noBudgets}</TableCell></TableRow> : items.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.period_start.slice(0, 7)}</TableCell>
                <TableCell>{item.category.name}</TableCell>
                <TableCell>{item.currency.code}</TableCell>
                <TableCell className="text-right font-mono">{formatAmount(item.amount, item.currency, lang)}</TableCell>
                <TableCell className="text-muted-foreground">{item.notes ?? "-"}</TableCell>
                <TableCell className="space-x-2 text-right">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(item)}>{t.common.edit}</Button>
                  <Button variant="ghost" size="sm" className="text-red-400" onClick={() => remove(item.id)}>{t.common.delete}</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? t.budgets.editDialog : t.budgets.addDialog}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <Field label={t.common.category}>
                <Select value={form.category_id} onValueChange={(v) => setForm({ ...form, category_id: v ?? "" })}>
                  <SelectTrigger><span className="truncate text-sm">{categoryMap.get(form.category_id)?.name ?? t.common.select}</span></SelectTrigger>
                  <SelectContent>{categories.map((item) => <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label={t.common.currency}>
                <Select value={form.currency_id} onValueChange={(v) => setForm({ ...form, currency_id: v ?? "" })}>
                  <SelectTrigger><span className="text-sm">{currencyMap.get(form.currency_id)?.code ?? t.common.select}</span></SelectTrigger>
                  <SelectContent>{currencies.map((item) => <SelectItem key={item.id} value={item.id}>{item.code}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label={t.budgets.month}><Input type="month" value={form.period_start.slice(0, 7)} onChange={(e) => setForm({ ...form, period_start: `${e.target.value}-01` })} /></Field>
              <Field label={t.common.amount}><Input type="number" min="0" step="0.01" placeholder="0" value={form.amount === 0 ? "" : form.amount} onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })} /></Field>
            </div>
            <Field label={t.common.notes}><Input value={form.notes ?? ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field>
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setOpen(false)}>{t.common.cancel}</Button><Button onClick={save} disabled={!form.category_id || !form.currency_id || form.amount <= 0}>{t.common.save}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}
