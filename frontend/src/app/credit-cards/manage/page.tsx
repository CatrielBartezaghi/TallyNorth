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
import { useLanguage } from "@/lib/LanguageContext";

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
  const { lang, t } = useLanguage();
  const locale = lang === "es" ? "es-AR" : "en-US";

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
      setError(e instanceof Error ? e.message : t.common.errorLoadingData);
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
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
      setError(e instanceof Error ? e.message : t.manageCreditCards.saveError);
    } finally {
      setSavingCard(false);
    }
  };

  const handleCardDelete = async (id: string) => {
    if (!confirm(t.manageCreditCards.confirmDelete)) return;
    try {
      await creditCardsApi.delete(id);
      await load(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.manageCreditCards.deleteError);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/credit-cards" className={buttonVariants({ variant: "outline", size: "icon" })}>
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.manageCreditCards.title}</h1>
          <p className="mt-1 text-muted-foreground">
            {t.manageCreditCards.subtitle}
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <div className="flex gap-2">
        <Button onClick={openCreateCard}>{t.manageCreditCards.add}</Button>
      </div>

      {loading ? (
        <p className="text-sm text-muted-foreground">{t.common.loading}</p>
      ) : cards.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
          <p className="text-lg">{t.manageCreditCards.noCards}</p>
          <p className="mt-1 text-sm">{t.manageCreditCards.emptyHint}</p>
        </div>
      ) : (
        <div className="rounded-lg border border-border bg-card">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t.common.name}</TableHead>
                  <TableHead>{t.manageCreditCards.paymentAccount}</TableHead>
                  <TableHead>{t.common.currency}</TableHead>
                  <TableHead>{t.manageCreditCards.limit}</TableHead>
                  <TableHead className="whitespace-nowrap">{t.manageCreditCards.closingDue}</TableHead>
                  <TableHead className="text-right">{t.common.actions}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {cards.map((card) => {
                  const account = accounts.find((item) => item.id === card.payment_account_id);
                  const currency = currencies.find((item) => item.id === card.currency_id);
                  return (
                    <TableRow key={card.id}>
                      <TableCell className="font-medium whitespace-nowrap">{card.name}</TableCell>
                      <TableCell className="text-muted-foreground whitespace-nowrap">{account?.name || t.manageCreditCards.notLinked}</TableCell>
                      <TableCell className="whitespace-nowrap">{currency?.code || t.common.unknown}</TableCell>
                      <TableCell className="whitespace-nowrap">
                        {card.credit_limit ? `${currency?.symbol || ""} ${card.credit_limit.toLocaleString(locale)}` : t.manageCreditCards.noLimit}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">
                        {t.manageCreditCards.day} {card.closing_day} / {t.manageCreditCards.day} {card.due_day}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="ghost" size="sm" onClick={() => openEditCard(card)}>{t.common.edit}</Button>
                          <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300" onClick={() => handleCardDelete(card.id)}>{t.common.delete}</Button>
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

      <Dialog open={cardDialogOpen} onOpenChange={setCardDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingCard ? t.manageCreditCards.editDialog : t.manageCreditCards.addDialog}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="card-name">{t.common.name}</Label>
              <Input
                id="card-name"
                placeholder={t.manageCreditCards.placeholderName}
                value={cardForm.name}
                onChange={(e) => setCardForm({ ...cardForm, name: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>{t.common.currency}</Label>
                <Select value={cardForm.currency_id || ""} onValueChange={(v: string | null) => setCardForm({ ...cardForm, currency_id: v ?? "" })}>
                  <SelectTrigger className="min-w-0">
                    <SelectValue placeholder={t.accounts.selectCurrency}>
                      {currencies.find((currency) => currency.id === cardForm.currency_id)?.code}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {currencies.map((currency) => <SelectItem key={currency.id} value={currency.id}>{currency.code}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>{t.manageCreditCards.autoDebitAccount}</Label>
                <Select value={cardForm.payment_account_id || "none"} onValueChange={(v: string | null) => setCardForm({ ...cardForm, payment_account_id: v === "none" || v === null ? null : v })}>
                  <SelectTrigger className="min-w-0">
                    <SelectValue placeholder={t.manageCreditCards.manualPayment}>
                      {accounts.find((account) => account.id === cardForm.payment_account_id)?.name ?? t.manageCreditCards.manualPayment}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">{t.manageCreditCards.manualPayment}</SelectItem>
                    {accounts.map((account) => <SelectItem key={account.id} value={account.id}>{account.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="closing-day">{t.manageCreditCards.closingDay}</Label>
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
                <Label htmlFor="due-day">{t.manageCreditCards.dueDay}</Label>
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
                <Label htmlFor="credit-limit">{t.manageCreditCards.limit}</Label>
                <Input
                  id="credit-limit"
                  type="number"
                  step="0.01" min="0" placeholder={t.manageCreditCards.optional}
                  value={cardForm.credit_limit ?? ""}
                  onFocus={(e) => e.currentTarget.select()}
                  onChange={(e) => setCardForm({ ...cardForm, credit_limit: e.target.value ? parseFloat(e.target.value) : null })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setCardDialogOpen(false)}>{t.common.cancel}</Button>
            <Button onClick={handleCardSave} disabled={savingCard || !cardForm.name || !cardForm.currency_id}>
              {savingCard ? t.common.saving : t.common.save}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
