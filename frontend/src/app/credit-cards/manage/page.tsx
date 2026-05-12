"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import {
  accountsApi,
  creditCardsApi,
  currenciesApi,
  type Account,
  type CreditCard,
  type Currency,
} from "@/lib/api";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

interface CreditCardForm {
  name: string;
  closing_day: number;
  due_day: number;
  currency_id: string;
  payment_account_id: string | null;
  credit_limit: number | null;
}

const EMPTY_CARD_FORM: CreditCardForm = {
  name: "",
  closing_day: 5,
  due_day: 20,
  currency_id: "",
  payment_account_id: null,
  credit_limit: null,
};

export default function ManageCardsPage() {
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [currencies, setCurrencies] = useState<Currency[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [cardDialogOpen, setCardDialogOpen] = useState(false);
  const [editingCard, setEditingCard] = useState<CreditCard | null>(null);
  const [cardForm, setCardForm] = useState<CreditCardForm>(EMPTY_CARD_FORM);
  const [savingCard, setSavingCard] = useState(false);

  const load = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      const [cardRows, accountRows, currencyRows] = await Promise.all([
        creditCardsApi.list(),
        accountsApi.list(),
        currenciesApi.list(),
      ]);
      setCards(cardRows);
      setAccounts(accountRows);
      setCurrencies(currencyRows);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(true); }, []);

  const openCreateCard = () => {
    setEditingCard(null);
    setCardForm({ ...EMPTY_CARD_FORM, currency_id: currencies[0]?.id ?? "" });
    setCardDialogOpen(true);
  };

  const openEditCard = (card: CreditCard) => {
    setEditingCard(card);
    setCardForm({
      name: card.name,
      closing_day: card.closing_day,
      due_day: card.due_day,
      currency_id: card.currency_id,
      payment_account_id: card.payment_account_id,
      credit_limit: card.credit_limit,
    });
    setCardDialogOpen(true);
  };

  const handleCardSave = async () => {
    setSavingCard(true);
    try {
      const payload = {
        ...cardForm,
        credit_limit: cardForm.credit_limit === null ? null : Number(cardForm.credit_limit),
      };
      if (editingCard) {
        await creditCardsApi.update(editingCard.id, payload);
      } else {
        await creditCardsApi.create(payload);
      }
      setCardDialogOpen(false);
      await load(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSavingCard(false);
    }
  };

  const handleCardDelete = async (id: string) => {
    if (!confirm("Delete this credit card? This will also delete its purchases and installments.")) return;
    try {
      await creditCardsApi.delete(id);
      await load(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/credit-cards" className={buttonVariants({ variant: "outline", size: "icon" })}>
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Manage Credit Cards</h1>
          <p className="text-muted-foreground mt-1">
            Add, edit, and configure your credit cards and auto-debit accounts.
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <div className="flex gap-2">
        <Button onClick={openCreateCard}>+ Add Card</Button>
      </div>

      {loading ? (
        <p className="text-muted-foreground text-sm">Loading...</p>
      ) : cards.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
          <p className="text-lg">No cards configured yet.</p>
          <p className="text-sm mt-1">Click "+ Add Card" to set up your first one.</p>
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Payment Account</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead>Limit</TableHead>
                  <TableHead className="whitespace-nowrap">Closing / Due</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cards.map((card) => {
                  const account = accounts.find(a => a.id === card.payment_account_id);
                  const currency = currencies.find(c => c.id === card.currency_id);
                  return (
                    <TableRow key={card.id}>
                      <TableCell className="font-medium whitespace-nowrap">{card.name}</TableCell>
                      <TableCell className="text-muted-foreground whitespace-nowrap">{account?.name || "Not linked"}</TableCell>
                      <TableCell className="whitespace-nowrap">{currency?.code || "Unknown"}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {card.credit_limit ? `${currency?.symbol || ""} ${card.credit_limit.toLocaleString()}` : "No limit"}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        Day {card.closing_day} / Day {card.due_day}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => openEditCard(card)}>Edit</Button>
                          <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300" onClick={() => handleCardDelete(card.id)}>Delete</Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </div>
      )}

      {/* --- Create/Edit Card Dialog --- */}
      <Dialog open={cardDialogOpen} onOpenChange={setCardDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingCard ? "Edit Credit Card" : "Add Credit Card"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="card-name">Name</Label>
              <Input
                id="card-name"
                placeholder="e.g. Visa Signature"
                value={cardForm.name}
                onChange={(e) => setCardForm({ ...cardForm, name: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Currency</Label>
                <Select value={cardForm.currency_id || ""} onValueChange={(v: string | null) => setCardForm({ ...cardForm, currency_id: v ?? "" })}>
                  <SelectTrigger className="min-w-0">
                    <SelectValue placeholder="Select currency">
                      {currencies.find(c => c.id === cardForm.currency_id)?.code}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {currencies.map((c) => <SelectItem key={c.id} value={c.id}>{c.code}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Auto-debit Account</Label>
                <Select value={cardForm.payment_account_id || "none"} onValueChange={(v: string | null) => setCardForm({ ...cardForm, payment_account_id: v === "none" || v === null ? null : v })}>
                  <SelectTrigger className="min-w-0">
                    <SelectValue placeholder="None (Manual payment)">
                      {accounts.find(a => a.id === cardForm.payment_account_id)?.name ?? "None (Manual payment)"}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None (Manual payment)</SelectItem>
                    {accounts.map((a) => <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="closing-day">Closing Day</Label>
                <Input
                  id="closing-day"
                  type="number"
                  min={1} max={31}
                  value={cardForm.closing_day}
                  onFocus={(e) => e.currentTarget.select()}
                  onChange={(e) => setCardForm({ ...cardForm, closing_day: parseInt(e.target.value) || 1 })}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="due-day">Due Day</Label>
                <Input
                  id="due-day"
                  type="number"
                  min={1} max={31}
                  value={cardForm.due_day}
                  onFocus={(e) => e.currentTarget.select()}
                  onChange={(e) => setCardForm({ ...cardForm, due_day: parseInt(e.target.value) || 1 })}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="credit-limit">Limit</Label>
                <Input
                  id="credit-limit"
                  type="number"
                  step="0.01" min="0" placeholder="Optional"
                  value={cardForm.credit_limit ?? ""}
                  onFocus={(e) => e.currentTarget.select()}
                  onChange={(e) => setCardForm({ ...cardForm, credit_limit: e.target.value ? parseFloat(e.target.value) : null })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setCardDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleCardSave} disabled={savingCard || !cardForm.name || !cardForm.currency_id}>
              {savingCard ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
