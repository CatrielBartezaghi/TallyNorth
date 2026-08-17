"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { accountsApi, currenciesApi, type Account, type Currency } from "@/lib/api";
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

type AccountType = "checking" | "savings" | "cash";

interface AccountForm {
  name: string;
  type: AccountType;
  currency_id: string;
  initial_balance: number;
  target_balance?: number;
}

const EMPTY_FORM: AccountForm = {
  name: "",
  type: "checking",
  currency_id: "",
  initial_balance: 0,
};

const ACCOUNT_TYPE_COLORS: Record<AccountType, string> = {
  checking: "text-blue-400 border-blue-400/40",
  savings: "text-emerald-400 border-emerald-400/40",
  cash: "text-amber-400 border-amber-400/40",
};

function formatAmount(amount: number, currency: Currency, lang: Language) {
  return `${currency.symbol} ${amount.toLocaleString(lang === "es" ? "es-AR" : "en-US", {
    minimumFractionDigits: currency.decimal_places,
    maximumFractionDigits: currency.decimal_places,
  })}`;
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [form, setForm] = useState<AccountForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const { lang, t } = useLanguage();

  const load = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      const [accs, curs] = await Promise.all([accountsApi.list(), currenciesApi.list()]);
      setAccounts(accs);
      setCurrencies(curs);
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
    setForm({ ...EMPTY_FORM, currency_id: currencies[0]?.id ?? "" });
    setDialogOpen(true);
  };

  const openEdit = (account: Account) => {
    setEditing(account);
    setForm({
      name: account.name,
      type: account.type,
      currency_id: account.currency_id,
      initial_balance: account.initial_balance,
      target_balance: account.current_balance,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editing) {
        const p1 = accountsApi.update(editing.id, form);
        const p2 = form.target_balance !== undefined && form.target_balance !== editing.current_balance 
          ? accountsApi.adjustBalance(editing.id, form.target_balance)
          : Promise.resolve();
        await Promise.all([p1, p2]);
      } else {
        await accountsApi.create(form);
      }
      setDialogOpen(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.accounts.saveError);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t.accounts.confirmDelete)) return;
    try {
      await accountsApi.delete(id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.accounts.deleteError);
    }
  };

  const accountTypeLabel = (type: AccountType) => t.enums[type];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.accounts.title}</h1>
          <p className="mt-1 text-muted-foreground">
            {t.accounts.subtitle}
          </p>
        </div>
        <Button onClick={openCreate} disabled={currencies.length === 0}>
          {t.accounts.add}
        </Button>
      </div>

      {currencies.length === 0 && !loading && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
          {t.accounts.noCurrencies} <Link href="/currencies" className="underline">{t.currencies.title}</Link>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">{t.common.loading}</p>
      ) : accounts.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
          <p className="text-lg">{t.accounts.noAccounts}</p>
          <p className="mt-1 text-sm">{t.accounts.emptyHint}</p>
        </div>
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t.common.name}</TableHead>
                <TableHead>{t.common.type}</TableHead>
                <TableHead>{t.common.currency}</TableHead>
                <TableHead className="text-right">{(t.accounts as any).currentBalance || (t.accounts as any).initialBalance}</TableHead>
                <TableHead className="text-right">{t.common.actions}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.map((account) => (
                <TableRow key={account.id}>
                  <TableCell className="font-medium">{account.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={ACCOUNT_TYPE_COLORS[account.type]}>
                      {accountTypeLabel(account.type)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-sm">
                      {account.currency.symbol} <span className="text-muted-foreground">{account.currency.code}</span>
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatAmount(account.current_balance, account.currency, lang)}
                  </TableCell>
                  <TableCell className="space-x-2 text-right">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(account)}>{t.common.edit}</Button>
                    <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300" onClick={() => handleDelete(account.id)}>
                      {t.common.delete}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? t.accounts.editDialog : t.accounts.addDialog}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="acc-name">{t.common.name}</Label>
              <Input
                id="acc-name"
                placeholder={t.accounts.placeholderName}
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-[minmax(9rem,0.75fr)_minmax(0,1.25fr)]">
              <div className="space-y-1.5">
                <Label>{t.common.type}</Label>
                <Select
                  value={form.type}
                  onValueChange={(v) => setForm({ ...form, type: v as AccountType })}
                >
                  <SelectTrigger className="w-full">
                    <span className="text-sm">
                      {accountTypeLabel(form.type) ?? t.accounts.selectType}
                    </span>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="checking">{t.enums.checking}</SelectItem>
                    <SelectItem value="savings">{t.enums.savings}</SelectItem>
                    <SelectItem value="cash">{t.enums.cash}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="min-w-0 space-y-1.5">
                <Label>{t.common.currency}</Label>
                <Select
                  value={form.currency_id || ""}
                  onValueChange={(v: string | null) => setForm({ ...form, currency_id: v ?? "" })}
                >
                  <SelectTrigger className="w-full min-w-0">
                    <span className="block min-w-0 truncate text-sm">
                      {(() => {
                        const c = currencies.find((cur) => cur.id === form.currency_id);
                        return c ? `${c.symbol} ${c.code} - ${c.name}` : t.accounts.selectCurrency;
                      })()}
                    </span>
                  </SelectTrigger>
                  <SelectContent>
                    {currencies.map((c) => (
                      <SelectItem key={c.id} value={c.id}>
                        {c.symbol} {c.code} - {c.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {editing ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-1.5 opacity-60">
                  <Label htmlFor="initial-balance">{(t.accounts as any).initialBalance}</Label>
                  <Input
                    id="initial-balance"
                    type="number"
                    step="0.01"
                    value={form.initial_balance === 0 ? "" : form.initial_balance}
                    disabled
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="target-balance">{(t.accounts as any).targetBalance}</Label>
                  <Input
                    id="target-balance"
                    type="number"
                    step="0.01"
                    value={form.target_balance === undefined ? "" : form.target_balance}
                    onChange={(e) => setForm({ ...form, target_balance: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-1.5">
                <Label htmlFor="initial-balance">{(t.accounts as any).initialBalance}</Label>
                <Input
                  id="initial-balance"
                  type="number"
                  step="0.01"
                  placeholder="0"
                  value={form.initial_balance === 0 ? "" : form.initial_balance}
                  onChange={(e) => setForm({ ...form, initial_balance: parseFloat(e.target.value) || 0 })}
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>{t.common.cancel}</Button>
            <Button
              onClick={handleSave}
              disabled={saving || !form.name || !form.currency_id}
            >
              {saving ? t.common.saving : t.common.save}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
