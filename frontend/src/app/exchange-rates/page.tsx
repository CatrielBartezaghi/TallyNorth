"use client";

import { useEffect, useMemo, useState } from "react";
import { currenciesApi, exchangeRatesApi, type Currency, type ExchangeRate, type ExchangeRatePayload } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

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
  const currencyMap = useMemo(() => new Map(currencies.map((item) => [item.id, item])), [currencies]);

  const load = async () => {
    try {
      setLoading(true);
      const [rateRows, currencyRows] = await Promise.all([exchangeRatesApi.list(), currenciesApi.list()]);
      setItems(rateRows);
      setCurrencies(currencyRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "No se pudieron cargar las cotizaciones");
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load(); }, []);

  const openCreate = () => {
    const ars = currencies.find((item) => item.code === "ARS");
    const firstForeign = currencies.find((item) => item.code !== "ARS");
    setEditing(null);
    setForm({ ...EMPTY, from_currency_id: firstForeign?.id ?? currencies[0]?.id ?? "", to_currency_id: ars?.id ?? currencies[1]?.id ?? "" });
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
    setOpen(true);
  };

  const save = async () => {
    if (editing) await exchangeRatesApi.update(editing.id, { rate: form.rate, date: form.date });
    else await exchangeRatesApi.create(form);
    setOpen(false);
    await load();
  };

  const syncMarketRates = async () => {
    try {
      setSyncing(true);
      await exchangeRatesApi.sync({ to: "ARS", from_codes: "USD,EUR,BTC" });
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "No se pudieron actualizar las cotizaciones");
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
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "No se pudo obtener el precio de mercado");
    } finally {
      setQuoting(false);
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Eliminar esta cotización?")) return;
    await exchangeRatesApi.delete(id);
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Cotizaciones</h1>
          <p className="mt-1 text-muted-foreground">Carga precios de conversión para consolidar el dashboard en ARS.</p>
        </div>
        <Button variant="outline" onClick={syncMarketRates} disabled={syncing}>{syncing ? "Actualizando..." : "Actualizar mercado"}</Button>
        <Button onClick={openCreate} disabled={currencies.length < 2}>+ Agregar cotización</Button>
      </div>
      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader><TableRow><TableHead>Desde</TableHead><TableHead>Hacia</TableHead><TableHead>Fecha</TableHead><TableHead className="text-right">Precio</TableHead><TableHead className="text-right">Acciones</TableHead></TableRow></TableHeader>
          <TableBody>
            {loading ? <TableRow><TableCell colSpan={5}>Cargando...</TableCell></TableRow> : items.length === 0 ? <TableRow><TableCell colSpan={5}>Sin cotizaciones.</TableCell></TableRow> : items.map((item) => (
              <TableRow key={item.id}>
                <TableCell>{item.from_currency.code}</TableCell>
                <TableCell>{item.to_currency.code}</TableCell>
                <TableCell>{item.date}</TableCell>
                <TableCell className="text-right font-mono">{Number(item.rate).toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                <TableCell className="space-x-2 text-right"><Button variant="ghost" size="sm" onClick={() => openEdit(item)}>Editar</Button><Button variant="ghost" size="sm" className="text-red-400" onClick={() => remove(item.id)}>Eliminar</Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Editar cotización" : "Agregar cotización"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Desde">
                <Select value={form.from_currency_id} disabled={!!editing} onValueChange={(v) => setForm({ ...form, from_currency_id: v ?? "" })}>
                  <SelectTrigger><span className="text-sm">{currencyMap.get(form.from_currency_id)?.code ?? "Seleccionar"}</span></SelectTrigger>
                  <SelectContent>{currencies.map((item) => <SelectItem key={item.id} value={item.id}>{item.code}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label="Hacia">
                <Select value={form.to_currency_id} disabled={!!editing} onValueChange={(v) => setForm({ ...form, to_currency_id: v ?? "" })}>
                  <SelectTrigger><span className="text-sm">{currencyMap.get(form.to_currency_id)?.code ?? "Seleccionar"}</span></SelectTrigger>
                  <SelectContent>{currencies.map((item) => <SelectItem key={item.id} value={item.id}>{item.code}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Fecha"><Input type="date" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></Field>
              <Field label="Precio"><Input type="number" min="0" step="0.01" value={form.rate} onFocus={(e) => e.currentTarget.select()} onChange={(e) => setForm({ ...form, rate: parseFloat(e.target.value) || 0 })} /></Field>
            </div>
            <Button variant="outline" onClick={fillMarketPrice} disabled={quoting || !form.from_currency_id || !form.to_currency_id || form.from_currency_id === form.to_currency_id}>
              {quoting ? "Obteniendo..." : "Obtener precio de mercado"}
            </Button>
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button><Button onClick={save} disabled={!form.from_currency_id || !form.to_currency_id || form.from_currency_id === form.to_currency_id || form.rate <= 0}>Guardar</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}
