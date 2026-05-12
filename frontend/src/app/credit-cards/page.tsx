"use client";

import { useEffect, useMemo, useState } from "react";
import {
  accountsApi,
  categoriesApi,
  creditCardsApi,
  installmentsApi,
  purchasesApi,
  type CreditCard,
  type Purchase,
  type Currency,
  type Category,
} from "@/lib/api";
import Link from "next/link";
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
import { Settings } from "lucide-react";

interface PurchaseForm {
  credit_card_id: string;
  description: string;
  installment_amount: number;
  installments: number;
  starting_installment: number;
  purchase_date: string;
  category_id: string;
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

function formatDate(value: string) {
  return new Date(`${value}T00:00:00`).toLocaleDateString("en-US");
}

function formatAmount(amount: number | null, currency?: Currency) {
  if (amount === null) return "No limit";
  if (!currency) return amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${currency.symbol} ${amount.toLocaleString("en-US", {
    minimumFractionDigits: currency.decimal_places,
    maximumFractionDigits: currency.decimal_places,
  })}`;
}

export default function CreditCardsPage() {
  const [purchases, setPurchases] = useState<Purchase[]>([]);
  const [cards, setCards] = useState<CreditCard[]>([]);

  const [selectedCardId, setSelectedCardId] = useState<string>("all");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Purchase Dialog state
  const [purchaseDialogOpen, setPurchaseDialogOpen] = useState(false);
  const [editingPurchase, setEditingPurchase] = useState<Purchase | null>(null);
  const [purchaseForm, setPurchaseForm] = useState<PurchaseForm>(EMPTY_PURCHASE_FORM);
  const [savingPurchase, setSavingPurchase] = useState(false);

  // Import Dialog state
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importRows, setImportRows] = useState<any[]>([]);
  const [importCardId, setImportCardId] = useState("");
  const [importing, setImporting] = useState(false);
  const [categories, setCategories] = useState<Category[]>([]);

  const cardMap = useMemo(
    () => new Map(cards.map((card) => [card.id, card])),
    [cards],
  );

  const categoryMap = useMemo(
    () => new Map(categories.map((c) => [c.id, c])),
    [categories],
  );

  const filteredPurchases = useMemo(() => {
    if (selectedCardId === "all") return purchases;
    return purchases.filter((p) => p.credit_card_id === selectedCardId);
  }, [purchases, selectedCardId]);

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
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { void load(false); }, []);

  // --- Purchase Handlers ---
  const openCreatePurchase = () => {
    setEditingPurchase(null);
    setPurchaseForm({
      ...EMPTY_PURCHASE_FORM,
      credit_card_id: selectedCardId !== "all" ? selectedCardId : (cards[0]?.id ?? ""),
      purchase_date: today()
    });
    setPurchaseDialogOpen(true);
  };

  const openEditPurchase = (purchase: Purchase) => {
    setEditingPurchase(purchase);
    setPurchaseForm({
      credit_card_id: purchase.credit_card_id,
      description: purchase.description,
      installment_amount: purchase.installment_amount,
      installments: purchase.installments,
      starting_installment: 1, // Updates don't change installments
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
          description: purchaseForm.description,
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
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSavingPurchase(false);
    }
  };

  const handlePurchaseDelete = async (id: string) => {
    if (!confirm("Delete this purchase? This will also delete its installments.")) return;
    try {
      await purchasesApi.delete(id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  // --- Installment Payment Handlers ---
  const handleInstallmentPaid = async (purchase: Purchase) => {
    const nextPending = purchase.installment_rows.find((installment) => !installment.is_paid);
    if (!nextPending) return;
    const card = cardMap.get(purchase.credit_card_id);

    if (!card?.payment_account_id) {
      alert("Please link a payment account (e.g. checking account) to this credit card in 'Manage Cards' before paying.");
      return;
    }

    await installmentsApi.update(nextPending.id, {
      is_paid: true,
      paid_account_id: card.payment_account_id,
    });
    await load();
  };

  const handleInstallmentReopen = async (purchase: Purchase) => {
    const lastPaid = [...purchase.installment_rows].reverse().find((installment) => installment.is_paid);
    if (!lastPaid) return;
    await installmentsApi.update(lastPaid.id, { is_paid: false, paid_account_id: null });
    await load();
  };

  // --- Import Handlers ---
  const openImport = () => {
    setImportRows([]);
    setImportCardId(selectedCardId !== "all" ? selectedCardId : (cards[0]?.id ?? ""));
    setImportDialogOpen(true);
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
      const dataLines = lines.slice(1);
      const parsed = dataLines.map((line, index) => {
        const parts = line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/).map(s => s.replace(/^"|"$/g, '').trim());
        const [date, description, amount, current_inst_str, total_inst_str, category] = parts;
        
        let starting_installment = parseInt(current_inst_str) || 1;
        let total_installments = parseInt(total_inst_str) || 1;

        let matchedCategoryId = "";
        if (category) {
          const match = categories.find(c => c.name.toLowerCase() === category.toLowerCase());
          if (match) matchedCategoryId = match.id;
        }

        return {
          id: index,
          purchase_date: date || "",
          description: description || "",
          installment_amount: parseFloat(amount) || 0,
          installments: total_installments,
          starting_installment: starting_installment,
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
      const payload = importRows.map(row => ({
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
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Credit Cards</h1>
          <p className="text-muted-foreground mt-1">
            Track card expenses, installments, and statement dues.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Select value={selectedCardId} onValueChange={(v: string | null) => setSelectedCardId(v ?? "all")}>
            <SelectTrigger className="w-[200px]">
              <SelectValue>
                {selectedCardId === "all" ? "All Cards" : cardMap.get(selectedCardId)?.name}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Cards</SelectItem>
              {cards.map(card => (
                <SelectItem key={card.id} value={card.id}>{card.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Link href="/credit-cards/manage" className={buttonVariants({ variant: "outline", size: "icon" })} title="Manage Cards">
            <Settings size={18} />
          </Link>
        </div>
      </div>

      <div className="flex gap-2">
        <Button variant="outline" onClick={openImport} disabled={cards.length === 0}>
          Import CSV
        </Button>
        <Button onClick={openCreatePurchase} disabled={cards.length === 0}>
          + Add Card Expense
        </Button>
      </div>

      {cards.length === 0 && !loading && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-400">
          No credit cards found. Click the gear icon above to add your first card.
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-muted-foreground text-sm">Loading...</p>
      ) : filteredPurchases.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-12 text-center text-muted-foreground">
          <p className="text-lg">No card expenses yet.</p>
          <p className="text-sm mt-1">Click "+ Add Card Expense" to create your first one.</p>
        </div>
      ) : (
        <div className="rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                {selectedCardId === "all" && <TableHead>Card</TableHead>}
                <TableHead>Description</TableHead>
                <TableHead>Category</TableHead>
                <TableHead className="text-right">Total</TableHead>
                <TableHead>Payments</TableHead>
                <TableHead className="text-right">Per Payment</TableHead>
                <TableHead>First Due</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredPurchases.map((purchase) => {
                const card = cardMap.get(purchase.credit_card_id);
                return (
                  <TableRow key={purchase.id}>
                    <TableCell>{formatDate(purchase.purchase_date)}</TableCell>
                    {selectedCardId === "all" && <TableCell className="font-medium">{card?.name ?? "Unknown"}</TableCell>}
                    <TableCell>{purchase.description}</TableCell>
                    <TableCell className="text-muted-foreground">{purchase.category_id ? categoryMap.get(purchase.category_id)?.name : (purchase.category ?? "-")}</TableCell>
                    <TableCell className="text-right font-mono">{formatAmount(purchase.total_amount, card?.currency)}</TableCell>
                    <TableCell>
                      {purchase.installments === 1 ? (
                        <Badge variant="secondary">1x</Badge>
                      ) : (
                        <Badge variant="outline">{purchase.installments}x</Badge>
                      )}
                      <span className="ml-2 text-muted-foreground text-xs">
                        {(() => {
                          const implicitlyPaid = purchase.installments - purchase.installment_rows.length;
                          const explicitlyPaid = purchase.installment_rows.filter((i) => i.is_paid).length;
                          return `(${implicitlyPaid + explicitlyPaid}/${purchase.installments} paid)`;
                        })()}
                      </span>
                    </TableCell>
                    <TableCell className="text-right font-mono">{formatAmount(purchase.installment_amount, card?.currency)}</TableCell>
                    <TableCell>{formatDate(purchase.first_installment_date)}</TableCell>
                    <TableCell className="text-right space-x-2">
                      <Button variant="ghost" size="sm" onClick={() => handleInstallmentPaid(purchase)} disabled={purchase.installment_rows.every((i) => i.is_paid)}>
                        Pay next
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleInstallmentReopen(purchase)} disabled={purchase.installment_rows.every((i) => !i.is_paid)}>
                        Reopen
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => openEditPurchase(purchase)}>Edit</Button>
                      <Button variant="ghost" size="sm" className="text-red-400 hover:text-red-300" onClick={() => handlePurchaseDelete(purchase.id)}>
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      {/* --- Purchase Dialog --- */}
      <Dialog open={purchaseDialogOpen} onOpenChange={setPurchaseDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingPurchase ? "Edit Card Expense" : "Add Card Expense"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label>Credit Card</Label>
              <Select
                value={purchaseForm.credit_card_id}
                onValueChange={(v: string | null) => setPurchaseForm({ ...purchaseForm, credit_card_id: v ?? "" })}
                disabled={!!editingPurchase}
              >
                <SelectTrigger className="min-w-0">
                  <span className="text-sm truncate block">
                    {cardMap.get(purchaseForm.credit_card_id)?.name ?? "Select credit card"}
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
              <Label htmlFor="purchase-description">Description</Label>
              <Input
                id="purchase-description"
                placeholder="e.g. Supermarket, Laptop..."
                value={purchaseForm.description}
                onChange={(e) => setPurchaseForm({ ...purchaseForm, description: e.target.value })}
              />
            </div>

            <div className="space-y-1.5">
              <Label>Category</Label>
              <Select
                value={purchaseForm.category_id}
                onValueChange={(v: string | null) => setPurchaseForm({ ...purchaseForm, category_id: v ?? "" })}
              >
                <SelectTrigger>
                  <span className="text-sm truncate block">
                    {purchaseForm.category_id ? categoryMap.get(purchaseForm.category_id)?.name : "None"}
                  </span>
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None</SelectItem>
                  {categories.filter(c => c.type === "expense").map(c => (
                    <SelectItem key={c.id} value={c.id}>
                      <div className="flex items-center gap-2">
                        <div className="h-3 w-3 rounded-full" style={{ backgroundColor: c.color }} />
                        {c.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="installment-amount">Installment Amount</Label>
                <Input
                  id="installment-amount"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0"
                  value={purchaseForm.installment_amount === 0 ? "" : purchaseForm.installment_amount}
                  onChange={(e) => setPurchaseForm({ ...purchaseForm, installment_amount: parseFloat(e.target.value) || 0 })}
                  disabled={!!editingPurchase}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="purchase-date">Statement Date</Label>
                <Input
                  id="purchase-date"
                  type="date"
                  value={purchaseForm.purchase_date}
                  onChange={(e) => setPurchaseForm({ ...purchaseForm, purchase_date: e.target.value })}
                  disabled={!!editingPurchase}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="starting-installment">Current Installment</Label>
                <Input
                  id="starting-installment"
                  type="number"
                  min={1}
                  value={purchaseForm.starting_installment}
                  onFocus={(e) => e.currentTarget.select()}
                  onChange={(e) => setPurchaseForm({ ...purchaseForm, starting_installment: parseInt(e.target.value) || 1 })}
                  disabled={!!editingPurchase}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="installments">Total Installments</Label>
                <Input
                  id="installments"
                  type="number"
                  min={1}
                  value={purchaseForm.installments}
                  onFocus={(e) => e.currentTarget.select()}
                  onChange={(e) => setPurchaseForm({ ...purchaseForm, installments: parseInt(e.target.value) || 1 })}
                  disabled={!!editingPurchase}
                />
              </div>
            </div>
            {editingPurchase && (
              <p className="text-xs text-muted-foreground">
                Amount, card, installments, and purchase date are locked because they determine generated installments.
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPurchaseDialogOpen(false)}>Cancel</Button>
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
              {savingPurchase ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* --- Import Dialog --- */}
      <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Import Expenses from CSV</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Credit Card</Label>
                <Select value={importCardId} onValueChange={(v: string | null) => setImportCardId(v ?? "")}>
                  <SelectTrigger className="min-w-0">
                    <span className="text-sm truncate block">{cardMap.get(importCardId)?.name ?? "Select"}</span>
                  </SelectTrigger>
                  <SelectContent>
                    {cards.map((c) => <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>CSV File</Label>
                <Input type="file" accept=".csv" onChange={handleFileUpload} />
              </div>
            </div>

            <div className="text-xs space-y-1">
              <p className="font-medium text-foreground/70">Expected format:</p>
              <p className="font-mono text-yellow-500">date, description, amount, current_installment, total_installments, category</p>
              <p className="font-mono text-yellow-500/80">2026-05-03, Supermarket, 150.50, 1, 1, Groceries</p>
              <p className="font-mono text-yellow-500/80">2026-05-01, New Laptop, 100.00, 12, 18, Electronics</p>
            </div>

            {importRows.length > 0 && (
              <p className="text-sm text-green-500 font-medium">Ready to import {importRows.length} valid row(s).</p>
            )}
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setImportDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleImportSave} disabled={importing || importRows.length === 0 || !importCardId}>
              {importing ? "Importing..." : "Confirm Import"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
