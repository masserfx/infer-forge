"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getOperations, createOperation, updateOperation, deleteOperation } from "@/lib/api";
import type { Operation, OperationCreate } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Wrench, Plus, Trash2, Pencil } from "lucide-react";
import { toast } from "sonner";

const STATUS_LABELS: Record<string, string> = {
  planned: "Plánováno",
  in_progress: "Probíhá",
  completed: "Dokončeno",
  cancelled: "Zrušeno",
};

const STATUS_COLORS: Record<string, string> = {
  planned: "bg-gray-100 text-gray-800",
  in_progress: "bg-blue-100 text-blue-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

interface OrderOperationsProps {
  orderId: string;
}

export function OrderOperations({ orderId }: OrderOperationsProps) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingOp, setEditingOp] = useState<Operation | null>(null);
  const [formData, setFormData] = useState<Partial<OperationCreate>>({});

  const { data: operations = [], isLoading } = useQuery({
    queryKey: ["operations", orderId],
    queryFn: () => getOperations(orderId),
  });

  const createMut = useMutation({
    mutationFn: (data: OperationCreate) => createOperation(orderId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operations", orderId] });
      toast.success("Operace vytvořena");
      setDialogOpen(false);
      setFormData({});
    },
    onError: () => toast.error("Chyba při vytváření operace"),
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      updateOperation(orderId, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operations", orderId] });
      toast.success("Operace aktualizována");
      setDialogOpen(false);
      setEditingOp(null);
      setFormData({});
    },
    onError: () => toast.error("Chyba při aktualizaci operace"),
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteOperation(orderId, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["operations", orderId] });
      toast.success("Operace smazána");
    },
    onError: () => toast.error("Chyba při mazání operace"),
  });

  const handleSubmit = () => {
    if (!formData.name) {
      toast.error("Název operace je povinný");
      return;
    }
    if (editingOp) {
      updateMut.mutate({ id: editingOp.id, data: formData });
    } else {
      createMut.mutate({
        name: formData.name,
        sequence: formData.sequence ?? operations.length + 1,
        description: formData.description,
        duration_hours: formData.duration_hours,
        responsible: formData.responsible,
        planned_start: formData.planned_start,
        planned_end: formData.planned_end,
        notes: formData.notes,
      });
    }
  };

  const openEdit = (op: Operation) => {
    setEditingOp(op);
    setFormData({
      name: op.name,
      description: op.description ?? undefined,
      sequence: op.sequence,
      duration_hours: op.duration_hours ?? undefined,
      responsible: op.responsible ?? undefined,
      notes: op.notes ?? undefined,
    });
    setDialogOpen(true);
  };

  const openCreate = () => {
    setEditingOp(null);
    setFormData({ sequence: operations.length + 1 });
    setDialogOpen(true);
  };

  const handleStatusChange = (op: Operation, newStatus: string) => {
    updateMut.mutate({ id: op.id, data: { status: newStatus } });
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleDateString("cs-CZ");
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wrench className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-xl font-semibold">Výrobní operace</h2>
          <span className="text-sm text-muted-foreground">
            ({operations.length})
          </span>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm" onClick={openCreate}>
              <Plus className="mr-1 h-4 w-4" />
              Přidat operaci
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                {editingOp ? "Upravit operaci" : "Nová operace"}
              </DialogTitle>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="op-name">Název *</Label>
                <Input
                  id="op-name"
                  value={formData.name ?? ""}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Např. Řezání, Svařování, Tryskání..."
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label htmlFor="op-seq">Pořadí</Label>
                  <Input
                    id="op-seq"
                    type="number"
                    min={1}
                    value={formData.sequence ?? ""}
                    onChange={(e) => setFormData({ ...formData, sequence: parseInt(e.target.value) || 1 })}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="op-dur">Doba (hod)</Label>
                  <Input
                    id="op-dur"
                    type="number"
                    step="0.5"
                    min={0}
                    value={formData.duration_hours ?? ""}
                    onChange={(e) => setFormData({ ...formData, duration_hours: parseFloat(e.target.value) || undefined })}
                  />
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="op-resp">Odpovědný</Label>
                <Input
                  id="op-resp"
                  value={formData.responsible ?? ""}
                  onChange={(e) => setFormData({ ...formData, responsible: e.target.value || undefined })}
                  placeholder="Jméno nebo tým"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="op-desc">Popis</Label>
                <Textarea
                  id="op-desc"
                  value={formData.description ?? ""}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value || undefined })}
                  rows={2}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="op-notes">Poznámky</Label>
                <Textarea
                  id="op-notes"
                  value={formData.notes ?? ""}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value || undefined })}
                  rows={2}
                />
              </div>
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline">Zrušit</Button>
              </DialogClose>
              <Button onClick={handleSubmit} disabled={createMut.isPending || updateMut.isPending}>
                {editingOp ? "Uložit" : "Vytvořit"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : operations.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
          Žádné operace. Přidejte první operaci tlačítkem výše.
        </div>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">#</TableHead>
                <TableHead>Název</TableHead>
                <TableHead className="w-20">Doba (h)</TableHead>
                <TableHead>Odpovědný</TableHead>
                <TableHead>Plán. start</TableHead>
                <TableHead>Plán. konec</TableHead>
                <TableHead className="w-36">Stav</TableHead>
                <TableHead className="w-20">Akce</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {operations.map((op) => (
                <TableRow key={op.id}>
                  <TableCell className="font-mono text-muted-foreground">
                    {op.sequence}
                  </TableCell>
                  <TableCell>
                    <div>
                      <span className="font-medium">{op.name}</span>
                      {op.description && (
                        <p className="text-xs text-muted-foreground">{op.description}</p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>{op.duration_hours ?? "—"}</TableCell>
                  <TableCell>{op.responsible ?? "—"}</TableCell>
                  <TableCell className="text-sm">{formatDate(op.planned_start)}</TableCell>
                  <TableCell className="text-sm">{formatDate(op.planned_end)}</TableCell>
                  <TableCell>
                    <Select
                      value={op.status}
                      onValueChange={(val) => handleStatusChange(op, val)}
                    >
                      <SelectTrigger className="h-7 w-full">
                        <SelectValue>
                          <Badge variant="outline" className={STATUS_COLORS[op.status]}>
                            {STATUS_LABELS[op.status]}
                          </Badge>
                        </SelectValue>
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(STATUS_LABELS).map(([value, label]) => (
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => openEdit(op)}
                        aria-label="Upravit operaci"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-destructive"
                            aria-label="Smazat operaci"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Smazat operaci?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Opravdu chcete smazat operaci &quot;{op.name}&quot;? Tuto akci nelze vrátit.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Zrušit</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => deleteMut.mutate(op.id)}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            >
                              Smazat
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
