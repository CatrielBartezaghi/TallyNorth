"use client";

import { useEffect, useState } from "react";
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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type AccountType = "checking" | "savings" | "cash";

interface AccountForm {
  name: string;
  type: AccountType;
  currency_id: string;
  initial_balance: number;
}

const EMPTY_FORM: AccountForm = {
  name: "",
  type: "checking",
  currency_id: "",
  initial_balance: 0,
};

const ACCOUNT_TYPE_LABELS: Record<AccountType, string> = {
  checking: "Checking",
  savings: "Savings",
  cash: "Cash",
};

const ACCOUNT_TYPE_COLORS: Record<AccountType, string> = {
  checking: "text-blue-400 border-blue-400/40",
  savings: "text-emerald-400 border-emerald-400/40",
  cash: "text-amber-400 border-amber-400/40",
};

function formatAmount(amount: number, currency: Currency) {
  return `${currency.symbol} ${amount.toLocaleString("en-US", {
    minimumFractionDigits: currency.decimal_places,
    maximumFractionDigits: currency.decimal_places,
  })}`;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const [form, setForm] = useState<AccountForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const load = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      const [accs, curs] = await Promise.all([accountsApi.list(), currenciesApi.list()]);
      setAccounts(accs);
      setCurrencies(curs);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load(false); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, currency_id: currencies[0]?.id ?? "" });
    setDialogOpen(true);
  };

  const openEdit = (a: Account) => {
    setEditing(a);
    setForm({
      name: a.name,
      type: a.type,
      currency_id: a.currency_id,
      initial_balance: a.initial_balance,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editing) {
        await accountsApi.update(editing.id, form);
      } else {
        await accountsApi.create(form);
      }
      setDialogOpen(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this account? This will also delete all its transactions.")) return;
    try {
      await accountsApi.delete(id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Accounts</h1>
          <p className="text-muted-foreground mt-1">
            Manage your bank accounts, savings, and cash wallets.
          </p>
        </div>
        <Button onClick={openCreate} disabled={currencies.length === 0}>
          + Add Account
        </Button>
      </div>

      {currencies.length === 0 && !loading && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
          No currencies found. Go to <a href="/currencies" className="underline">Currencies</a> to add one first.
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Table */}
      {loading ? (
        <p className="text-muted-foreground text-sm">Loading...</p>
      ) : accounts.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
          <p className="text-lg">No accounts yet.</p>
          <p className="text-sm mt-1">Click &quot;Add Account&quot; to create your first one.</p>
        </div>
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Currency</TableHead>
                <TableHead className="text-right">Initial Balance</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts.map((a) => (
                <TableRow key={a.id}>
                  <TableCell className="font-medium">{a.name}</TableCell>
                  <TableCell>
                    <Badge variant="outline" className={ACCOUNT_TYPE_COLORS[a.type]}>
                      {ACCOUNT_TYPE_LABELS[a.type]}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-sm">
                      {a.currency.symbol} <span className="text-muted-foreground">{a.currency.code}</span>
                    </span>
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatAmount(a.initial_balance, a.currency)}
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(a)}>Edit</Button>
                    <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300" onClick={() => handleDelete(a.id)}>
                      Delete
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Edit Account" : "Add Account"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="acc-name">Name</Label>
              <Input
                id="acc-name"
                placeholder="e.g. Galicia Checking"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-[minmax(9rem,0.75fr)_minmax(0,1.25fr)]">
              <div className="space-y-1.5">
                <Label>Type</Label>
                <Select
                  value={form.type}
                  onValueChange={(v) => setForm({ ...form, type: v as AccountType })}
                >
                  <SelectTrigger className="w-full">
                    <span className="text-sm">
                      {ACCOUNT_TYPE_LABELS[form.type] ?? "Select type"}
                    </span>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="checking">Checking</SelectItem>
                    <SelectItem value="savings">Savings</SelectItem>
                    <SelectItem value="cash">Cash</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="min-w-0 space-y-1.5">
                <Label>Currency</Label>
                <Select
                  value={form.currency_id || ""}
                  onValueChange={(v: string | null) => setForm({ ...form, currency_id: v ?? "" })}
                >
                  <SelectTrigger className="w-full min-w-0">
                    <span className="block min-w-0 truncate text-sm">
                      {(() => {
                        const c = currencies.find((cur) => cur.id === form.currency_id);
                        return c ? `${c.symbol} ${c.code} - ${c.name}` : "Select currency";
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

            <div className="space-y-1.5">
              <Label htmlFor="initial-balance">Initial Balance</Label>
              <Input
                id="initial-balance"
                type="number"
                step="0.01"
                min="0"
                placeholder="0"
                value={form.initial_balance === 0 ? "" : form.initial_balance}
                onChange={(e) => setForm({ ...form, initial_balance: parseFloat(e.target.value) || 0 })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button
              onClick={handleSave}
              disabled={saving || !form.name || !form.currency_id}
            >
              {saving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
