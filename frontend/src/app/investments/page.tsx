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

function formatAmount(amount: number, currency?: Currency) {
  return `${currency?.symbol ?? "$"} ${amount.toLocaleString("es-AR", { maximumFractionDigits: 2 })}`;
}

export default function InvestmentsPage() {
  const [items, setItems] = useState<Investment[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [form, setForm] = useState<InvestmentPayload>(EMPTY);
  const [editing, setEditing] = useState<Investment | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const currencyMap = useMemo(() => new Map(currencies.map((item) => [item.id, item])), [currencies]);

  const load = async () => {
    try {
      setLoading(true);
      const [investmentRows, currencyRows] = await Promise.all([investmentsApi.list(), currenciesApi.list()]);
      setItems(investmentRows);
      setCurrencies(currencyRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "No se pudieron cargar las inversiones");
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect
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
    if (!confirm("Eliminar esta inversión?")) return;
    await investmentsApi.delete(id);
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Inversiones</h1>
          <p className="mt-1 text-muted-foreground">Carga valores invertidos y valor actual manualmente.</p>
        </div>
        <Button onClick={openCreate} disabled={currencies.length === 0}>+ Agregar inversión</Button>
      </div>
      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader><TableRow><TableHead>Nombre</TableHead><TableHead>Tipo</TableHead><TableHead>Moneda</TableHead><TableHead className="text-right">Invertido</TableHead><TableHead className="text-right">Valor actual</TableHead><TableHead className="text-right">Ganancia</TableHead><TableHead className="text-right">Acciones</TableHead></TableRow></TableHeader>
          <TableBody>
            {loading ? <TableRow><TableCell colSpan={7}>Cargando...</TableCell></TableRow> : items.length === 0 ? <TableRow><TableCell colSpan={7}>Sin inversiones.</TableCell></TableRow> : items.map((item) => {
              const gain = item.current_value - item.invested_amount;
              return (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell><Badge variant="outline">{item.type}</Badge></TableCell>
                  <TableCell>{item.currency.code}</TableCell>
                  <TableCell className="text-right font-mono">{formatAmount(item.invested_amount, item.currency)}</TableCell>
                  <TableCell className="text-right font-mono">{formatAmount(item.current_value, item.currency)}</TableCell>
                  <TableCell className={`text-right font-mono ${gain >= 0 ? "text-emerald-400" : "text-red-400"}`}>{formatAmount(gain, item.currency)}</TableCell>
                  <TableCell className="space-x-2 text-right"><Button variant="ghost" size="sm" onClick={() => openEdit(item)}>Editar</Button><Button variant="ghost" size="sm" className="text-red-400" onClick={() => remove(item.id)}>Eliminar</Button></TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Editar inversión" : "Agregar inversión"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <Field label="Nombre"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Tipo">
                <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: (v ?? "other") as InvestmentType })}>
                  <SelectTrigger><span className="text-sm">{form.type}</span></SelectTrigger>
                  <SelectContent>{TYPES.map((type) => <SelectItem key={type} value={type}>{type}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label="Moneda">
                <Select value={form.currency_id} onValueChange={(v) => setForm({ ...form, currency_id: v ?? "" })}>
                  <SelectTrigger><span className="text-sm">{currencyMap.get(form.currency_id)?.code ?? "Seleccionar"}</span></SelectTrigger>
                  <SelectContent>{currencies.map((item) => <SelectItem key={item.id} value={item.id}>{item.code}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <Field label="Invertido"><Input type="number" min="0" step="0.01" placeholder="0" value={form.invested_amount === 0 ? "" : form.invested_amount} onChange={(e) => setForm({ ...form, invested_amount: parseFloat(e.target.value) || 0 })} /></Field>
              <Field label="Valor actual"><Input type="number" min="0" step="0.01" placeholder="0" value={form.current_value === 0 ? "" : form.current_value} onChange={(e) => setForm({ ...form, current_value: parseFloat(e.target.value) || 0 })} /></Field>
              <Field label="Tasa esperada"><Input type="number" step="0.01" value={form.expected_return_rate ?? ""} onFocus={(e) => e.currentTarget.select()} onChange={(e) => setForm({ ...form, expected_return_rate: e.target.value ? parseFloat(e.target.value) : null })} /></Field>
            </div>
            <Field label="Notas"><Input value={form.notes ?? ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field>
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button><Button onClick={save} disabled={!form.name || !form.currency_id || form.invested_amount <= 0}>Guardar</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}
