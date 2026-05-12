"use client";

import { useEffect, useState } from "react";
import { currenciesApi, type Currency } from "@/lib/api";
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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface CurrencyForm {
  code: string;
  name: string;
  symbol: string;
  decimal_places: number;
  is_crypto: boolean;
}

const EMPTY_FORM: CurrencyForm = {
  code: "",
  name: "",
  symbol: "",
  decimal_places: 2,
  is_crypto: false,
};

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function CurrenciesPage() {
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Currency | null>(null);
  const [form, setForm] = useState<CurrencyForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);

  const load = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      setCurrencies(await currenciesApi.list());
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load currencies");
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load(false); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (c: Currency) => {
    setEditing(c);
    setForm({ code: c.code, name: c.name, symbol: c.symbol, decimal_places: c.decimal_places, is_crypto: c.is_crypto });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (editing) {
        await currenciesApi.update(editing.id, {
          name: form.name,
          symbol: form.symbol,
          decimal_places: form.decimal_places,
          is_crypto: form.is_crypto,
        });
      } else {
        await currenciesApi.create(form);
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
    if (!confirm("Delete this currency? This will fail if any accounts or credit cards use it.")) return;
    try {
      await currenciesApi.delete(id);
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
          <h1 className="text-3xl font-bold tracking-tight">Currencies</h1>
          <p className="text-muted-foreground mt-1">
            Manage fiat and crypto currencies used across accounts and credit cards.
          </p>
        </div>
        <Button onClick={openCreate}>+ Add Currency</Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Table */}
      {loading ? (
        <p className="text-muted-foreground text-sm">Loading...</p>
      ) : currencies.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
          <p className="text-lg">No currencies yet.</p>
          <p className="text-sm mt-1">Click &quot;Add Currency&quot; to create one.</p>
        </div>
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Code</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Decimals</TableHead>
                <TableHead>Type</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {currencies.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-mono font-semibold">{c.code}</TableCell>
                  <TableCell>{c.name}</TableCell>
                  <TableCell className="font-mono text-lg">{c.symbol}</TableCell>
                  <TableCell>{c.decimal_places}</TableCell>
                  <TableCell>
                    {c.is_crypto ? (
                      <Badge variant="outline" className="text-amber-400 border-amber-400/40">Crypto</Badge>
                    ) : (
                      <Badge variant="outline" className="text-blue-400 border-blue-400/40">Fiat</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right space-x-2">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(c)}>Edit</Button>
                    <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300" onClick={() => handleDelete(c.id)}>
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
            <DialogTitle>{editing ? "Edit Currency" : "Add Currency"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="code">Code</Label>
                <Input
                  id="code"
                  placeholder="e.g. ARS, BTC"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                  disabled={!!editing}
                  maxLength={10}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="symbol">Symbol</Label>
                <Input
                  id="symbol"
                  placeholder="e.g. $, BTC, EUR"
                  value={form.symbol}
                  onChange={(e) => setForm({ ...form, symbol: e.target.value })}
                  maxLength={10}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="e.g. Argentine Peso"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="decimals">Decimal places</Label>
                <Input
                  id="decimals"
                  type="number"
                  min={0}
                  max={18}
                  value={form.decimal_places}
                  onFocus={(e) => e.currentTarget.select()}
                  onChange={(e) => setForm({ ...form, decimal_places: parseInt(e.target.value) || 2 })}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Type</Label>
                <div className="flex items-center gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, is_crypto: false })}
                    className={`px-3 py-1 rounded-md text-sm border transition-colors ${!form.is_crypto ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground"}`}
                  >
                    Fiat
                  </button>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, is_crypto: true })}
                    className={`px-3 py-1 rounded-md text-sm border transition-colors ${form.is_crypto ? "border-amber-400 bg-amber-400/10 text-amber-400" : "border-border text-muted-foreground"}`}
                  >
                    Crypto
                  </button>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving || !form.code || !form.name || !form.symbol}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
