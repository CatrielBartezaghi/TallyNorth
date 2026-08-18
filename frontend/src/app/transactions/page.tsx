"use client";

import { useEffect, useMemo, useState } from "react";
import {
  accountsApi,
  categoriesApi,
  creditCardsApi,
  purchasesApi,
  transactionsApi,
  type Account,
  type Category,
  type CreditCard,
  type Purchase,
  type RecurrenceRule,
  type Transaction,
  type TransactionType,
} from "@/lib/api";
import {
  recurringEntriesApi,
  type RecurringEntry,
  type RecurringEntryPayload,
} from "@/lib/recurring-api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { useLanguage } from "@/lib/LanguageContext";
import type { Language } from "@/lib/translations";

const today = () => new Date().toISOString().slice(0, 10);

type DestinationValue = `account:${string}` | `credit_card:${string}` | "";
type EditingMovement =
  | { kind: "account"; item: Transaction }
  | { kind: "card"; item: Purchase }
  | null;

type UnifiedMovement =
  | {
      kind: "account";
      id: string;
      date: string;
      createdAt: string;
      type: TransactionType;
      description: string;
      categoryId: string | null;
      category: string | null;
      amount: number;
      destinationName: string;
      destinationType: "account";
      symbol?: string;
      item: Transaction;
    }
  | {
      kind: "card";
      id: string;
      date: string;
      createdAt: string;
      type: "expense";
      description: string;
      categoryId: string | null;
      category: string | null;
      amount: number;
      destinationName: string;
      destinationType: "credit_card";
      symbol?: string;
      installments: number;
      firstInstallmentDate: string;
      item: Purchase;
    };

interface MovementForm {
  destination: DestinationValue;
  type: TransactionType;
  amount: number;
  description: string;
  category_id: string;
  date: string;
  installments: number;
}

interface RecurringForm {
  type: TransactionType;
  amount: number;
  description: string;
  category_id: string;
  frequency: RecurrenceRule;
  start_date: string;
  end_date: string;
  active: boolean;
  destination: DestinationValue;
}

const EMPTY_MOVEMENT: MovementForm = {
  destination: "",
  type: "expense",
  amount: 0,
  description: "",
  category_id: "",
  date: today(),
  installments: 1,
};

const EMPTY_RECURRING: RecurringForm = {
  type: "expense",
  amount: 0,
  description: "",
  category_id: "",
  frequency: "monthly",
  start_date: today(),
  end_date: "",
  active: true,
  destination: "",
};

const TYPE_COLORS: Record<TransactionType, string> = {
  income: "text-emerald-400 border-emerald-400/40",
  expense: "text-red-400 border-red-400/40",
};

function localeFor(lang: Language) {
  return lang === "es" ? "es-AR" : "en-US";
}

function formatDate(value: string, lang: Language) {
  return new Date(`${value}T00:00:00`).toLocaleDateString(localeFor(lang));
}

function formatAmount(amount: number, lang: Language, symbol?: string) {
  const value = amount.toLocaleString(localeFor(lang), { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return symbol ? `${symbol} ${value}` : value;
}

export default function TransactionsPage() {
  const { lang, t } = useLanguage();
  const es = lang === "es";

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [recurring, setRecurring] = useState<RecurringEntry[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [movementOpen, setMovementOpen] = useState(false);
  const [editingMovement, setEditingMovement] = useState<EditingMovement>(null);
  const [movementForm, setMovementForm] = useState<MovementForm>(EMPTY_MOVEMENT);

  const [recurringOpen, setRecurringOpen] = useState(false);
  const [editingRecurring, setEditingRecurring] = useState<RecurringEntry | null>(null);
  const [recurringForm, setRecurringForm] = useState<RecurringForm>(EMPTY_RECURRING);
  const [saving, setSaving] = useState(false);

  const accountMap = useMemo(() => new Map(accounts.map((item) => [item.id, item])), [accounts]);
  const cardMap = useMemo(() => new Map(cards.map((item) => [item.id, item])), [cards]);
  const categoryMap = useMemo(() => new Map(categories.map((item) => [item.id, item])), [categories]);

  const movements = useMemo<UnifiedMovement[]>(() => {
    const accountMovements: UnifiedMovement[] = transactions.map((transaction) => {
      const account = accountMap.get(transaction.account_id);
      return {
        kind: "account",
        id: transaction.id,
        date: transaction.date,
        createdAt: transaction.created_at,
        type: transaction.type,
        description: transaction.description,
        categoryId: transaction.category_id,
        category: transaction.category,
        amount: transaction.amount,
        destinationName: account?.name ?? t.transactions.unknownAccount,
        destinationType: "account",
        symbol: account?.currency.symbol,
        item: transaction,
      };
    });

    const cardMovements: UnifiedMovement[] = purchases.map((purchase) => {
      const card = cardMap.get(purchase.credit_card_id);
      return {
        kind: "card",
        id: purchase.id,
        date: purchase.purchase_date,
        createdAt: purchase.created_at,
        type: "expense",
        description: purchase.description,
        categoryId: purchase.category_id,
        category: purchase.category,
        amount: purchase.total_amount,
        destinationName: card?.name ?? (es ? "Tarjeta desconocida" : "Unknown card"),
        destinationType: "credit_card",
        symbol: card?.currency.symbol,
        installments: purchase.installments,
        firstInstallmentDate: purchase.first_installment_date,
        item: purchase,
      };
    });

    return [...accountMovements, ...cardMovements].sort((a, b) =>
      b.date.localeCompare(a.date) || b.createdAt.localeCompare(a.createdAt)
    );
  }, [transactions, purchases, accountMap, cardMap, es, t.transactions.unknownAccount]);

  const load = async () => {
    try {
      setLoading(true);
      const [transactionRows, purchaseRows, recurringRows, accountRows, cardRows, categoryRows] = await Promise.all([
        transactionsApi.list(),
        purchasesApi.list(),
        recurringEntriesApi.list(),
        accountsApi.list(),
        creditCardsApi.list(),
        categoriesApi.list(),
      ]);
      setTransactions(transactionRows);
      setPurchases(purchaseRows);
      setRecurring(recurringRows);
      setAccounts(accountRows);
      setCards(cardRows);
      setCategories(categoryRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.common.errorLoadingData);
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { void load(); }, []);

  const categoryOptions = (type: TransactionType) =>
    categories.filter((category) => category.type === type || category.type === "both");

  const defaultDestination = (type: TransactionType): DestinationValue => {
    if (accounts[0]) return `account:${accounts[0].id}`;
    if (type === "expense" && cards[0]) return `credit_card:${cards[0].id}`;
    return "";
  };

  const destinationLabel = (destination: DestinationValue) => {
    if (!destination) return es ? "Seleccionar destino" : "Select destination";
    if (destination.startsWith("account:")) {
      return `${es ? "Cuenta" : "Account"} · ${accountMap.get(destination.slice(8))?.name ?? "-"}`;
    }
    return `${es ? "Tarjeta" : "Card"} · ${cardMap.get(destination.slice(12))?.name ?? "-"}`;
  };

  const openMovementCreate = () => {
    setEditingMovement(null);
    setMovementForm({ ...EMPTY_MOVEMENT, destination: defaultDestination("expense"), date: today() });
    setMovementOpen(true);
  };

  const openMovementEdit = (movement: UnifiedMovement) => {
    if (movement.kind === "account") {
      setEditingMovement({ kind: "account", item: movement.item });
      setMovementForm({
        destination: `account:${movement.item.account_id}`,
        type: movement.item.type,
        amount: movement.item.amount,
        description: movement.item.description,
        category_id: movement.item.category_id ?? "",
        date: movement.item.date,
        installments: 1,
      });
    } else {
      setEditingMovement({ kind: "card", item: movement.item });
      setMovementForm({
        destination: `credit_card:${movement.item.credit_card_id}`,
        type: "expense",
        amount: movement.item.total_amount,
        description: movement.item.description,
        category_id: movement.item.category_id ?? "",
        date: movement.item.purchase_date,
        installments: movement.item.installments,
      });
    }
    setMovementOpen(true);
  };

  const saveMovement = async () => {
    if (!movementForm.destination) return;
    setSaving(true);
    try {
      const [destinationType, destinationId] = movementForm.destination.split(":") as ["account" | "credit_card", string];
      const selectedCategory = movementForm.category_id ? categoryMap.get(movementForm.category_id) : undefined;

      if (destinationType === "account") {
        if (editingMovement?.kind === "card") throw new Error(es ? "No se puede convertir una compra de tarjeta en movimiento de cuenta desde esta edición." : "A card purchase cannot be converted into an account movement from this editor.");
        const payload = {
          account_id: destinationId,
          type: movementForm.type,
          amount: movementForm.amount,
          description: movementForm.description,
          category_id: movementForm.category_id || null,
          category: selectedCategory?.name ?? null,
          date: movementForm.date,
        };
        if (editingMovement) await transactionsApi.update(editingMovement.item.id, payload);
        else await transactionsApi.create(payload);
      } else {
        if (editingMovement?.kind === "account") throw new Error(es ? "No se puede convertir un movimiento de cuenta en compra de tarjeta desde esta edición." : "An account movement cannot be converted into a card purchase from this editor.");
        const payload = {
          credit_card_id: destinationId,
          description: movementForm.description,
          total_amount: movementForm.amount,
          installments: Math.max(1, Math.trunc(movementForm.installments || 1)),
          purchase_date: movementForm.date,
          category_id: movementForm.category_id || null,
          category: selectedCategory?.name ?? null,
        };
        if (editingMovement) await purchasesApi.update(editingMovement.item.id, payload);
        else await purchasesApi.create(payload);
      }

      setMovementOpen(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.transactions.saveError);
    } finally {
      setSaving(false);
    }
  };

  const deleteMovement = async (movement: UnifiedMovement) => {
    if (!confirm(es ? "¿Eliminar este movimiento?" : "Delete this movement?")) return;
    try {
      if (movement.kind === "account") await transactionsApi.delete(movement.id);
      else await purchasesApi.delete(movement.id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.transactions.deleteError);
    }
  };

  const openRecurringCreate = () => {
    setEditingRecurring(null);
    setRecurringForm({ ...EMPTY_RECURRING, start_date: today(), destination: defaultDestination("expense") });
    setRecurringOpen(true);
  };

  const openRecurringEdit = (entry: RecurringEntry) => {
    setEditingRecurring(entry);
    const destination: DestinationValue = entry.destination_type === "account"
      ? `account:${entry.account_id}`
      : `credit_card:${entry.credit_card_id}`;
    setRecurringForm({
      type: entry.type,
      amount: entry.amount,
      description: entry.description,
      category_id: entry.category_id ?? "",
      frequency: entry.frequency,
      start_date: entry.start_date,
      end_date: entry.end_date ?? "",
      active: entry.active,
      destination,
    });
    setRecurringOpen(true);
  };

  const saveRecurring = async () => {
    if (!recurringForm.destination) return;
    setSaving(true);
    try {
      const [destinationType, destinationId] = recurringForm.destination.split(":") as ["account" | "credit_card", string];
      const payload: RecurringEntryPayload = {
        type: recurringForm.type,
        amount: recurringForm.amount,
        description: recurringForm.description,
        category_id: recurringForm.category_id || null,
        frequency: recurringForm.frequency,
        start_date: recurringForm.start_date,
        end_date: recurringForm.end_date || null,
        active: recurringForm.active,
        destination_type: destinationType,
        account_id: destinationType === "account" ? destinationId : null,
        credit_card_id: destinationType === "credit_card" ? destinationId : null,
      };
      if (editingRecurring) await recurringEntriesApi.update(editingRecurring.id, payload);
      else await recurringEntriesApi.create(payload);
      setRecurringOpen(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : (es ? "No se pudo guardar el recurrente" : "Failed to save recurring entry"));
    } finally {
      setSaving(false);
    }
  };

  const deleteRecurring = async (id: string) => {
    if (!confirm(es ? "¿Eliminar este recurrente? Los movimientos ya generados se conservan." : "Delete this recurring entry? Existing generated movements are kept.")) return;
    try {
      await recurringEntriesApi.delete(id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : (es ? "No se pudo eliminar" : "Delete failed"));
    }
  };

  const recurringDestinationName = (entry: RecurringEntry) => {
    if (entry.destination_type === "account") return accountMap.get(entry.account_id ?? "")?.name ?? "-";
    return cardMap.get(entry.credit_card_id ?? "")?.name ?? "-";
  };

  const recurringSymbol = (entry: RecurringEntry) => {
    if (entry.destination_type === "account") return accountMap.get(entry.account_id ?? "")?.currency.symbol;
    return cardMap.get(entry.credit_card_id ?? "")?.currency.symbol;
  };

  const movementDestinationIsCard = movementForm.destination.startsWith("credit_card:");
  const canChooseAccounts = editingMovement?.kind !== "card";
  const canChooseCards = editingMovement?.kind !== "account" && movementForm.type === "expense";

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.transactions.title}</h1>
          <p className="mt-1 text-muted-foreground">
            {es ? "Cuentas, tarjetas y reglas recurrentes en un solo lugar." : "Accounts, cards, and recurring rules in one place."}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={openRecurringCreate} disabled={accounts.length === 0 && cards.length === 0}>
            {es ? "+ Agregar recurrente" : "+ Add recurring"}
          </Button>
          <Button onClick={openMovementCreate} disabled={accounts.length === 0 && cards.length === 0}>
            {t.transactions.add}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>
      )}

      <section className="space-y-3">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">{es ? "Recurrentes" : "Recurring"}</h2>
            <p className="text-sm text-muted-foreground">
              {es ? "La frecuencia es independiente del destino: cuenta o tarjeta." : "Frequency is independent from destination: account or card."}
            </p>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">{t.common.loading}</p>
        ) : recurring.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
            {es ? "Todavía no hay reglas recurrentes." : "No recurring rules yet."}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t.common.description}</TableHead>
                  <TableHead>{t.common.type}</TableHead>
                  <TableHead>{es ? "Destino" : "Destination"}</TableHead>
                  <TableHead>{t.transactions.frequency}</TableHead>
                  <TableHead>{es ? "Inicio" : "Starts"}</TableHead>
                  <TableHead>{es ? "Estado" : "Status"}</TableHead>
                  <TableHead className="text-right">{t.common.amount}</TableHead>
                  <TableHead className="text-right">{t.common.actions}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recurring.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="font-medium">{entry.description}</TableCell>
                    <TableCell><Badge variant="outline" className={TYPE_COLORS[entry.type]}>{t.enums[entry.type]}</Badge></TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span>{recurringDestinationName(entry)}</span>
                        <span className="text-xs text-muted-foreground">{entry.destination_type === "account" ? (es ? "Cuenta" : "Account") : (es ? "Tarjeta" : "Card")}</span>
                      </div>
                    </TableCell>
                    <TableCell>{t.enums[entry.frequency]}</TableCell>
                    <TableCell>{formatDate(entry.start_date, lang)}</TableCell>
                    <TableCell><Badge variant={entry.active ? "outline" : "secondary"}>{entry.active ? t.common.active : t.common.inactive}</Badge></TableCell>
                    <TableCell className={`text-right font-mono ${entry.type === "income" ? "text-emerald-400" : "text-red-400"}`}>
                      {entry.type === "income" ? "+" : "-"}{formatAmount(entry.amount, lang, recurringSymbol(entry))}
                    </TableCell>
                    <TableCell className="space-x-1 text-right">
                      <Button variant="ghost" size="sm" onClick={() => openRecurringEdit(entry)}>{t.common.edit}</Button>
                      <Button variant="ghost" size="sm" className="text-red-400" onClick={() => deleteRecurring(entry.id)}>{t.common.delete}</Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="text-xl font-semibold">{es ? "Movimientos" : "Movements"}</h2>
          <p className="text-sm text-muted-foreground">
            {es ? "Los gastos de cuenta impactan el saldo al instante; los consumos de tarjeta generan deuda y se descuentan de la cuenta de pago al vencimiento." : "Account expenses affect cash immediately; card purchases create debt and affect the payment account at the due date."}
          </p>
        </div>

        {!loading && movements.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">{t.transactions.noTransactions}</div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t.common.date}</TableHead>
                  <TableHead>{es ? "Destino" : "Destination"}</TableHead>
                  <TableHead>{t.common.type}</TableHead>
                  <TableHead>{t.common.description}</TableHead>
                  <TableHead>{t.common.category}</TableHead>
                  <TableHead className="text-right">{t.common.amount}</TableHead>
                  <TableHead className="text-right">{t.common.actions}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {movements.map((movement) => (
                  <TableRow key={`${movement.kind}:${movement.id}`}>
                    <TableCell>{formatDate(movement.date, lang)}</TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span>{movement.destinationName}</span>
                        <span className="text-xs text-muted-foreground">
                          {movement.destinationType === "account"
                            ? (es ? "Cuenta" : "Account")
                            : `${es ? "Tarjeta" : "Card"}${movement.installments > 1 ? ` · ${movement.installments} ${es ? "cuotas" : "installments"}` : ""}`}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell><Badge variant="outline" className={TYPE_COLORS[movement.type]}>{t.enums[movement.type]}</Badge></TableCell>
                    <TableCell className="font-medium">{movement.description}</TableCell>
                    <TableCell className="text-muted-foreground">{movement.categoryId ? categoryMap.get(movement.categoryId)?.name : (movement.category ?? "-")}</TableCell>
                    <TableCell className={`text-right font-mono ${movement.type === "income" ? "text-emerald-400" : "text-red-400"}`}>
                      {movement.type === "income" ? "+" : "-"}{formatAmount(movement.amount, lang, movement.symbol)}
                    </TableCell>
                    <TableCell className="space-x-1 text-right">
                      <Button variant="ghost" size="sm" onClick={() => openMovementEdit(movement)}>{t.common.edit}</Button>
                      <Button variant="ghost" size="sm" className="text-red-400" onClick={() => deleteMovement(movement)}>{t.common.delete}</Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>

      <Dialog open={movementOpen} onOpenChange={setMovementOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editingMovement ? t.transactions.editDialog : t.transactions.addDialog}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>{es ? "Destino" : "Destination"}</Label>
                <Select value={movementForm.destination} onValueChange={(v) => {
                  const destination = (v ?? "") as DestinationValue;
                  const type: TransactionType = destination.startsWith("credit_card:") ? "expense" : movementForm.type;
                  setMovementForm({ ...movementForm, destination, type, category_id: type === movementForm.type ? movementForm.category_id : "" });
                }}>
                  <SelectTrigger><span className="truncate text-sm">{destinationLabel(movementForm.destination)}</span></SelectTrigger>
                  <SelectContent>
                    {canChooseAccounts && accounts.map((account) => <SelectItem key={`account:${account.id}`} value={`account:${account.id}`}>{es ? "Cuenta" : "Account"} · {account.name}</SelectItem>)}
                    {canChooseCards && cards.map((card) => <SelectItem key={`credit_card:${card.id}`} value={`credit_card:${card.id}`}>{es ? "Tarjeta" : "Card"} · {card.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>{t.common.type}</Label>
                <Select value={movementForm.type} disabled={movementDestinationIsCard || editingMovement?.kind === "card"} onValueChange={(v) => {
                  const type = (v ?? "expense") as TransactionType;
                  const destination = type === "income" && movementForm.destination.startsWith("credit_card:") ? defaultDestination("income") : movementForm.destination;
                  setMovementForm({ ...movementForm, type, destination, category_id: "" });
                }}>
                  <SelectTrigger><span className="text-sm">{t.enums[movementForm.type]}</span></SelectTrigger>
                  <SelectContent><SelectItem value="income">{t.enums.income}</SelectItem><SelectItem value="expense">{t.enums.expense}</SelectItem></SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5"><Label>{t.common.amount}</Label><Input type="number" min="0" step="0.01" value={movementForm.amount || ""} onChange={(e) => setMovementForm({ ...movementForm, amount: Number(e.target.value) })} /></div>
              <div className="space-y-1.5"><Label>{t.common.date}</Label><Input type="date" value={movementForm.date} onChange={(e) => setMovementForm({ ...movementForm, date: e.target.value })} /></div>
            </div>
            <div className="space-y-1.5"><Label>{t.common.description}</Label><Input value={movementForm.description} onChange={(e) => setMovementForm({ ...movementForm, description: e.target.value })} /></div>
            <div className={movementDestinationIsCard ? "grid grid-cols-2 gap-4" : "space-y-1.5"}>
              <div className="space-y-1.5">
                <Label>{t.common.category}</Label>
                <Select value={movementForm.category_id} onValueChange={(v) => setMovementForm({ ...movementForm, category_id: v ?? "" })}>
                  <SelectTrigger><span className="truncate text-sm">{movementForm.category_id ? categoryMap.get(movementForm.category_id)?.name : t.common.none}</span></SelectTrigger>
                  <SelectContent><SelectItem value="">{t.common.none}</SelectItem>{categoryOptions(movementForm.type).map((category) => <SelectItem key={category.id} value={category.id}>{category.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              {movementDestinationIsCard && (
                <div className="space-y-1.5">
                  <Label>{es ? "Cuotas" : "Installments"}</Label>
                  <Input type="number" min="1" step="1" value={movementForm.installments || 1} onChange={(e) => setMovementForm({ ...movementForm, installments: Math.max(1, Number(e.target.value)) })} />
                </div>
              )}
            </div>
            {movementDestinationIsCard && (
              <p className="rounded-md border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                {es ? "Este gasto se registra como consumo de tarjeta. No descuenta saldo de una cuenta ahora; las cuotas impactan la cuenta de pago al vencimiento." : "This expense is recorded as a card purchase. It does not reduce an account balance now; installments affect the payment account at their due dates."}
              </p>
            )}
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setMovementOpen(false)}>{t.common.cancel}</Button><Button onClick={saveMovement} disabled={saving || !movementForm.destination || !movementForm.description || !movementForm.date || movementForm.amount <= 0 || (movementDestinationIsCard && movementForm.installments < 1)}>{saving ? t.common.saving : t.common.save}</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={recurringOpen} onOpenChange={setRecurringOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editingRecurring ? (es ? "Editar recurrente" : "Edit recurring") : (es ? "Agregar recurrente" : "Add recurring")}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>{t.common.type}</Label>
                <Select value={recurringForm.type} onValueChange={(v) => {
                  const type = (v ?? "expense") as TransactionType;
                  const destination = type === "income" && recurringForm.destination.startsWith("credit_card:") ? defaultDestination("income") : recurringForm.destination;
                  setRecurringForm({ ...recurringForm, type, destination, category_id: "" });
                }}>
                  <SelectTrigger><span className="text-sm">{t.enums[recurringForm.type]}</span></SelectTrigger>
                  <SelectContent><SelectItem value="income">{t.enums.income}</SelectItem><SelectItem value="expense">{t.enums.expense}</SelectItem></SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>{es ? "Destino" : "Destination"}</Label>
                <Select value={recurringForm.destination} onValueChange={(v) => setRecurringForm({ ...recurringForm, destination: (v ?? "") as DestinationValue })}>
                  <SelectTrigger><span className="truncate text-sm">{destinationLabel(recurringForm.destination)}</span></SelectTrigger>
                  <SelectContent>
                    {accounts.map((account) => <SelectItem key={`account:${account.id}`} value={`account:${account.id}`}>{es ? "Cuenta" : "Account"} · {account.name}</SelectItem>)}
                    {recurringForm.type === "expense" && cards.map((card) => <SelectItem key={`credit_card:${card.id}`} value={`credit_card:${card.id}`}>{es ? "Tarjeta" : "Card"} · {card.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5"><Label>{t.common.amount}</Label><Input type="number" min="0" step="0.01" value={recurringForm.amount || ""} onChange={(e) => setRecurringForm({ ...recurringForm, amount: Number(e.target.value) })} /></div>
              <div className="space-y-1.5">
                <Label>{t.transactions.frequency}</Label>
                <Select value={recurringForm.frequency} onValueChange={(v) => setRecurringForm({ ...recurringForm, frequency: (v ?? "monthly") as RecurrenceRule })}>
                  <SelectTrigger><span className="text-sm">{t.enums[recurringForm.frequency]}</span></SelectTrigger>
                  <SelectContent><SelectItem value="weekly">{t.enums.weekly}</SelectItem><SelectItem value="monthly">{t.enums.monthly}</SelectItem><SelectItem value="yearly">{t.enums.yearly}</SelectItem></SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5"><Label>{t.common.description}</Label><Input value={recurringForm.description} onChange={(e) => setRecurringForm({ ...recurringForm, description: e.target.value })} /></div>
            <div className="space-y-1.5">
              <Label>{t.common.category}</Label>
              <Select value={recurringForm.category_id} onValueChange={(v) => setRecurringForm({ ...recurringForm, category_id: v ?? "" })}>
                <SelectTrigger><span className="truncate text-sm">{recurringForm.category_id ? categoryMap.get(recurringForm.category_id)?.name : t.common.none}</span></SelectTrigger>
                <SelectContent><SelectItem value="">{t.common.none}</SelectItem>{categoryOptions(recurringForm.type).map((category) => <SelectItem key={category.id} value={category.id}>{category.name}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5"><Label>{es ? "Fecha de inicio" : "Start date"}</Label><Input type="date" value={recurringForm.start_date} onChange={(e) => setRecurringForm({ ...recurringForm, start_date: e.target.value })} /></div>
              <div className="space-y-1.5"><Label>{t.transactions.endDate}</Label><Input type="date" value={recurringForm.end_date} onChange={(e) => setRecurringForm({ ...recurringForm, end_date: e.target.value })} /></div>
            </div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={recurringForm.active} onChange={(e) => setRecurringForm({ ...recurringForm, active: e.target.checked })} />{es ? "Activo" : "Active"}</label>
            {recurringForm.destination.startsWith("credit_card:") && (
              <p className="rounded-md border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                {es ? "El gasto se registra en la tarjeta en cada ocurrencia y afecta la cuenta de pago recién al vencimiento del resumen." : "The expense is registered on the card at each occurrence and affects its payment account only on the statement due date."}
              </p>
            )}
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => setRecurringOpen(false)}>{t.common.cancel}</Button><Button onClick={saveRecurring} disabled={saving || !recurringForm.destination || !recurringForm.description || !recurringForm.start_date || recurringForm.amount <= 0}>{saving ? t.common.saving : t.common.save}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
