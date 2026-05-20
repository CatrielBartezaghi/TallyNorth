"use client";

import { useEffect, useMemo, useState } from "react";
import { currenciesApi, investmentsApi, type Currency, type Investment, type InvestmentPayload, type InvestmentType } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useLanguage } from "@/lib/LanguageContext";
import type { Language } from "@/lib/translations";

const TYPES: InvestmentType[] = ["fixed_income", "fund", "stock", "crypto", "forex", "other"];
const EMPTY: InvestmentPayload = {
  name: "",
  type: "other",
  currency_id: "",
  invested_amount: 0,
  current_value: 0,
  expected_return_rate: null,
  notes: "",
};

function formatAmount(amount: number, currency: Currency | undefined, lang: Language) {
  return `${currency?.symbol ?? "$"} ${amount.toLocaleString(lang === "es" ? "es-AR" : "en-US", { maximumFractionDigits: 2 })}`;
}

export default function InvestmentsPage() {
  const [items, setItems] = useState<Investment[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [form, setForm] = useState<InvestmentPayload>(EMPTY);
  const [editing, setEditing] = useState<Investment | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { lang, t } = useLanguage();
  const currencyMap = useMemo(() => new Map(currencies.map((item) => [item.id, item])), [currencies]);

  const load = async () => {
    try {
      setLoading(true);
      const [investmentRows, currencyRows] = await Promise.all([investmentsApi.list(), currenciesApi.list()]);
      setItems(investmentRows);
      setCurrencies(currencyRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.investments.loadError);
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

  const openEdit = (item: Investment) => {
    setEditing(item);
    setForm({
      name: item.name,
      type: item.type,
      currency_id: item.currency_id,
      invested_amount: item.invested_amount,
      current_value: item.current_value,
      expected_return_rate: item.expected_return_rate,
      notes: item.notes ?? "",
    });
    setOpen(true);
  };

  const save = async () => {
    const payload = { ...form, notes: form.notes || null };
    if (editing) await investmentsApi.update(editing.id, payload);
    else await investmentsApi.create(payload);
    setOpen(false);
    await load();
  };

  const remove = async (id: string) => {
    if (!confirm(t.investments.confirmDelete)) return;
    await investmentsApi.delete(id);
    await load();
  };

  const typeLabel = (type: InvestmentType) => t.enums[type];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.investments.title}</h1>
          <p className="mt-1 text-muted-foreground">{t.investments.subtitle}</p>
        </div>
        <Button onClick={openCreate} disabled={currencies.length === 0}>{t.investments.add}</Button>
      </div>
      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader><TableRow><TableHead>{t.common.name}</TableHead><TableHead>{t.common.type}</TableHead><TableHead>{t.common.currency}</TableHead><TableHead className="text-right">{t.investments.invested}</TableHead><TableHead className="text-right">{t.investments.currentValue}</TableHead><TableHead className="text-right">{t.investments.gain}</TableHead><TableHead className="text-right">{t.common.actions}</TableHead></TableRow></TableHeader>
          <TableBody>
            {loading ? <TableRow><TableCell colSpan={7}>{t.common.loading}</TableCell></TableRow> : items.length === 0 ? <TableRow><TableCell colSpan={7}>{t.investments.noInvestments}</TableCell></TableRow> : items.map((item) => {
              const gain = item.current_value - item.invested_amount;
              return (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell><Badge variant="outline">{typeLabel(item.type)}</Badge></TableCell>
                  <TableCell>{item.currency.code}</TableCell>
                  <TableCell className="text-right font-mono">{formatAmount(item.invested_amount, item.currency, lang)}</TableCell>
                  <TableCell className="text-right font-mono">{formatAmount(item.current_value, item.currency, lang)}</TableCell>
                  <TableCell className={`text-right font-mono ${gain >= 0 ? "text-emerald-400" : "text-red-400"}`}>{formatAmount(gain, item.currency, lang)}</TableCell>
                  <TableCell className="space-x-2 text-right"><Button variant="ghost" size="sm" onClick={() => openEdit(item)}>{t.common.edit}</Button><Button variant="ghost" size="sm" className="text-red-400" onClick={() => remove(item.id)}>{t.common.delete}</Button></TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? t.investments.editDialog : t.investments.addDialog}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <Field label={t.common.name}><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label={t.common.type}>
                <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: (v ?? "other") as InvestmentType })}>
                  <SelectTrigger><span className="text-sm">{typeLabel(form.type)}</span></SelectTrigger>
                  <SelectContent>{TYPES.map((type) => <SelectItem key={type} value={type}>{typeLabel(type)}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label={t.common.currency}>
                <Select value={form.currency_id} onValueChange={(v) => setForm({ ...form, currency_id: v ?? "" })}>
                  <SelectTrigger><span className="text-sm">{currencyMap.get(form.currency_id)?.code ?? t.common.select}</span></SelectTrigger>
                  <SelectContent>{currencies.map((item) => <SelectItem key={item.id} value={item.id}>{item.code}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Field label={t.investments.invested}><Input type="number" min="0" step="0.01" placeholder="0" value={form.invested_amount === 0 ? "" : form.invested_amount} onChange={(e) => setForm({ ...form, invested_amount: parseFloat(e.target.value) || 0 })} /></Field>
              <Field label={t.investments.currentValue}><Input type="number" min="0" step="0.01" placeholder="0" value={form.current_value === 0 ? "" : form.current_value} onChange={(e) => setForm({ ...form, current_value: parseFloat(e.target.value) || 0 })} /></Field>
              <Field label={t.investments.expectedRate}><Input type="number" step="0.01" value={form.expected_return_rate ?? ""} onFocus={(e) => e.currentTarget.select()} onChange={(e) => setForm({ ...form, expected_return_rate: e.target.value ? parseFloat(e.target.value) : null })} /></Field>
            </div>
            <Field label={t.common.notes}><Input value={form.notes ?? ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field>
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setOpen(false)}>{t.common.cancel}</Button><Button onClick={save} disabled={!form.name || !form.currency_id || form.invested_amount <= 0}>{t.common.save}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}
