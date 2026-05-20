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
import { useLanguage } from "@/lib/LanguageContext";

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

export default function CurrenciesPage() {
  const [currencies, setCurrencies] = useState<Currency[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Currency | null>(null);
  const [form, setForm] = useState<CurrencyForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const { t } = useLanguage();

  const load = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      setCurrencies(await currenciesApi.list());
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.currencies.loadError);
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { void load(false); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDialogOpen(true);
  };

  const openEdit = (currency: Currency) => {
    setEditing(currency);
    setForm({ code: currency.code, name: currency.name, symbol: currency.symbol, decimal_places: currency.decimal_places, is_crypto: currency.is_crypto });
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
      setError(e instanceof Error ? e.message : t.currencies.saveError);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t.currencies.confirmDelete)) return;
    try {
      await currenciesApi.delete(id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.currencies.deleteError);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.currencies.title}</h1>
          <p className="mt-1 text-muted-foreground">
            {t.currencies.subtitle}
          </p>
        </div>
        <Button onClick={openCreate}>{t.currencies.add}</Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">{t.common.loading}</p>
      ) : currencies.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
          <p className="text-lg">{t.currencies.noCurrencies}</p>
          <p className="mt-1 text-sm">{t.currencies.emptyHint}</p>
        </div>
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t.currencies.code}</TableHead>
                <TableHead>{t.common.name}</TableHead>
                <TableHead>{t.currencies.symbol}</TableHead>
                <TableHead>{t.currencies.decimals}</TableHead>
                <TableHead>{t.common.type}</TableHead>
                <TableHead className="text-right">{t.common.actions}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {currencies.map((currency) => (
                <TableRow key={currency.id}>
                  <TableCell className="font-mono font-semibold">{currency.code}</TableCell>
                  <TableCell>{currency.name}</TableCell>
                  <TableCell className="font-mono text-lg">{currency.symbol}</TableCell>
                  <TableCell>{currency.decimal_places}</TableCell>
                  <TableCell>
                    {currency.is_crypto ? (
                      <Badge variant="outline" className="border-amber-400/40 text-amber-400">{t.enums.crypto}</Badge>
                    ) : (
                      <Badge variant="outline" className="border-blue-400/40 text-blue-400">{t.enums.fiat}</Badge>
                    )}
                  </TableCell>
                  <TableCell className="space-x-2 text-right">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(currency)}>{t.common.edit}</Button>
                    <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300" onClick={() => handleDelete(currency.id)}>
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
            <DialogTitle>{editing ? t.currencies.editDialog : t.currencies.addDialog}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="code">{t.currencies.code}</Label>
                <Input
                  id="code"
                  placeholder={t.currencies.placeholderCode}
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                  disabled={!!editing}
                  maxLength={10}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="symbol">{t.currencies.symbol}</Label>
                <Input
                  id="symbol"
                  placeholder={t.currencies.placeholderSymbol}
                  value={form.symbol}
                  onChange={(e) => setForm({ ...form, symbol: e.target.value })}
                  maxLength={10}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="name">{t.common.name}</Label>
              <Input
                id="name"
                placeholder={t.currencies.placeholderName}
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="decimals">{t.currencies.decimalPlaces}</Label>
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
                <Label>{t.common.type}</Label>
                <div className="flex items-center gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, is_crypto: false })}
                    className={`rounded-md border px-3 py-1 text-sm transition-colors ${!form.is_crypto ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground"}`}
                  >
                    {t.enums.fiat}
                  </button>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, is_crypto: true })}
                    className={`rounded-md border px-3 py-1 text-sm transition-colors ${form.is_crypto ? "border-amber-400 bg-amber-400/10 text-amber-400" : "border-border text-muted-foreground"}`}
                  >
                    {t.enums.crypto}
                  </button>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>{t.common.cancel}</Button>
            <Button onClick={handleSave} disabled={saving || !form.code || !form.name || !form.symbol}>
              {saving ? t.common.saving : t.common.save}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
