"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  accountsApi,
  categoriesApi,
  transactionsApi,
  type Account,
  type Category,
  type RecurrenceRule,
  type Transaction,
  type TransactionType,
} from "@/lib/api";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger,
} from "@/components/ui/select";
import { useLanguage } from "@/lib/LanguageContext";
import type { Language } from "@/lib/translations";

interface TransactionForm {
  account_id: string;
  type: TransactionType;
  amount: number;
  description: string;
  category_id: string;
  date: string;
  is_recurring: boolean;
  recurrence_rule: RecurrenceRule;
  end_date: string;
}

interface TransactionFilters {
  account_id: string;
  type: "all" | TransactionType;
  date_from: string;
  date_to: string;
}

const today = () => new Date().toISOString().slice(0, 10);

const EMPTY_FORM: TransactionForm = {
  account_id: "",
  type: "expense",
  amount: 0,
  description: "",
  category_id: "",
  date: today(),
  is_recurring: false,
  recurrence_rule: "monthly",
  end_date: "",
};

const EMPTY_FILTERS: TransactionFilters = {
  account_id: "",
  type: "all",
  date_from: "",
  date_to: "",
};

const TYPE_COLORS: Record<TransactionType, string> = {
  income: "text-emerald-400 border-emerald-400/40",
  expense: "text-red-400 border-red-400/40",
};

function localeFor(lang: Language) {
  return lang === "es" ? "es-AR" : "en-US";
}

function formatAmount(amount: number, lang: Language, account?: Account) {
  if (!account) return amount.toLocaleString(localeFor(lang), { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${account.currency.symbol} ${amount.toLocaleString(localeFor(lang), {
    minimumFractionDigits: account.currency.decimal_places,
    maximumFractionDigits: account.currency.decimal_places,
  })}`;
}

function formatDate(value: string, lang: Language) {
  return new Date(`${value}T00:00:00`).toLocaleDateString(localeFor(lang));
}

export default function TransactionsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [filters, setFilters] = useState<TransactionFilters>(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Transaction | null>(null);
  const [form, setForm] = useState<TransactionForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const { lang, t } = useLanguage();

  const accountMap = useMemo(
    () => new Map(accounts.map((account) => [account.id, account])),
    [accounts],
  );

  const categoryMap = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  );

  const load = async (showLoading = true, nextFilters = filters) => {
    try {
      if (showLoading) setLoading(true);
      const params = {
        account_id: nextFilters.account_id || undefined,
        type: nextFilters.type === "all" ? undefined : nextFilters.type,
        date_from: nextFilters.date_from || undefined,
        date_to: nextFilters.date_to || undefined,
      };
      const [transactionRows, accountRows, categoryRows] = await Promise.all([
        transactionsApi.list(params),
        accountsApi.list(),
        categoriesApi.list(),
      ]);
      setTransactions(transactionRows);
      setAccounts(accountRows);
      setCategories(categoryRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.common.errorLoadingData);
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { void load(false); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, account_id: accounts[0]?.id ?? "", date: today() });
    setDialogOpen(true);
  };

  const openEdit = (transaction: Transaction) => {
    setEditing(transaction);
    setForm({
      account_id: transaction.account_id,
      type: transaction.type,
      amount: transaction.amount,
      description: transaction.description,
      category_id: transaction.category_id ?? "",
      date: transaction.date,
      is_recurring: transaction.is_recurring,
      recurrence_rule: transaction.recurrence_rule ?? "monthly",
      end_date: transaction.end_date ?? "",
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {
        account_id: form.account_id,
        type: form.type,
        amount: form.amount,
        description: form.description,
        category_id: form.category_id || null,
        date: form.date,
        is_recurring: form.is_recurring,
        recurrence_rule: form.is_recurring ? form.recurrence_rule : null,
        end_date: form.is_recurring && form.end_date ? form.end_date : null,
      };
      if (editing) {
        await transactionsApi.update(editing.id, payload);
      } else {
        await transactionsApi.create(payload);
      }
      setDialogOpen(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.transactions.saveError);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t.transactions.confirmDelete)) return;
    try {
      await transactionsApi.delete(id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.transactions.deleteError);
    }
  };

  const applyFilters = async () => {
    await load(true, filters);
  };

  const clearFilters = async () => {
    setFilters(EMPTY_FILTERS);
    await load(true, EMPTY_FILTERS);
  };

  const transactionTypeLabel = (type: TransactionType) => t.enums[type];
  const recurrenceLabel = (rule: RecurrenceRule) => t.enums[rule];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.transactions.title}</h1>
          <p className="mt-1 text-muted-foreground">
            {t.transactions.subtitle}
          </p>
        </div>
        <Button onClick={openCreate} disabled={accounts.length === 0}>
          {t.transactions.add}
        </Button>
      </div>

      {accounts.length === 0 && !loading && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
          {t.transactions.noAccounts} <Link href="/accounts" className="underline">{t.accounts.title}</Link>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 rounded-lg border border-border p-4 sm:grid-cols-2 lg:grid-cols-5">
        <div className="space-y-1.5">
          <Label>{t.transactions.account}</Label>
          <Select
            value={filters.account_id}
            onValueChange={(v: string | null) => setFilters({ ...filters, account_id: v ?? "" })}
          >
            <SelectTrigger className="w-full min-w-0">
              <span className="block truncate text-sm">
                {filters.account_id ? accountMap.get(filters.account_id)?.name : t.transactions.allAccounts}
              </span>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">{t.transactions.allAccounts}</SelectItem>
              {accounts.map((account) => (
                <SelectItem key={account.id} value={account.id}>{account.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>{t.common.type}</Label>
          <Select
            value={filters.type}
            onValueChange={(v: string | null) => setFilters({ ...filters, type: (v ?? "all") as TransactionFilters["type"] })}
          >
            <SelectTrigger className="w-full">
              <span className="text-sm">{filters.type === "all" ? t.common.all : transactionTypeLabel(filters.type)}</span>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t.common.all}</SelectItem>
              <SelectItem value="income">{t.enums.income}</SelectItem>
              <SelectItem value="expense">{t.enums.expense}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="date-from">{t.transactions.from}</Label>
          <Input id="date-from" type="date" value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="date-to">{t.transactions.to}</Label>
          <Input id="date-to" type="date" value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} />
        </div>
        <div className="flex items-end gap-2">
          <Button onClick={applyFilters}>{t.common.apply}</Button>
          <Button variant="ghost" onClick={clearFilters}>{t.common.clear}</Button>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">{t.common.loading}</p>
      ) : transactions.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
          <p className="text-lg">{t.transactions.noTransactions}</p>
          <p className="mt-1 text-sm">{t.transactions.emptyHint}</p>
        </div>
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t.common.date}</TableHead>
                <TableHead>{t.transactions.account}</TableHead>
                <TableHead>{t.common.type}</TableHead>
                <TableHead>{t.common.description}</TableHead>
                <TableHead>{t.common.category}</TableHead>
                <TableHead>{t.transactions.recurring}</TableHead>
                <TableHead className="text-right">{t.common.amount}</TableHead>
                <TableHead className="text-right">{t.common.actions}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {transactions.map((transaction) => {
                const account = accountMap.get(transaction.account_id);
                return (
                  <TableRow key={transaction.id}>
                    <TableCell>{formatDate(transaction.date, lang)}</TableCell>
                    <TableCell className="font-medium">{account?.name ?? t.transactions.unknownAccount}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className={TYPE_COLORS[transaction.type]}>
                        {transactionTypeLabel(transaction.type)}
                      </Badge>
                    </TableCell>
                    <TableCell>{transaction.description}</TableCell>
                    <TableCell className="text-muted-foreground">{transaction.category_id ? categoryMap.get(transaction.category_id)?.name : (transaction.category ?? "-")}</TableCell>
                    <TableCell>
                      {transaction.is_recurring ? (
                        <div className="flex flex-col items-start gap-1">
                          {transaction.recurrence_rule && <Badge variant="outline">{recurrenceLabel(transaction.recurrence_rule)}</Badge>}
                          {transaction.end_date && (
                            <span className="text-xs text-muted-foreground">
                              {t.transactions.until} {formatDate(transaction.end_date, lang)}
                            </span>
                          )}
                        </div>
                      ) : (
                        <span className="text-muted-foreground">{t.transactions.no}</span>
                      )}
                    </TableCell>
                    <TableCell className={`text-right font-mono ${transaction.type === "income" ? "text-emerald-400" : "text-red-400"}`}>
                      {transaction.type === "income" ? "+" : "-"}{formatAmount(transaction.amount, lang, account)}
                    </TableCell>
                    <TableCell className="space-x-2 text-right">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(transaction)}>{t.common.edit}</Button>
                      <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300" onClick={() => handleDelete(transaction.id)}>
                        {t.common.delete}
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? t.transactions.editDialog : t.transactions.addDialog}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>{t.transactions.account}</Label>
                <Select
                  value={form.account_id}
                  onValueChange={(v: string | null) => setForm({ ...form, account_id: v ?? "" })}
                >
                  <SelectTrigger className="min-w-0">
                    <span className="block truncate text-sm">
                      {accountMap.get(form.account_id)?.name ?? t.transactions.selectAccount}
                    </span>
                  </SelectTrigger>
                  <SelectContent>
                    {accounts.map((account) => (
                      <SelectItem key={account.id} value={account.id}>{account.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>{t.common.type}</Label>
                <Select
                  value={form.type}
                  onValueChange={(v: string | null) => setForm({ ...form, type: (v ?? "expense") as TransactionType })}
                >
                  <SelectTrigger>
                    <span className="text-sm">{transactionTypeLabel(form.type)}</span>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="income">{t.enums.income}</SelectItem>
                    <SelectItem value="expense">{t.enums.expense}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="amount">{t.common.amount}</Label>
                <Input
                  id="amount"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0"
                  value={form.amount === 0 ? "" : form.amount}
                  onChange={(e) => setForm({ ...form, amount: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="transaction-date">{t.common.date}</Label>
                <Input
                  id="transaction-date"
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="description">{t.common.description}</Label>
              <Input
                id="description"
                placeholder={t.transactions.placeholderDescription}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>

            <div className="space-y-1.5">
              <Label>{t.common.category}</Label>
              <Select
                value={form.category_id}
                onValueChange={(v: string | null) => setForm({ ...form, category_id: v ?? "" })}
              >
                <SelectTrigger>
                  <span className="block truncate text-sm">
                    {form.category_id ? categoryMap.get(form.category_id)?.name : t.common.none}
                  </span>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">{t.common.none}</SelectItem>
                  {categories.filter((category) => category.type === form.type || category.type === "both").map((category) => (
                    <SelectItem key={category.id} value={category.id}>
                      <div className="flex items-center gap-2">
                        <div className="h-3 w-3 rounded-full" style={{ backgroundColor: category.color }} />
                        {category.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-3">
              <label className="flex h-9 items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.is_recurring}
                  onChange={(e) => setForm({ ...form, is_recurring: e.target.checked })}
                />
                {t.transactions.recurring}
              </label>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label>{t.transactions.frequency}</Label>
                  <Select
                    value={form.recurrence_rule}
                    onValueChange={(v: string | null) => setForm({ ...form, recurrence_rule: (v ?? "monthly") as RecurrenceRule })}
                    disabled={!form.is_recurring}
                  >
                    <SelectTrigger className="w-full">
                      <span className="text-sm">{recurrenceLabel(form.recurrence_rule)}</span>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="monthly">{t.enums.monthly}</SelectItem>
                      <SelectItem value="weekly">{t.enums.weekly}</SelectItem>
                      <SelectItem value="yearly">{t.enums.yearly}</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="end-date">{t.transactions.endDate}</Label>
                  <Input
                    id="end-date"
                    type="date"
                    value={form.end_date}
                    onChange={(e) => setForm({ ...form, end_date: e.target.value })}
                    disabled={!form.is_recurring}
                  />
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>{t.common.cancel}</Button>
            <Button
              onClick={handleSave}
              disabled={saving || !form.account_id || !form.description || !form.date || form.amount <= 0}
            >
              {saving ? t.common.saving : t.common.save}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
