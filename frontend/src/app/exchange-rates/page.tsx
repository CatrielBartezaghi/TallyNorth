"use client";

import { useEffect, useMemo, useState } from "react";
import { currenciesApi, exchangeRatesApi, type Currency, type ExchangeRate, type ExchangeRatePayload } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useLanguage } from "@/lib/LanguageContext";

const today = () => new Date().toISOString().slice(0, 10);

const EMPTY: ExchangeRatePayload = {
  from_currency_id: "",
  to_currency_id: "",
  rate: 1,
  date: today(),
};

export default function ExchangeRatesPage() {
  const [items, setItems] = useState<ExchangeRate[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [form, setForm] = useState<ExchangeRatePayload>(EMPTY);
  const [editing, setEditing] = useState<ExchangeRate | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [quoting, setQuoting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const { lang, t } = useLanguage();
  const currencyMap = useMemo(() => new Map(currencies.map((item) => [item.id, item])), [currencies]);
  const locale = lang === "es" ? "es-AR" : "en-US";

  const load = async () => {
    try {
      setLoading(true);
      const [rateRows, currencyRows] = await Promise.all([exchangeRatesApi.list(), currenciesApi.list()]);
      setItems(rateRows);
      setCurrencies(currencyRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.exchangeRates.loadError);
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { void load(); }, []);

  const openCreate = () => {
    const ars = currencies.find((item) => item.code === "ARS");
    const firstForeign = currencies.find((item) => item.code !== "ARS");
    setEditing(null);
    setForm({ ...EMPTY, from_currency_id: firstForeign?.id ?? currencies[0]?.id ?? "", to_currency_id: ars?.id ?? currencies[1]?.id ?? "" });
    setDialogError(null);
    setOpen(true);
  };

  const openEdit = (item: ExchangeRate) => {
    setEditing(item);
    setForm({
      from_currency_id: item.from_currency_id,
      to_currency_id: item.to_currency_id,
      rate: item.rate,
      date: item.date,
    });
    setDialogError(null);
    setOpen(true);
  };

  const save = async () => {
    const duplicate = items.find((item) => (
      item.id !== editing?.id &&
      item.from_currency_id === form.from_currency_id &&
      item.to_currency_id === form.to_currency_id &&
      item.date === form.date
    ));
    if (duplicate) {
      setDialogError(t.exchangeRates.duplicate);
      return;
    }
    try {
      if (editing) await exchangeRatesApi.update(editing.id, { rate: form.rate, date: form.date });
      else await exchangeRatesApi.create(form);
      setOpen(false);
      setDialogError(null);
      await load();
    } catch (e: unknown) {
      setDialogError(e instanceof Error ? e.message : t.exchangeRates.saveError);
    }
  };

  const syncMarketRates = async () => {
    try {
      setSyncing(true);
      await exchangeRatesApi.sync({ to: "ARS", from_codes: "USD" });
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.exchangeRates.syncError);
    } finally {
      setSyncing(false);
    }
  };

  const fillMarketPrice = async () => {
    if (!form.from_currency_id || !form.to_currency_id || form.from_currency_id === form.to_currency_id) return;
    try {
      setQuoting(true);
      const quote = await exchangeRatesApi.quote({
        from_currency_id: form.from_currency_id,
        to_currency_id: form.to_currency_id,
      });
      setForm({ ...form, rate: quote.rate, date: quote.date });
      setDialogError(null);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.exchangeRates.quoteError);
    } finally {
      setQuoting(false);
    }
  };

  const remove = async (id: string) => {
    if (!confirm(t.exchangeRates.confirmDelete)) return;
    await exchangeRatesApi.delete(id);
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.exchangeRates.title}</h1>
          <p className="mt-1 text-muted-foreground">{t.exchangeRates.subtitle}</p>
        </div>
        <Button variant="outline" onClick={syncMarketRates} disabled={syncing}>{syncing ? t.exchangeRates.updating : t.exchangeRates.updateMarket}</Button>
        <Button onClick={openCreate} disabled={currencies.length < 2}>{t.exchangeRates.add}</Button>
      </div>
      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader><TableRow><TableHead>{t.exchangeRates.from}</TableHead><TableHead>{t.exchangeRates.to}</TableHead><TableHead>{t.common.date}</TableHead><TableHead className="text-right">{t.exchangeRates.price}</TableHead><TableHead className="text-right">{t.common.actions}</TableHead></TableRow></TableHeader>
          <TableBody>
            {loading ? <TableRow><TableCell colSpan={5}>{t.common.loading}</TableCell></TableRow> : items.length === 0 ? <TableRow><TableCell colSpan={5}>{t.exchangeRates.noRates}</TableCell></TableRow> : items.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.from_currency.code}</TableCell>
                <TableCell>{item.to_currency.code}</TableCell>
                <TableCell>{item.date}</TableCell>
                <TableCell className="text-right font-mono">{Number(item.rate).toLocaleString(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                <TableCell className="space-x-2 text-right"><Button variant="ghost" size="sm" onClick={() => openEdit(item)}>{t.common.edit}</Button><Button variant="ghost" size="sm" className="text-red-400" onClick={() => remove(item.id)}>{t.common.delete}</Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? t.exchangeRates.editDialog : t.exchangeRates.addDialog}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <Field label={t.exchangeRates.from}>
                <Select value={form.from_currency_id} disabled={!!editing} onValueChange={(v) => { setDialogError(null); setForm({ ...form, from_currency_id: v ?? "" }); }}>
                  <SelectTrigger><span className="text-sm">{currencyMap.get(form.from_currency_id)?.code ?? t.common.select}</span></SelectTrigger>
                  <SelectContent>{currencies.map((item) => <SelectItem key={item.id} value={item.id}>{item.code}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label={t.exchangeRates.to}>
                <Select value={form.to_currency_id} disabled={!!editing} onValueChange={(v) => { setDialogError(null); setForm({ ...form, to_currency_id: v ?? "" }); }}>
                  <SelectTrigger><span className="text-sm">{currencyMap.get(form.to_currency_id)?.code ?? t.common.select}</span></SelectTrigger>
                  <SelectContent>{currencies.map((item) => <SelectItem key={item.id} value={item.id}>{item.code}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label={t.common.date}><Input type="date" value={form.date} onChange={(e) => { setDialogError(null); setForm({ ...form, date: e.target.value }); }} /></Field>
              <Field label={t.exchangeRates.price}><Input type="number" min="0" step="0.01" value={form.rate} onFocus={(e) => e.currentTarget.select()} onChange={(e) => { setDialogError(null); setForm({ ...form, rate: parseFloat(e.target.value) || 0 }); }} /></Field>
            </div>
            {dialogError && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300">{dialogError}</div>}
            <Button variant="outline" onClick={fillMarketPrice} disabled={quoting || !form.from_currency_id || !form.to_currency_id || form.from_currency_id === form.to_currency_id}>
              {quoting ? t.exchangeRates.getting : t.exchangeRates.getMarketPrice}
            </Button>
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setOpen(false)}>{t.common.cancel}</Button><Button onClick={save} disabled={!form.from_currency_id || !form.to_currency_id || form.from_currency_id === form.to_currency_id || form.rate <= 0}>{t.common.save}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}
