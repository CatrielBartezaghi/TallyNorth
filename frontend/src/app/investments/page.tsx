"use client";

import { useEffect, useMemo, useState } from "react";
import {
  accountsApi,
  currenciesApi,
  investmentsApi,
  type Account,
  type Currency,
  type Investment,
  type InvestmentOperation,
  type InvestmentOperationPayload,
  type InvestmentOperationType,
  type InvestmentPayload,
  type InvestmentType,
  type InvestmentValuation,
} from "@/lib/api";
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
const OPERATION_TYPES: InvestmentOperationType[] = ["buy", "sell", "dividend", "interest", "fee"];

const EMPTY: InvestmentPayload = {
  name: "",
  symbol: "",
  broker: "",
  type: "other",
  currency_id: "",
  invested_amount: 0,
  opening_quantity: null,
  current_value: 0,
  expected_return_rate: null,
  notes: "",
};

const today = () => new Date().toISOString().slice(0, 10);

function formatAmount(amount: number, currency: Currency | undefined, lang: Language) {
  return `${currency?.symbol ?? "$"} ${Number(amount).toLocaleString(lang === "es" ? "es-AR" : "en-US", { maximumFractionDigits: 2 })}`;
}

export default function InvestmentsPage() {
  const [items, setItems] = useState<Investment[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [form, setForm] = useState<InvestmentPayload>(EMPTY);
  const [editing, setEditing] = useState<Investment | null>(null);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Investment | null>(null);
  const [ledgerOpen, setLedgerOpen] = useState(false);
  const [operations, setOperations] = useState<InvestmentOperation[]>([]);
  const [valuations, setValuations] = useState<InvestmentValuation[]>([]);
  const [operationForm, setOperationForm] = useState<InvestmentOperationPayload>({
    type: "buy",
    account_id: null,
    quantity: null,
    unit_price: null,
    amount: 0,
    fee: 0,
    date: today(),
    notes: "",
  });
  const [valuationValue, setValuationValue] = useState(0);
  const [valuationDate, setValuationDate] = useState(today());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { lang, t } = useLanguage();
  const currencyMap = useMemo(() => new Map(currencies.map((item) => [item.id, item])), [currencies]);

  const ui = lang === "es" ? {
    symbol: "Símbolo / ticker",
    broker: "Broker / plataforma",
    quantity: "Cantidad",
    averageCost: "Costo promedio",
    realized: "Resultado realizado",
    totalGain: "Resultado total",
    ledger: "Operaciones",
    addOperation: "Registrar operación",
    valuation: "Valuación",
    recordValuation: "Registrar valuación",
    account: "Cuenta de origen/destino",
    noAccount: "Sin cuenta vinculada",
    unitPrice: "Precio unitario",
    amount: "Importe total",
    fee: "Comisión",
    date: "Fecha",
    recentOperations: "Historial de operaciones",
    recentValuations: "Historial de valuaciones",
    source: "Origen",
    openingHint: "Al crear una inversión existente, estos importes se guardan como posición y valuación inicial.",
    editHint: "El costo invertido y la valuación se modifican registrando operaciones o valuaciones; no se pisan manualmente.",
  } : {
    symbol: "Symbol / ticker",
    broker: "Broker / platform",
    quantity: "Quantity",
    averageCost: "Average cost",
    realized: "Realized gain",
    totalGain: "Total gain",
    ledger: "Operations",
    addOperation: "Record operation",
    valuation: "Valuation",
    recordValuation: "Record valuation",
    account: "Source/destination account",
    noAccount: "No linked account",
    unitPrice: "Unit price",
    amount: "Total amount",
    fee: "Fee",
    date: "Date",
    recentOperations: "Operation history",
    recentValuations: "Valuation history",
    source: "Source",
    openingHint: "When creating an existing investment, these amounts are stored as the opening position and initial valuation.",
    editHint: "Invested cost and valuation are changed through operations or valuations instead of being overwritten.",
  };

  const load = async () => {
    try {
      setLoading(true);
      const [investmentRows, currencyRows, accountRows] = await Promise.all([
        investmentsApi.list(),
        currenciesApi.list(),
        accountsApi.list(),
      ]);
      setItems(investmentRows);
      setCurrencies(currencyRows);
      setAccounts(accountRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.investments.loadError);
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

  const openEdit = (item: Investment) => {
    setEditing(item);
    setForm({
      name: item.name,
      symbol: item.symbol ?? "",
      broker: item.broker ?? "",
      type: item.type,
      currency_id: item.currency_id,
      invested_amount: item.invested_amount,
      opening_quantity: item.quantity || null,
      current_value: item.current_value,
      expected_return_rate: item.expected_return_rate,
      notes: item.notes ?? "",
    });
    setOpen(true);
  };

  const save = async () => {
    if (editing) {
      await investmentsApi.update(editing.id, {
        name: form.name,
        symbol: form.symbol || null,
        broker: form.broker || null,
        type: form.type,
        currency_id: form.currency_id,
        expected_return_rate: form.expected_return_rate,
        notes: form.notes || null,
      });
    } else {
      await investmentsApi.create({
        ...form,
        symbol: form.symbol || null,
        broker: form.broker || null,
        opening_quantity: form.opening_quantity || null,
        notes: form.notes || null,
      });
    }
    setOpen(false);
    await load();
  };

  const remove = async (id: string) => {
    if (!confirm(t.investments.confirmDelete)) return;
    await investmentsApi.delete(id);
    await load();
  };

  const openLedger = async (item: Investment) => {
    setSelected(item);
    setValuationValue(item.current_value);
    setValuationDate(today());
    setOperationForm({
      type: "buy",
      account_id: null,
      quantity: null,
      unit_price: null,
      amount: 0,
      fee: 0,
      date: today(),
      notes: "",
    });
    const [operationRows, valuationRows] = await Promise.all([
      investmentsApi.listOperations(item.id),
      investmentsApi.listValuations(item.id),
    ]);
    setOperations(operationRows);
    setValuations(valuationRows);
    setLedgerOpen(true);
  };

  const refreshLedger = async (investmentId: string) => {
    const [investment, operationRows, valuationRows] = await Promise.all([
      investmentsApi.get(investmentId),
      investmentsApi.listOperations(investmentId),
      investmentsApi.listValuations(investmentId),
    ]);
    setSelected(investment);
    setOperations(operationRows);
    setValuations(valuationRows);
    await load();
  };

  const addOperation = async () => {
    if (!selected || operationForm.amount <= 0) return;
    await investmentsApi.addOperation(selected.id, {
      ...operationForm,
      account_id: operationForm.account_id || null,
      quantity: operationForm.quantity || null,
      unit_price: operationForm.unit_price || null,
      notes: operationForm.notes || null,
    });
    await refreshLedger(selected.id);
    setOperationForm({ ...operationForm, amount: 0, quantity: null, unit_price: null, fee: 0, notes: "" });
  };

  const addValuation = async () => {
    if (!selected || valuationValue < 0) return;
    await investmentsApi.addValuation(selected.id, {
      value: valuationValue,
      valuation_date: valuationDate,
      source: "manual",
    });
    await refreshLedger(selected.id);
  };

  const typeLabel = (type: InvestmentType) => t.enums[type];
  const operationLabel = (type: InvestmentOperationType) => {
    const es: Record<InvestmentOperationType, string> = {
      opening: "Posición inicial", buy: "Compra", sell: "Venta",
      dividend: "Dividendo", interest: "Interés", fee: "Comisión",
    };
    const en: Record<InvestmentOperationType, string> = {
      opening: "Opening", buy: "Buy", sell: "Sell",
      dividend: "Dividend", interest: "Interest", fee: "Fee",
    };
    return (lang === "es" ? es : en)[type];
  };

  const availableAccounts = selected
    ? accounts.filter((account) => account.currency_id === selected.currency_id)
    : [];

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
          <TableHeader>
            <TableRow>
              <TableHead>{t.common.name}</TableHead>
              <TableHead>{t.common.type}</TableHead>
              <TableHead>{ui.broker}</TableHead>
              <TableHead className="text-right">{ui.quantity}</TableHead>
              <TableHead className="text-right">{t.investments.invested}</TableHead>
              <TableHead className="text-right">{t.investments.currentValue}</TableHead>
              <TableHead className="text-right">{ui.totalGain}</TableHead>
              <TableHead className="text-right">{t.common.actions}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={8}>{t.common.loading}</TableCell></TableRow>
            ) : items.length === 0 ? (
              <TableRow><TableCell colSpan={8}>{t.investments.noInvestments}</TableCell></TableRow>
            ) : items.map((item) => {
              const gain = Number(item.current_value) - Number(item.invested_amount) + Number(item.realized_gain);
              return (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">
                    {item.name}
                    {item.symbol && <span className="ml-2 text-xs text-muted-foreground">{item.symbol}</span>}
                  </TableCell>
                  <TableCell><Badge variant="outline">{typeLabel(item.type)}</Badge></TableCell>
                  <TableCell>{item.broker ?? "-"}</TableCell>
                  <TableCell className="text-right font-mono">{item.quantity || "-"}</TableCell>
                  <TableCell className="text-right font-mono">{formatAmount(item.invested_amount, item.currency, lang)}</TableCell>
                  <TableCell className="text-right font-mono">{formatAmount(item.current_value, item.currency, lang)}</TableCell>
                  <TableCell className={`text-right font-mono ${gain >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                    {formatAmount(gain, item.currency, lang)}
                  </TableCell>
                  <TableCell className="space-x-2 text-right">
                    <Button variant="outline" size="sm" onClick={() => void openLedger(item)}>{ui.ledger}</Button>
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
          <DialogHeader><DialogTitle>{editing ? t.investments.editDialog : t.investments.addDialog}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <Field label={t.common.name}><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
              <Field label={ui.symbol}><Input value={form.symbol ?? ""} onChange={(e) => setForm({ ...form, symbol: e.target.value })} /></Field>
            </div>
            <div className="grid grid-cols-3 gap-4">
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
              <Field label={ui.broker}><Input value={form.broker ?? ""} onChange={(e) => setForm({ ...form, broker: e.target.value })} /></Field>
            </div>
            {!editing ? (
              <>
                <p className="text-xs text-muted-foreground">{ui.openingHint}</p>
                <div className="grid grid-cols-4 gap-4">
                  <Field label={t.investments.invested}><Input type="number" min="0" step="0.01" value={form.invested_amount || ""} onChange={(e) => setForm({ ...form, invested_amount: parseFloat(e.target.value) || 0 })} /></Field>
                  <Field label={ui.quantity}><Input type="number" min="0" step="0.00000001" value={form.opening_quantity ?? ""} onChange={(e) => setForm({ ...form, opening_quantity: e.target.value ? parseFloat(e.target.value) : null })} /></Field>
                  <Field label={t.investments.currentValue}><Input type="number" min="0" step="0.01" value={form.current_value || ""} onChange={(e) => setForm({ ...form, current_value: parseFloat(e.target.value) || 0 })} /></Field>
                  <Field label={t.investments.expectedRate}><Input type="number" step="0.01" value={form.expected_return_rate ?? ""} onChange={(e) => setForm({ ...form, expected_return_rate: e.target.value ? parseFloat(e.target.value) : null })} /></Field>
                </div>
              </>
            ) : (
              <>
                <p className="text-xs text-muted-foreground">{ui.editHint}</p>
                <Field label={t.investments.expectedRate}><Input type="number" step="0.01" value={form.expected_return_rate ?? ""} onChange={(e) => setForm({ ...form, expected_return_rate: e.target.value ? parseFloat(e.target.value) : null })} /></Field>
              </>
            )}
            <Field label={t.common.notes}><Input value={form.notes ?? ""} onChange={(e) => setForm({ ...form, notes: e.target.value })} /></Field>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>{t.common.cancel}</Button>
            <Button onClick={() => void save()} disabled={!form.name || !form.currency_id}>{t.common.save}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={ledgerOpen} onOpenChange={setLedgerOpen}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>{selected?.name} · {ui.ledger}</DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="max-h-[75vh] space-y-6 overflow-y-auto py-2 pr-1">
              <div className="grid grid-cols-4 gap-3 rounded-lg border p-4 text-sm">
                <Metric label={ui.quantity} value={String(selected.quantity)} />
                <Metric label={ui.averageCost} value={selected.average_cost == null ? "-" : formatAmount(selected.average_cost, selected.currency, lang)} />
                <Metric label={ui.realized} value={formatAmount(selected.realized_gain, selected.currency, lang)} />
                <Metric label={ui.valuation} value={formatAmount(selected.current_value, selected.currency, lang)} />
              </div>

              <div className="space-y-3 rounded-lg border p-4">
                <h3 className="font-medium">{ui.addOperation}</h3>
                <div className="grid grid-cols-3 gap-3">
                  <Field label={t.common.type}>
                    <Select value={operationForm.type} onValueChange={(v) => setOperationForm({ ...operationForm, type: (v ?? "buy") as InvestmentOperationType })}>
                      <SelectTrigger><span className="text-sm">{operationLabel(operationForm.type)}</span></SelectTrigger>
                      <SelectContent>{OPERATION_TYPES.map((type) => <SelectItem key={type} value={type}>{operationLabel(type)}</SelectItem>)}</SelectContent>
                    </Select>
                  </Field>
                  <Field label={ui.account}>
                    <Select value={operationForm.account_id ?? "none"} onValueChange={(v) => setOperationForm({ ...operationForm, account_id: !v || v === "none" ? null : v })}>
                      <SelectTrigger><span className="text-sm">{availableAccounts.find((a) => a.id === operationForm.account_id)?.name ?? ui.noAccount}</span></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">{ui.noAccount}</SelectItem>
                        {availableAccounts.map((account) => <SelectItem key={account.id} value={account.id}>{account.name}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </Field>
                  <Field label={ui.date}><Input type="date" value={operationForm.date} onChange={(e) => setOperationForm({ ...operationForm, date: e.target.value })} /></Field>
                  <Field label={ui.quantity}><Input type="number" min="0" step="0.00000001" value={operationForm.quantity ?? ""} onChange={(e) => setOperationForm({ ...operationForm, quantity: e.target.value ? parseFloat(e.target.value) : null })} /></Field>
                  <Field label={ui.unitPrice}><Input type="number" min="0" step="0.00000001" value={operationForm.unit_price ?? ""} onChange={(e) => setOperationForm({ ...operationForm, unit_price: e.target.value ? parseFloat(e.target.value) : null })} /></Field>
                  <Field label={ui.amount}><Input type="number" min="0" step="0.01" value={operationForm.amount || ""} onChange={(e) => setOperationForm({ ...operationForm, amount: parseFloat(e.target.value) || 0 })} /></Field>
                  <Field label={ui.fee}><Input type="number" min="0" step="0.01" value={operationForm.fee || ""} onChange={(e) => setOperationForm({ ...operationForm, fee: parseFloat(e.target.value) || 0 })} /></Field>
                  <div className="col-span-2"><Field label={t.common.notes}><Input value={operationForm.notes ?? ""} onChange={(e) => setOperationForm({ ...operationForm, notes: e.target.value })} /></Field></div>
                </div>
                <Button onClick={() => void addOperation()} disabled={operationForm.amount <= 0}>{ui.addOperation}</Button>
              </div>

              <div className="space-y-3 rounded-lg border p-4">
                <h3 className="font-medium">{ui.recordValuation}</h3>
                <div className="grid grid-cols-3 gap-3">
                  <Field label={ui.valuation}><Input type="number" min="0" step="0.01" value={valuationValue} onChange={(e) => setValuationValue(parseFloat(e.target.value) || 0)} /></Field>
                  <Field label={ui.date}><Input type="date" value={valuationDate} onChange={(e) => setValuationDate(e.target.value)} /></Field>
                  <div className="flex items-end"><Button className="w-full" onClick={() => void addValuation()}>{ui.recordValuation}</Button></div>
                </div>
              </div>

              <div>
                <h3 className="mb-2 font-medium">{ui.recentOperations}</h3>
                <div className="rounded-lg border">
                  <Table>
                    <TableHeader><TableRow><TableHead>{ui.date}</TableHead><TableHead>{t.common.type}</TableHead><TableHead className="text-right">{ui.quantity}</TableHead><TableHead className="text-right">{ui.amount}</TableHead><TableHead className="text-right">{ui.fee}</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {operations.map((operation) => (
                        <TableRow key={operation.id}>
                          <TableCell>{operation.date}</TableCell>
                          <TableCell>{operationLabel(operation.type)}</TableCell>
                          <TableCell className="text-right font-mono">{operation.quantity ?? "-"}</TableCell>
                          <TableCell className="text-right font-mono">{formatAmount(operation.amount, selected.currency, lang)}</TableCell>
                          <TableCell className="text-right font-mono">{formatAmount(operation.fee, selected.currency, lang)}</TableCell>
                        </TableRow>
                      ))}
                      {operations.length === 0 && <TableRow><TableCell colSpan={5}>-</TableCell></TableRow>}
                    </TableBody>
                  </Table>
                </div>
              </div>

              <div>
                <h3 className="mb-2 font-medium">{ui.recentValuations}</h3>
                <div className="rounded-lg border">
                  <Table>
                    <TableHeader><TableRow><TableHead>{ui.date}</TableHead><TableHead className="text-right">{ui.valuation}</TableHead><TableHead>{ui.source}</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {valuations.map((valuation) => (
                        <TableRow key={valuation.id}>
                          <TableCell>{valuation.valuation_date}</TableCell>
                          <TableCell className="text-right font-mono">{formatAmount(valuation.value, selected.currency, lang)}</TableCell>
                          <TableCell>{valuation.source}</TableCell>
                        </TableRow>
                      ))}
                      {valuations.length === 0 && <TableRow><TableCell colSpan={3}>-</TableCell></TableRow>}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><div className="text-xs text-muted-foreground">{label}</div><div className="mt-1 font-mono">{value}</div></div>;
}
