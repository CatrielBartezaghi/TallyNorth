"use client";

import { useEffect, useMemo, useState } from "react";
import { CalendarClock, Check, Pencil, Plus, SkipForward, Trash2 } from "lucide-react";

import {
  accountsApi,
  categoriesApi,
  creditCardsApi,
  type Account,
  type Category,
  type CreditCard,
  type RecurrenceRule,
  type TransactionType,
} from "@/lib/api";
import {
  recurringEntriesApi,
  type RecurringEntry,
  type RecurringEntryPayload,
  type RecurringOccurrence,
  type RecurringSettlementMode,
} from "@/lib/recurring-api";
import { useLanguage } from "@/lib/LanguageContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

const today = () => new Date().toISOString().slice(0, 10);

type DestinationValue = `account:${string}` | `credit_card:${string}` | "";

interface ScheduledForm {
  type: TransactionType;
  amount: number;
  description: string;
  category_id: string;
  frequency: RecurrenceRule;
  start_date: string;
  end_date: string;
  one_time: boolean;
  active: boolean;
  settlement_mode: RecurringSettlementMode;
  destination: DestinationValue;
}

const EMPTY_FORM: ScheduledForm = {
  type: "income",
  amount: 0,
  description: "",
  category_id: "",
  frequency: "monthly",
  start_date: today(),
  end_date: "",
  one_time: false,
  active: true,
  settlement_mode: "manual",
  destination: "",
};

export default function ScheduledPage() {
  const { lang } = useLanguage();
  const es = lang === "es";
  const [entries, setEntries] = useState<RecurringEntry[]>([]);
  const [pending, setPending] = useState<RecurringOccurrence[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<RecurringEntry | null>(null);
  const [form, setForm] = useState<ScheduledForm>(EMPTY_FORM);

  const accountMap = useMemo(() => new Map(accounts.map((item) => [item.id, item])), [accounts]);
  const cardMap = useMemo(() => new Map(cards.map((item) => [item.id, item])), [cards]);

  const load = async () => {
    setLoading(true);
    try {
      const [entryRows, occurrenceRows, accountRows, cardRows, categoryRows] = await Promise.all([
        recurringEntriesApi.list(),
        recurringEntriesApi.occurrences({ status: "pending" }),
        accountsApi.list(),
        creditCardsApi.list(),
        categoriesApi.list(),
      ]);
      setEntries(entryRows);
      setPending(occurrenceRows);
      setAccounts(accountRows);
      setCards(cardRows);
      setCategories(categoryRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : es ? "No se pudieron cargar los programados" : "Failed to load scheduled entries");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const categoryOptions = categories.filter(
    (category) => category.type === form.type || category.type === "both",
  );

  const defaultDestination = (type: TransactionType): DestinationValue => {
    if (accounts[0]) return `account:${accounts[0].id}`;
    if (type === "expense" && cards[0]) return `credit_card:${cards[0].id}`;
    return "";
  };

  const destinationLabel = (entry: RecurringEntry) => {
    if (entry.destination_type === "account") {
      return accountMap.get(entry.account_id ?? "")?.name ?? "-";
    }
    return cardMap.get(entry.credit_card_id ?? "")?.name ?? "-";
  };

  const currencySymbol = (entry: RecurringEntry) => {
    if (entry.destination_type === "account") {
      return accountMap.get(entry.account_id ?? "")?.currency.symbol ?? "";
    }
    return cardMap.get(entry.credit_card_id ?? "")?.currency.symbol ?? "";
  };

  const formatAmount = (amount: number, entry: RecurringEntry) => {
    const formatted = amount.toLocaleString(es ? "es-AR" : "en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    const symbol = currencySymbol(entry);
    return symbol ? `${symbol} ${formatted}` : formatted;
  };

  const openCreate = () => {
    setEditing(null);
    setForm({
      ...EMPTY_FORM,
      start_date: today(),
      destination: defaultDestination("income"),
    });
    setDialogOpen(true);
  };

  const openEdit = (entry: RecurringEntry) => {
    const destination: DestinationValue = entry.destination_type === "account"
      ? `account:${entry.account_id}`
      : `credit_card:${entry.credit_card_id}`;
    setEditing(entry);
    setForm({
      type: entry.type,
      amount: entry.amount,
      description: entry.description,
      category_id: entry.category_id ?? "",
      frequency: entry.frequency,
      start_date: entry.start_date,
      end_date: entry.end_date ?? "",
      one_time: entry.end_date === entry.start_date,
      active: entry.active,
      settlement_mode: entry.settlement_mode,
      destination,
    });
    setDialogOpen(true);
  };

  const save = async () => {
    if (!form.destination || !form.description.trim() || form.amount <= 0) return;
    setSaving(true);
    try {
      const [destinationType, destinationId] = form.destination.split(":") as [
        "account" | "credit_card",
        string,
      ];
      const payload: RecurringEntryPayload = {
        type: form.type,
        amount: form.amount,
        description: form.description.trim(),
        category_id: form.category_id || null,
        frequency: form.one_time ? "monthly" : form.frequency,
        start_date: form.start_date,
        end_date: form.one_time ? form.start_date : form.end_date || null,
        active: form.active,
        settlement_mode: form.settlement_mode,
        destination_type: destinationType,
        account_id: destinationType === "account" ? destinationId : null,
        credit_card_id: destinationType === "credit_card" ? destinationId : null,
      };
      if (editing) await recurringEntriesApi.update(editing.id, payload);
      else await recurringEntriesApi.create(payload);
      setDialogOpen(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : es ? "No se pudo guardar" : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const remove = async (entry: RecurringEntry) => {
    const message = es
      ? "¿Eliminar este programado? Los movimientos ya confirmados se conservan."
      : "Delete this scheduled entry? Already confirmed movements are kept.";
    if (!confirm(message)) return;
    try {
      await recurringEntriesApi.delete(entry.id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : es ? "No se pudo eliminar" : "Delete failed");
    }
  };

  const settle = async (occurrence: RecurringOccurrence) => {
    try {
      await recurringEntriesApi.settleOccurrence(occurrence.id, today());
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : es ? "No se pudo confirmar" : "Confirmation failed");
    }
  };

  const skip = async (occurrence: RecurringOccurrence) => {
    const message = es ? "¿Omitir esta ocurrencia?" : "Skip this occurrence?";
    if (!confirm(message)) return;
    try {
      await recurringEntriesApi.skipOccurrence(occurrence.id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : es ? "No se pudo omitir" : "Skip failed");
    }
  };

  const changeType = (value: string | null) => {
    if (value !== "income" && value !== "expense") return;
    const nextType = value as TransactionType;
    const destinationStillValid =
      nextType === "expense" || !form.destination.startsWith("credit_card:");
    setForm((current) => ({
      ...current,
      type: nextType,
      category_id: "",
      destination: destinationStillValid ? current.destination : defaultDestination(nextType),
    }));
  };

  if (loading) {
    return <p className="text-sm text-muted-foreground">{es ? "Cargando programados..." : "Loading scheduled entries..."}</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <CalendarClock className="size-7 text-cyan-300" />
            <h1 className="text-3xl font-bold tracking-tight">{es ? "Programados" : "Scheduled"}</h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {es
              ? "Ingresos y gastos automáticos o pendientes de confirmación."
              : "Automatic income/expenses and items waiting for confirmation."}
          </p>
        </div>
        <Button onClick={openCreate} className="gap-2">
          <Plus size={16} />
          {es ? "Nuevo programado" : "New scheduled entry"}
        </Button>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{es ? "Pendientes de cobro / pago" : "Pending collection / payment"}</CardTitle>
        </CardHeader>
        <CardContent>
          {pending.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {es ? "No hay vencimientos pendientes." : "There are no pending due items."}
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{es ? "Fecha" : "Date"}</TableHead>
                  <TableHead>{es ? "Concepto" : "Description"}</TableHead>
                  <TableHead>{es ? "Tipo" : "Type"}</TableHead>
                  <TableHead>{es ? "Destino" : "Destination"}</TableHead>
                  <TableHead className="text-right">{es ? "Importe" : "Amount"}</TableHead>
                  <TableHead className="text-right">{es ? "Acciones" : "Actions"}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pending.map((occurrence) => {
                  const income = occurrence.entry.type === "income";
                  return (
                    <TableRow key={occurrence.id}>
                      <TableCell>{occurrence.scheduled_date}</TableCell>
                      <TableCell className="font-medium">{occurrence.entry.description}</TableCell>
                      <TableCell>
                        <Badge className={income ? "border-emerald-400/40 text-emerald-300" : "border-red-400/40 text-red-300"}>
                          {income ? (es ? "Ingreso" : "Income") : es ? "Gasto" : "Expense"}
                        </Badge>
                      </TableCell>
                      <TableCell>{destinationLabel(occurrence.entry)}</TableCell>
                      <TableCell className="text-right font-mono">
                        {formatAmount(occurrence.amount, occurrence.entry)}
                      </TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <Button size="sm" onClick={() => void settle(occurrence)} className="gap-1.5">
                            <Check size={14} />
                            {income ? (es ? "Cobrado" : "Collected") : es ? "Pagado" : "Paid"}
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => void skip(occurrence)} className="gap-1.5">
                            <SkipForward size={14} />
                            {es ? "Omitir" : "Skip"}
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{es ? "Reglas programadas" : "Scheduled rules"}</CardTitle>
        </CardHeader>
        <CardContent>
          {entries.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {es ? "Todavía no hay ingresos o gastos programados." : "No scheduled income or expenses yet."}
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{es ? "Concepto" : "Description"}</TableHead>
                  <TableHead>{es ? "Tipo" : "Type"}</TableHead>
                  <TableHead>{es ? "Frecuencia" : "Frequency"}</TableHead>
                  <TableHead>{es ? "Registro" : "Settlement"}</TableHead>
                  <TableHead>{es ? "Destino" : "Destination"}</TableHead>
                  <TableHead className="text-right">{es ? "Importe" : "Amount"}</TableHead>
                  <TableHead className="text-right">{es ? "Acciones" : "Actions"}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {entries.map((entry) => {
                  const oneTime = entry.end_date === entry.start_date;
                  const frequency = oneTime
                    ? es ? "Una vez" : "Once"
                    : entry.frequency === "weekly"
                      ? es ? "Semanal" : "Weekly"
                      : entry.frequency === "monthly"
                        ? es ? "Mensual" : "Monthly"
                        : es ? "Anual" : "Yearly";
                  return (
                    <TableRow key={entry.id}>
                      <TableCell>
                        <div className="font-medium">{entry.description}</div>
                        <div className="text-xs text-muted-foreground">
                          {entry.start_date}{entry.end_date && !oneTime ? ` → ${entry.end_date}` : ""}
                        </div>
                      </TableCell>
                      <TableCell>{entry.type === "income" ? (es ? "Ingreso" : "Income") : es ? "Gasto" : "Expense"}</TableCell>
                      <TableCell>{frequency}</TableCell>
                      <TableCell>
                        <Badge className={entry.settlement_mode === "manual" ? "border-amber-400/40 text-amber-300" : "border-cyan-400/40 text-cyan-300"}>
                          {entry.settlement_mode === "manual" ? (es ? "Confirmar" : "Manual") : es ? "Automático" : "Automatic"}
                        </Badge>
                      </TableCell>
                      <TableCell>{destinationLabel(entry)}</TableCell>
                      <TableCell className="text-right font-mono">{formatAmount(entry.amount, entry)}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <Button size="sm" variant="outline" onClick={() => openEdit(entry)}>
                            <Pencil size={14} />
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => void remove(entry)}>
                            <Trash2 size={14} />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>
              {editing
                ? es ? "Editar programado" : "Edit scheduled entry"
                : es ? "Nuevo programado" : "New scheduled entry"}
            </DialogTitle>
          </DialogHeader>

          <div className="grid gap-4 py-2 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>{es ? "Tipo" : "Type"}</Label>
              <Select value={form.type} onValueChange={changeType}>
                <SelectTrigger>{form.type === "income" ? (es ? "Ingreso" : "Income") : es ? "Gasto" : "Expense"}</SelectTrigger>
                <SelectContent>
                  <SelectItem value="income">{es ? "Ingreso" : "Income"}</SelectItem>
                  <SelectItem value="expense">{es ? "Gasto" : "Expense"}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{es ? "Importe" : "Amount"}</Label>
              <Input type="number" min="0" step="0.01" value={form.amount || ""} onChange={(event) => setForm((current) => ({ ...current, amount: Number(event.target.value) }))} />
            </div>

            <div className="space-y-2 sm:col-span-2">
              <Label>{es ? "Descripción" : "Description"}</Label>
              <Input value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} placeholder={es ? "Ej. Honorarios cliente" : "E.g. Client fee"} />
            </div>

            <div className="space-y-2">
              <Label>{es ? "Categoría" : "Category"}</Label>
              <Select value={form.category_id || "none"} onValueChange={(value) => setForm((current) => ({ ...current, category_id: value === "none" || !value ? "" : value }))}>
                <SelectTrigger>{form.category_id ? categories.find((item) => item.id === form.category_id)?.name ?? "-" : es ? "Sin categoría" : "No category"}</SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{es ? "Sin categoría" : "No category"}</SelectItem>
                  {categoryOptions.map((category) => (
                    <SelectItem key={category.id} value={category.id}>{category.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{es ? "Cuenta / tarjeta" : "Account / card"}</Label>
              <Select value={form.destination} onValueChange={(value) => setForm((current) => ({ ...current, destination: (value ?? "") as DestinationValue }))}>
                <SelectTrigger>
                  {form.destination.startsWith("account:")
                    ? `${es ? "Cuenta" : "Account"} · ${accountMap.get(form.destination.slice(8))?.name ?? "-"}`
                    : form.destination.startsWith("credit_card:")
                      ? `${es ? "Tarjeta" : "Card"} · ${cardMap.get(form.destination.slice(12))?.name ?? "-"}`
                      : es ? "Seleccionar" : "Select"}
                </SelectTrigger>
                <SelectContent>
                  {accounts.map((account) => (
                    <SelectItem key={`account:${account.id}`} value={`account:${account.id}`}>{es ? "Cuenta" : "Account"} · {account.name}</SelectItem>
                  ))}
                  {form.type === "expense" ? cards.map((card) => (
                    <SelectItem key={`credit_card:${card.id}`} value={`credit_card:${card.id}`}>{es ? "Tarjeta" : "Card"} · {card.name}</SelectItem>
                  )) : null}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{es ? "Fecha inicial" : "Start date"}</Label>
              <Input type="date" value={form.start_date} onChange={(event) => setForm((current) => ({ ...current, start_date: event.target.value }))} />
            </div>

            <div className="space-y-2">
              <Label>{es ? "Registro" : "Settlement"}</Label>
              <Select value={form.settlement_mode} onValueChange={(value) => {
                if (value === "automatic" || value === "manual") {
                  setForm((current) => ({ ...current, settlement_mode: value }));
                }
              }}>
                <SelectTrigger>{form.settlement_mode === "manual" ? (es ? "Confirmación manual" : "Manual confirmation") : es ? "Automático" : "Automatic"}</SelectTrigger>
                <SelectContent>
                  <SelectItem value="manual">
                    {form.type === "income"
                      ? es ? "Esperar confirmación de cobro" : "Wait for collection confirmation"
                      : es ? "Esperar confirmación de pago" : "Wait for payment confirmation"}
                  </SelectItem>
                  <SelectItem value="automatic">{es ? "Registrar automáticamente al vencer" : "Post automatically when due"}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <input type="checkbox" checked={form.one_time} onChange={(event) => setForm((current) => ({ ...current, one_time: event.target.checked, end_date: event.target.checked ? current.start_date : current.end_date }))} />
              {es ? "Ocurre una sola vez" : "Occurs only once"}
            </label>

            {!form.one_time ? (
              <>
                <div className="space-y-2">
                  <Label>{es ? "Frecuencia" : "Frequency"}</Label>
                  <Select value={form.frequency} onValueChange={(value) => {
                    if (value === "weekly" || value === "monthly" || value === "yearly") {
                      setForm((current) => ({ ...current, frequency: value }));
                    }
                  }}>
                    <SelectTrigger>{form.frequency === "weekly" ? (es ? "Semanal" : "Weekly") : form.frequency === "monthly" ? (es ? "Mensual" : "Monthly") : es ? "Anual" : "Yearly"}</SelectTrigger>
                    <SelectContent>
                      <SelectItem value="weekly">{es ? "Semanal" : "Weekly"}</SelectItem>
                      <SelectItem value="monthly">{es ? "Mensual" : "Monthly"}</SelectItem>
                      <SelectItem value="yearly">{es ? "Anual" : "Yearly"}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>{es ? "Fecha final (opcional)" : "End date (optional)"}</Label>
                  <Input type="date" value={form.end_date} onChange={(event) => setForm((current) => ({ ...current, end_date: event.target.value }))} />
                </div>
              </>
            ) : null}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>{es ? "Cancelar" : "Cancel"}</Button>
            <Button disabled={saving || !form.destination || !form.description.trim() || form.amount <= 0} onClick={() => void save()}>
              {saving ? (es ? "Guardando..." : "Saving...") : es ? "Guardar" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
