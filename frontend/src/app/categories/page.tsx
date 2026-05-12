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

  const load = async () => {
    try {
      setLoading(true);
      setItems(await categoriesApi.list());
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "No se pudieron cargar las categorías");
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/set-state-in-effect
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
    if (!confirm("Eliminar esta categoría?")) return;
    await categoriesApi.delete(id);
    await load();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Categorías</h1>
          <p className="mt-1 text-muted-foreground">Administra nombres, colores e iconos para clasificar movimientos.</p>
        </div>
        <Button onClick={openCreate}>+ Agregar categoría</Button>
      </div>

      {error && <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</div>}

      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nombre</TableHead>
              <TableHead>Tipo</TableHead>
              <TableHead>Color</TableHead>
              <TableHead>Icono</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead className="text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={6}>Cargando...</TableCell></TableRow>
            ) : items.length === 0 ? (
              <TableRow><TableCell colSpan={6}>Sin categorías.</TableCell></TableRow>
            ) : items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-medium">{item.name}</TableCell>
                <TableCell><Badge variant="outline">{item.type}</Badge></TableCell>
                <TableCell><span className="inline-flex items-center gap-2"><span className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />{item.color}</span></TableCell>
                <TableCell className="text-muted-foreground">{item.icon ?? "-"}</TableCell>
                <TableCell>{item.is_active ? "Activa" : "Inactiva"}</TableCell>
                <TableCell className="space-x-2 text-right">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(item)}>Editar</Button>
                  <Button variant="ghost" size="sm" className="text-red-400" onClick={() => remove(item.id)}>Eliminar</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editing ? "Editar categoría" : "Agregar categoría"}</DialogTitle></DialogHeader>
          <div className="space-y-4 py-2">
            <Field label="Nombre"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Tipo">
                <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: (v ?? "expense") as CategoryType })}>
                  <SelectTrigger><span className="text-sm">{form.type}</span></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="income">income</SelectItem>
                    <SelectItem value="expense">expense</SelectItem>
                    <SelectItem value="both">both</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Field label="Color"><Input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} /></Field>
            </div>
            <Field label="Icono"><Input value={form.icon ?? ""} onChange={(e) => setForm({ ...form, icon: e.target.value })} placeholder="home, receipt, car" /></Field>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />Activa</label>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancelar</Button>
            <Button onClick={save} disabled={!form.name}>Guardar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-1.5"><Label>{label}</Label>{children}</div>;
}
