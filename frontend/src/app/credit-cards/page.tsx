"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Settings } from "lucide-react";
import {
  categoriesApi,
  creditCardsApi,
  installmentsApi,
  purchasesApi,
  type CreditCard,
  type Purchase,
  type Currency,
  type Category,
} from "@/lib/api";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
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
import type { Language } from "@/lib/translations";

interface PurchaseForm {
  credit_card_id: string;
  description: string;
  installment_amount: number;
  installments: number;
  starting_installment: number;
  purchase_date: string;
  category_id: string;
}

interface ImportRow {
  id: number;
  purchase_date: string;
  description: string;
  installment_amount: number;
  installments: number;
  starting_installment: number;
  category_id: string;
  category: string;
}

const today = () => new Date().toISOString().slice(0, 10);

const EMPTY_PURCHASE_FORM: PurchaseForm = {
  credit_card_id: "",
  description: "",
  installment_amount: 0,
  installments: 1,
  starting_installment: 1,
  purchase_date: today(),
  category_id: "",
};

function localeFor(lang: Language) {
  return lang === "es" ? "es-AR" : "en-US";
}

function formatDate(value: string, lang: Language) {
  return new Date(`${value}T00:00:00`).toLocaleDateString(localeFor(lang));
}

function formatAmount(amount: number | null, currency: Currency | undefined, lang: Language, noLimit: string) {
  if (amount === null) return noLimit;
  if (!currency) return amount.toLocaleString(localeFor(lang), { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${currency.symbol} ${amount.toLocaleString(localeFor(lang), {
    minimumFractionDigits: currency.decimal_places,
    maximumFractionDigits: currency.decimal_places,
  })}`;
}

export default function CreditCardsPage() {
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [cards, setCards] = useState<CreditCard[]>([]);
  const [selectedCardId, setSelectedCardId] = useState<string>("all");
  const [hideCompleted, setHideCompleted] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [purchaseDialogOpen, setPurchaseDialogOpen] = useState(false);
  const [editingPurchase, setEditingPurchase] = useState<Purchase | null>(null);
  const [purchaseForm, setPurchaseForm] = useState<PurchaseForm>(EMPTY_PURCHASE_FORM);
  const [savingPurchase, setSavingPurchase] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importRows, setImportRows] = useState<ImportRow[]>([]);
  const [importCardId, setImportCardId] = useState("");
  const [importing, setImporting] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);
  const { lang, t } = useLanguage();

  const cardMap = useMemo(
    () => new Map(cards.map((card) => [card.id, card])),
    [cards],
  );

  const categoryMap = useMemo(
    () => new Map(categories.map((category) => [category.id, category])),
    [categories],
  );

  const filteredPurchases = useMemo(() => {
    let result = purchases;
    if (selectedCardId !== "all") {
      result = result.filter((purchase) => purchase.credit_card_id === selectedCardId);
    }
    if (hideCompleted) {
      result = result.filter((purchase) => {
        const explicitlyPaid = purchase.installment_rows.filter((installment) => installment.is_paid).length;
        const implicitlyPaid = purchase.installments - purchase.installment_rows.length;
        const totalPaid = explicitlyPaid + implicitlyPaid;
        return totalPaid < purchase.installments;
      });
    }
    return result;
  }, [purchases, selectedCardId, hideCompleted]);

  const load = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);
      const [purchaseRows, cardRows, categoryRows] = await Promise.all([
        purchasesApi.list(),
        creditCardsApi.list(),
        categoriesApi.list(),
      ]);
      setPurchases(purchaseRows);
      setCards(cardRows);
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

  const openCreatePurchase = () => {
    setEditingPurchase(null);
    setPurchaseForm({
      ...EMPTY_PURCHASE_FORM,
      credit_card_id: selectedCardId !== "all" ? selectedCardId : (cards[0]?.id ?? ""),
      purchase_date: today(),
    });
    setPurchaseDialogOpen(true);
  };

  const openEditPurchase = (purchase: Purchase) => {
    setEditingPurchase(purchase);
    const implicitlyPaid = purchase.installments - purchase.installment_rows.length;
    setPurchaseForm({
      credit_card_id: purchase.credit_card_id,
      description: purchase.description,
      installment_amount: purchase.installment_amount,
      installments: purchase.installments,
      starting_installment: implicitlyPaid + 1,
      purchase_date: purchase.purchase_date,
      category_id: purchase.category_id ?? "",
    });
    setPurchaseDialogOpen(true);
  };

  const handlePurchaseSave = async () => {
    setSavingPurchase(true);
    try {
      if (editingPurchase) {
        await purchasesApi.update(editingPurchase.id, {
          ...purchaseForm,
          total_amount: purchaseForm.installment_amount * purchaseForm.installments,
          category_id: purchaseForm.category_id || null,
        });
      } else {
        await purchasesApi.create({
          ...purchaseForm,
          total_amount: purchaseForm.installment_amount * purchaseForm.installments,
          category_id: purchaseForm.category_id || null,
        });
      }
      setPurchaseDialogOpen(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.creditCards.saveError);
    } finally {
      setSavingPurchase(false);
    }
  };

  const handlePurchaseDelete = async (id: string) => {
    if (!confirm(t.creditCards.confirmDelete)) return;
    try {
      await purchasesApi.delete(id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.creditCards.deleteError);
    }
  };

  const handleInstallmentPaid = async (purchase: Purchase) => {
    const nextPending = purchase.installment_rows.find((installment) => !installment.is_paid);
    if (!nextPending) return;
    const card = cardMap.get(purchase.credit_card_id);

    if (!card?.payment_account_id) {
      alert(t.creditCards.paymentAccountRequired);
      return;
    }

    await installmentsApi.update(nextPending.id, {
      is_paid: true,
      paid_account_id: card.payment_account_id,
    });
    await load();
  };


  const openImport = () => {
    setImportRows([]);
    setImportCardId(selectedCardId !== "all" ? selectedCardId : (cards[0]?.id ?? ""));
    setImportDialogOpen(true);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const lines = text.split("\n").map((line) => line.trim()).filter(Boolean);
      const dataLines = lines.slice(1);
      const parsed = dataLines.map((line, index) => {
        const parts = line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/).map((part) => part.replace(/^"|"$/g, "").trim());
        const [date, description, amount, currentInstallment, totalInstallments, category] = parts;

        const startingInstallment = parseInt(currentInstallment) || 1;
        const installments = parseInt(totalInstallments) || 1;

        let matchedCategoryId = "";
        if (category) {
          const match = categories.find((item) => item.name.toLowerCase() === category.toLowerCase());
          if (match) matchedCategoryId = match.id;
        }

        return {
          id: index,
          purchase_date: date || "",
          description: description || "",
          installment_amount: parseFloat(amount) || 0,
          installments,
          starting_installment: startingInstallment,
          category_id: matchedCategoryId,
          category: category || "",
        };
      });
      setImportRows(parsed);
    };
    reader.readAsText(file);
  };

  const handleImportSave = async () => {
    setImporting(true);
    try {
      const payload = importRows.map((row) => ({
        credit_card_id: importCardId,
        description: row.description,
        total_amount: row.installment_amount * row.installments,
        installments: row.installments,
        starting_installment: row.starting_installment,
        purchase_date: row.purchase_date,
        category_id: row.category_id || null,
        category: row.category || null,
      }));
      await purchasesApi.createBulk(payload);
      setImportDialogOpen(false);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.creditCards.importError);
    } finally {
      setImporting(false);
    }
  };

  const money = (amount: number | null, currency?: Currency) => formatAmount(amount, currency, lang, t.creditCards.noLimit);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.creditCards.title}</h1>
          <p className="mt-1 text-muted-foreground">
            {t.creditCards.subtitle}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label className="mr-4 flex cursor-pointer items-center gap-2 text-sm text-muted-foreground hover:text-foreground">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 bg-transparent"
              checked={hideCompleted}
              onChange={(e) => setHideCompleted(e.target.checked)}
            />
            {t.creditCards.hideCompleted}
          </label>

          <Select value={selectedCardId} onValueChange={(v: string | null) => setSelectedCardId(v ?? "all")}>
            <SelectTrigger className="w-[200px]">
              <SelectValue>
                {selectedCardId === "all" ? t.creditCards.allCards : cardMap.get(selectedCardId)?.name}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t.creditCards.allCards}</SelectItem>
              {cards.map((card) => (
                <SelectItem key={card.id} value={card.id}>{card.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Link href="/credit-cards/manage" className={buttonVariants({ variant: "outline", size: "icon" })} title={t.creditCards.manageCards}>
            <Settings size={18} />
          </Link>
        </div>
      </div>

      <div className="flex gap-2">
        <Button variant="outline" onClick={openImport} disabled={cards.length === 0}>
          {t.creditCards.importCsv}
        </Button>
        <Button onClick={openCreatePurchase} disabled={cards.length === 0}>
          {t.creditCards.addExpense}
        </Button>
      </div>

      {cards.length === 0 && !loading && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
          {t.creditCards.noCards}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-sm text-muted-foreground">{t.common.loading}</p>
      ) : filteredPurchases.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
          <p className="text-lg">{t.creditCards.noExpenses}</p>
          <p className="mt-1 text-sm">{t.creditCards.emptyHint}</p>
        </div>
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t.common.date}</TableHead>
                {selectedCardId === "all" && <TableHead>{t.creditCards.card}</TableHead>}
                <TableHead>{t.common.description}</TableHead>
                <TableHead>{t.common.category}</TableHead>
                <TableHead className="text-right">{t.creditCards.total}</TableHead>
                <TableHead>{t.creditCards.payments}</TableHead>
                <TableHead className="text-right">{t.creditCards.perPayment}</TableHead>
                <TableHead>{t.creditCards.firstDue}</TableHead>
                <TableHead className="text-right">{t.common.actions}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredPurchases.map((purchase) => {
                const card = cardMap.get(purchase.credit_card_id);
                const implicitlyPaid = purchase.installments - purchase.installment_rows.length;
                const explicitlyPaid = purchase.installment_rows.filter((installment) => installment.is_paid).length;
                return (
                  <TableRow key={purchase.id}>
                    <TableCell>{formatDate(purchase.purchase_date, lang)}</TableCell>
                    {selectedCardId === "all" && <TableCell className="font-medium">{card?.name ?? t.common.unknown}</TableCell>}
                    <TableCell>{purchase.description}</TableCell>
                    <TableCell className="text-muted-foreground">{purchase.category_id ? categoryMap.get(purchase.category_id)?.name : (purchase.category ?? "-")}</TableCell>
                    <TableCell className="text-right font-mono">{money(purchase.total_amount, card?.currency)}</TableCell>
                    <TableCell>
                      {purchase.installments === 1 ? (
                        <Badge variant="secondary">1x</Badge>
                      ) : (
                        <Badge variant="outline">{purchase.installments}x</Badge>
                      )}
                      <span className="ml-2 text-xs text-muted-foreground">
                        ({implicitlyPaid + explicitlyPaid}/{purchase.installments} {t.creditCards.paid})
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">{money(purchase.installment_amount, card?.currency)}</TableCell>
                    <TableCell>{formatDate(purchase.first_installment_date, lang)}</TableCell>
                    <TableCell className="space-x-2 text-right">
                      <Button variant="ghost" size="sm" onClick={() => handleInstallmentPaid(purchase)} disabled={purchase.installment_rows.every((installment) => installment.is_paid)}>
                        {t.creditCards.payNext}
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => openEditPurchase(purchase)}>{t.common.edit}</Button>
                      <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300" onClick={() => handlePurchaseDelete(purchase.id)}>
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

      <Dialog open={purchaseDialogOpen} onOpenChange={setPurchaseDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingPurchase ? t.creditCards.editDialog : t.creditCards.addDialog}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>{t.creditCards.creditCard}</Label>
              <Select
                value={purchaseForm.credit_card_id}
                onValueChange={(v: string | null) => setPurchaseForm({ ...purchaseForm, credit_card_id: v ?? "" })}
              >
                <SelectTrigger className="min-w-0">
                  <span className="block truncate text-sm">
                    {cardMap.get(purchaseForm.credit_card_id)?.name ?? t.creditCards.selectCreditCard}
                  </span>
                </SelectTrigger>
                <SelectContent>
                  {cards.map((card) => (
                    <SelectItem key={card.id} value={card.id}>{card.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="purchase-description">{t.common.description}</Label>
              <Input
                id="purchase-description"
                placeholder={t.creditCards.placeholderDescription}
                value={purchaseForm.description}
                onChange={(e) => setPurchaseForm({ ...purchaseForm, description: e.target.value })}
              />
            </div>

            <div className="space-y-1.5">
              <Label>{t.common.category}</Label>
              <Select
                value={purchaseForm.category_id}
                onValueChange={(v: string | null) => setPurchaseForm({ ...purchaseForm, category_id: v ?? "" })}
              >
                <SelectTrigger>
                  <span className="block truncate text-sm">
                    {purchaseForm.category_id ? categoryMap.get(purchaseForm.category_id)?.name : t.common.none}
                  </span>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">{t.common.none}</SelectItem>
                  {categories.filter((category) => category.type === "expense" || category.type === "both").map((category) => (
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

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="installment-amount">{t.creditCards.installmentAmount}</Label>
                <Input
                  id="installment-amount"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0"
                  value={purchaseForm.installment_amount === 0 ? "" : purchaseForm.installment_amount}
                  onChange={(e) => setPurchaseForm({ ...purchaseForm, installment_amount: parseFloat(e.target.value) || 0 })}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="purchase-date">{t.creditCards.statementDate}</Label>
                <Input
                  id="purchase-date"
                  type="date"
                  value={purchaseForm.purchase_date}
                  onChange={(e) => setPurchaseForm({ ...purchaseForm, purchase_date: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="starting-installment">{t.creditCards.currentInstallment}</Label>
                <Input
                  id="starting-installment"
                  type="number"
                  min={1}
                  value={purchaseForm.starting_installment}
                  onFocus={(e) => e.currentTarget.select()}
                  onChange={(e) => setPurchaseForm({ ...purchaseForm, starting_installment: parseInt(e.target.value) || 1 })}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="installments">{t.creditCards.totalInstallments}</Label>
                <Input
                  id="installments"
                  type="number"
                  min={1}
                  value={purchaseForm.installments}
                  onFocus={(e) => e.currentTarget.select()}
                  onChange={(e) => setPurchaseForm({ ...purchaseForm, installments: parseInt(e.target.value) || 1 })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPurchaseDialogOpen(false)}>{t.common.cancel}</Button>
            <Button
              onClick={handlePurchaseSave}
              disabled={
                savingPurchase ||
                !purchaseForm.credit_card_id ||
                !purchaseForm.description ||
                purchaseForm.installment_amount <= 0 ||
                purchaseForm.installments < 1 ||
                purchaseForm.starting_installment > purchaseForm.installments ||
                !purchaseForm.purchase_date
              }
            >
              {savingPurchase ? t.common.saving : t.common.save}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t.creditCards.importTitle}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>{t.creditCards.creditCard}</Label>
                <Select value={importCardId} onValueChange={(v: string | null) => setImportCardId(v ?? "")}>
                  <SelectTrigger className="min-w-0">
                    <span className="block truncate text-sm">{cardMap.get(importCardId)?.name ?? t.common.select}</span>
                  </SelectTrigger>
                  <SelectContent>
                    {cards.map((card) => <SelectItem key={card.id} value={card.id}>{card.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>{t.creditCards.csvFile}</Label>
                <Input type="file" accept=".csv" onChange={handleFileUpload} />
              </div>
            </div>

            <div className="space-y-1 text-xs">
              <p className="font-medium text-foreground/70">{t.creditCards.expectedFormat}</p>
              <p className="font-mono text-yellow-500">date, description, amount, current_installment, total_installments, category</p>
              <p className="font-mono text-yellow-500/80">2026-05-03, Supermarket, 150.50, 1, 1, Groceries</p>
              <p className="font-mono text-yellow-500/80">2026-05-01, New Laptop, 100.00, 12, 18, Electronics</p>
            </div>

            {importRows.length > 0 && (
              <p className="text-sm font-medium text-green-500">{t.creditCards.readyToImport.replace("{count}", String(importRows.length))}</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setImportDialogOpen(false)}>{t.common.cancel}</Button>
            <Button onClick={handleImportSave} disabled={importing || importRows.length === 0 || !importCardId}>
              {importing ? t.creditCards.importing : t.creditCards.confirmImport}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
