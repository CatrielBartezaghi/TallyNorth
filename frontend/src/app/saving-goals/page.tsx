"use client";

import { useEffect, useMemo, useState } from "react";
import { currenciesApi, savingGoalsApi, type Currency, type SavingGoal, type SavingGoalPayload } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const EMPTY: SavingGoalPayload = {
  name: "",
  currency_id: "",
  target_amount: 0,
  current_amount: 0,
  target_date: null,
  color: "#22c55e",
  icon: "",
};

function formatAmount(amount: number, currency?: Currency) {
  return `${currency?.symbol ?? "$"} ${amount.toLocaleString("es-AR", { maximumFractionDigits: 2 })}`;
}

export default function SavingGoalsPage() {
  const [items, setItems] = useState<SavingGoal[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [form, setForm] = useState<SavingGoalPayload>(EMPTY);
  const [editing, setEditing] = useState<SavingGoal | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const currencyMap = useMemo(() => new Map(currencies.map((item) => [item.id, item])), [currencies]);

  const load = async () => {
    try {
      setLoading(true);
      const [goalRows, currencyRows] = await Promise.all([savingGoalsApi.list(), currenciesApi.list()]);
      setItems(goalRows);
      setCurrencies(currencyRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "No se pudieron cargar las metas");
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
    if (!confirm("Eliminar esta meta?")) return;
    await savingGoalsApi.delete(id);
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Metas de ahorro</h1>
          <p className="mt-1 text-muted-foreground">Registra objetivos y avance acumulado.</p>
        </div>
        <Button onClick={openCreate} disabled={currencies.length === 0}>+ Agregar meta</Button>
      </div>
      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader><TableRow><TableHead>Nombre</TableHead><TableHead>Moneda</TableHead><TableHead className="text-right">Actual</TableHead><TableHead className="text-right">Objetivo</TableHead><TableHead>Fecha objetivo</TableHead><TableHead className="text-right">Acciones</TableHead></TableRow></TableHeader>
          <TableBody>
            {loading ? <TableRow><TableCell colSpan={6}>Cargando...</TableCell></TableRow> : items.length === 0 ? <TableRow><TableCell colSpan={6}>Sin metas.</TableCell></TableRow> : items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-medium"><span className="mr-2 inline-block h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />{item.name}</TableCell>
                <TableCell>{item.currency.code}</TableCell>
                <TableCell className="text-right font-mono">{formatAmount(item.current_amount, item.currency)}</TableCell>
                <TableCell className="text-right font-mono">{formatAmount(item.target_amount, item.currency)}</TableCell>
                <TableCell>{item.target_date ?? "-"}</TableCell>
                <TableCell className="space-x-2 text-right"><Button variant="ghost" size="sm" onClick={() => openEdit(item)}>Editar</Button><Button variant="ghost" size="sm" className="text-red-400" onClick={() => remove(item.id)}>Eliminar</Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Editar meta" : "Agregar meta"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <Field label="Nombre"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Moneda">
                <Select value={form.currency_id} onValueChange={(v) => setForm({ ...form, currency_id: v ?? "" })}>
                  <SelectTrigger><span className="text-sm">{currencyMap.get(form.currency_id)?.code ?? "Seleccionar"}</span></SelectTrigger>
                  <SelectContent>{currencies.map((item) => <SelectItem key={item.id} value={item.id}>{item.code}</SelectItem>)}</SelectContent>
                </Select>
              </Field>
              <Field label="Color"><Input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} /></Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Monto actual"><Input type="number" min="0" step="0.01" placeholder="0" value={form.current_amount === 0 ? "" : form.current_amount} onChange={(e) => setForm({ ...form, current_amount: parseFloat(e.target.value) || 0 })} /></Field>
              <Field label="Objetivo"><Input type="number" min="0" step="0.01" placeholder="0" value={form.target_amount === 0 ? "" : form.target_amount} onChange={(e) => setForm({ ...form, target_amount: parseFloat(e.target.value) || 0 })} /></Field>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Fecha objetivo"><Input type="date" value={form.target_date ?? ""} onChange={(e) => setForm({ ...form, target_date: e.target.value || null })} /></Field>
              <Field label="Icono"><Input value={form.icon ?? ""} onChange={(e) => setForm({ ...form, icon: e.target.value })} /></Field>
            </div>
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button><Button onClick={save} disabled={!form.name || !form.currency_id || form.target_amount <= 0}>Guardar</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}
