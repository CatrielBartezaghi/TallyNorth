"use client";

import { useEffect, useState } from "react";
import { categoriesApi, type Category, type CategoryPayload, type CategoryType } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useLanguage } from "@/lib/LanguageContext";

const EMPTY: CategoryPayload = {
  name: "",
  type: "expense",
  color: "#38bdf8",
  icon: "",
  is_active: true,
};

export default function CategoriesPage() {
  const [items, setItems] = useState<Category[]>([]);
  const [form, setForm] = useState<CategoryPayload>(EMPTY);
  const [editing, setEditing] = useState<Category | null>(null);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { t } = useLanguage();

  const load = async () => {
    try {
      setLoading(true);
      setItems(await categoriesApi.list());
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.categories.loadError);
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect, react-hooks/exhaustive-deps
  useEffect(() => { void load(); }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY);
    setOpen(true);
  };

  const openEdit = (item: Category) => {
    setEditing(item);
    setForm({
      name: item.name,
      type: item.type,
      color: item.color,
      icon: item.icon ?? "",
      is_active: item.is_active,
    });
    setOpen(true);
  };

  const save = async () => {
    const payload = { ...form, icon: form.icon || null };
    if (editing) await categoriesApi.update(editing.id, payload);
    else await categoriesApi.create(payload);
    setOpen(false);
    await load();
  };

  const remove = async (id: string) => {
    if (!confirm(t.categories.confirmDelete)) return;
    await categoriesApi.delete(id);
    await load();
  };

  const typeLabel = (type: CategoryType) => t.enums[type];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t.categories.title}</h1>
          <p className="mt-1 text-muted-foreground">{t.categories.subtitle}</p>
        </div>
        <Button onClick={openCreate}>{t.categories.add}</Button>
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t.common.name}</TableHead>
              <TableHead>{t.common.type}</TableHead>
              <TableHead>{t.common.color}</TableHead>
              <TableHead>{t.categories.icon}</TableHead>
              <TableHead>{t.categories.status}</TableHead>
              <TableHead className="text-right">{t.common.actions}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={6}>{t.common.loading}</TableCell></TableRow>
            ) : items.length === 0 ? (
              <TableRow><TableCell colSpan={6}>{t.categories.noCategories}</TableCell></TableRow>
            ) : items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-medium">{item.name}</TableCell>
                <TableCell><Badge variant="outline">{typeLabel(item.type)}</Badge></TableCell>
                <TableCell><span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />{item.color}</span></TableCell>
                <TableCell className="text-muted-foreground">{item.icon ?? "-"}</TableCell>
                <TableCell>{item.is_active ? t.common.active : t.common.inactive}</TableCell>
                <TableCell className="space-x-2 text-right">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(item)}>{t.common.edit}</Button>
                  <Button variant="ghost" size="sm" className="text-red-400" onClick={() => remove(item.id)}>{t.common.delete}</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? t.categories.editDialog : t.categories.addDialog}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <Field label={t.common.name}><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label={t.common.type}>
                <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: (v ?? "expense") as CategoryType })}>
                  <SelectTrigger><span className="text-sm">{typeLabel(form.type)}</span></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="income">{t.enums.income}</SelectItem>
                    <SelectItem value="expense">{t.enums.expense}</SelectItem>
                    <SelectItem value="both">{t.enums.both}</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label={t.common.color}><Input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} /></Field>
            </div>
            <Field label={t.categories.icon}><Input value={form.icon ?? ""} onChange={(e) => setForm({ ...form, icon: e.target.value })} placeholder={t.categories.placeholderIcon} /></Field>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />{t.common.active}</label>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>{t.common.cancel}</Button>
            <Button onClick={save} disabled={!form.name}>{t.common.save}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}
