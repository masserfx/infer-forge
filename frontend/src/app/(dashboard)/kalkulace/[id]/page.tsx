"use client";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
  addCalculationItem,
  generateOffer,
  getCalculation,
  getOrder,
  removeCalculationItem,
  updateCalculation,
  updateCalculationItem,
  getAIEstimate,
  getCalculationAnomalies,
} from "@/lib/api";
import { MaterialCombobox } from "@/components/material-combobox";
import { formatCurrency } from "@/lib/utils";
import {
  CALCULATION_STATUS_LABELS,
  COST_TYPE_COLORS,
  COST_TYPE_LABELS,
  type CalculationItem,
  type CalculationStatus,
  type CostType,
  type MaterialPrice,
} from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Edit2,
  FileText,
  Plus,
  Trash2,
  Sparkles,
  AlertTriangle as WarningIcon,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

export default function CalculationDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const queryClient = useQueryClient();

  const [isAddItemDialogOpen, setIsAddItemDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isOfferDialogOpen, setIsOfferDialogOpen] = useState(false);
  const [isAIEstimateOpen, setIsAIEstimateOpen] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<string | null>(null);
  const [itemToEdit, setItemToEdit] = useState<CalculationItem | null>(null);

  const { data: calculation, isLoading } = useQuery({
    queryKey: ["calculation", id],
    queryFn: () => getCalculation(id),
    enabled: !!id,
  });

  const { data: order } = useQuery({
    queryKey: ["order", calculation?.order_id],
    queryFn: () => getOrder(calculation!.order_id),
    enabled: !!calculation?.order_id,
  });

  const [newItem, setNewItem] = useState({
    cost_type: "material" as CostType,
    name: "",
    description: "",
    quantity: 1,
    unit: "ks",
    unit_price: 0,
  });

  const [editData, setEditData] = useState({
    name: "",
    margin_percent: 20,
    status: "draft" as CalculationStatus,
    note: "",
  });

  const [offerData, setOfferData] = useState({
    offer_number: "",
    valid_days: 30,
  });

  const addItemMutation = useMutation({
    mutationFn: (item: typeof newItem) => addCalculationItem(id, item),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calculation", id] });
      setIsAddItemDialogOpen(false);
      setNewItem({
        cost_type: "material",
        name: "",
        description: "",
        quantity: 1,
        unit: "ks",
        unit_price: 0,
      });
    },
  });

  const updateItemMutation = useMutation({
    mutationFn: ({
      itemId,
      data,
    }: {
      itemId: string;
      data: Partial<CalculationItem>;
    }) => updateCalculationItem(id, itemId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calculation", id] });
      setItemToEdit(null);
    },
  });

  const deleteItemMutation = useMutation({
    mutationFn: (itemId: string) => removeCalculationItem(id, itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calculation", id] });
      setItemToDelete(null);
    },
  });

  const updateCalcMutation = useMutation({
    mutationFn: (data: typeof editData) => updateCalculation(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["calculation", id] });
      setIsEditDialogOpen(false);
    },
  });

  const generateOfferMutation = useMutation({
    mutationFn: (data: typeof offerData) =>
      generateOffer(id, data.offer_number, data.valid_days),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["calculation", id] });
      setIsOfferDialogOpen(false);
      alert(
        `Nabídka ${data.number} byla vygenerována. Celková cena: ${data.total_price}`,
      );
    },
  });

  const aiEstimateMutation = useMutation({
    mutationFn: () => getAIEstimate(calculation?.order_id || ""),
  });

  const { data: anomalies } = useQuery({
    queryKey: ["anomalies", id],
    queryFn: () => getCalculationAnomalies(id),
    enabled: !!id,
  });

  const handleAddItem = (e: React.FormEvent) => {
    e.preventDefault();
    addItemMutation.mutate(newItem);
  };

  const handleUpdateItem = (e: React.FormEvent) => {
    e.preventDefault();
    if (!itemToEdit) return;
    updateItemMutation.mutate({
      itemId: itemToEdit.id,
      data: {
        name: itemToEdit.name,
        description: itemToEdit.description,
        quantity: itemToEdit.quantity,
        unit: itemToEdit.unit,
        unit_price: itemToEdit.unit_price,
        cost_type: itemToEdit.cost_type,
      },
    });
  };

  const handleUpdateCalculation = (e: React.FormEvent) => {
    e.preventDefault();
    updateCalcMutation.mutate(editData);
  };

  const handleGenerateOffer = (e: React.FormEvent) => {
    e.preventDefault();
    generateOfferMutation.mutate(offerData);
  };

  const openEditDialog = () => {
    if (calculation) {
      setEditData({
        name: calculation.name,
        margin_percent: calculation.margin_percent,
        status: calculation.status,
        note: calculation.note || "",
      });
      setIsEditDialogOpen(true);
    }
  };

  const groupedItems = calculation?.items.reduce(
    (acc, item) => {
      if (!acc[item.cost_type]) {
        acc[item.cost_type] = [];
      }
      acc[item.cost_type].push(item);
      return acc;
    },
    {} as Record<CostType, CalculationItem[]>,
  );

  const getStatusBadgeVariant = (
    status: CalculationStatus,
  ): "default" | "secondary" | "outline" => {
    switch (status) {
      case "draft":
        return "outline";
      case "approved":
        return "default";
      case "offered":
        return "secondary";
      default:
        return "outline";
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
          <p className="mt-4 text-sm text-muted-foreground">
            Načítání kalkulace...
          </p>
        </div>
      </div>
    );
  }

  if (!calculation) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card>
          <CardContent className="pt-6">
            <p className="text-center">Kalkulace nenalezena</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/kalkulace">
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">
                {calculation.name}
              </h1>
              <Badge variant={getStatusBadgeVariant(calculation.status)}>
                {CALCULATION_STATUS_LABELS[calculation.status]}
              </Badge>
            </div>
            <p className="text-muted-foreground">
              Zakázka: {order?.number} | {order?.customer?.company_name}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={openEditDialog}>
            <Edit2 className="mr-2 h-4 w-4" />
            Upravit
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setIsAIEstimateOpen(true);
              aiEstimateMutation.mutate();
            }}
          >
            <Sparkles className="mr-2 h-4 w-4" />
            AI Kalkulace
          </Button>
          {calculation.status === "approved" && (
            <Button onClick={() => setIsOfferDialogOpen(true)}>
              <FileText className="mr-2 h-4 w-4" />
              Generovat nabídku
            </Button>
          )}
        </div>
      </div>

      {/* Anomaly Warning */}
      {anomalies?.anomalies && anomalies.anomalies.length > 0 && (
        <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-4">
          <div className="flex items-center gap-2 mb-2">
            <WarningIcon className="h-5 w-5 text-yellow-600" />
            <h3 className="font-medium text-yellow-900">Upozornění na anomálie</h3>
          </div>
          {anomalies.anomalies.map((a: { type: string; message: string }, i: number) => (
            <p key={i} className="text-sm text-yellow-800">{a.message}</p>
          ))}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Materiál</CardDescription>
            <CardTitle className="text-2xl">
              {formatCurrency(calculation.material_total)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Práce</CardDescription>
            <CardTitle className="text-2xl">
              {formatCurrency(calculation.labor_total)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Kooperace</CardDescription>
            <CardTitle className="text-2xl">
              {formatCurrency(calculation.cooperation_total)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Režie</CardDescription>
            <CardTitle className="text-2xl">
              {formatCurrency(calculation.overhead_total)}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Margin and Total */}
      <Card>
        <CardHeader>
          <CardTitle>Celková cena</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                Součet nákladů bez marže:
              </span>
              <span className="font-medium">
                {formatCurrency(
                  calculation.total_price - calculation.margin_amount,
                )}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">
                Marže ({calculation.margin_percent}%):
              </span>
              <span className="font-medium">
                {formatCurrency(calculation.margin_amount)}
              </span>
            </div>
            <div className="flex justify-between border-t pt-2">
              <span className="text-lg font-semibold">Celkem s marží:</span>
              <span className="text-lg font-semibold">
                {formatCurrency(calculation.total_price)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Items */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Položky kalkulace</CardTitle>
            <Button size="sm" onClick={() => setIsAddItemDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Přidat položku
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {calculation.items.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              Zatím nebyly přidány žádné položky
            </div>
          ) : (
            <div className="space-y-6">
              {(Object.keys(groupedItems || {}) as CostType[]).map(
                (costType) => (
                  <div key={costType}>
                    <div className="mb-2">
                      <Badge className={COST_TYPE_COLORS[costType]}>
                        {COST_TYPE_LABELS[costType]}
                      </Badge>
                    </div>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Název</TableHead>
                          <TableHead>Popis</TableHead>
                          <TableHead className="text-right">Množství</TableHead>
                          <TableHead className="text-right">
                            Jedn. cena
                          </TableHead>
                          <TableHead className="text-right">Celkem</TableHead>
                          <TableHead className="w-24"></TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {groupedItems?.[costType].map((item) => (
                          <TableRow key={item.id}>
                            <TableCell className="font-medium">
                              {item.name}
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">
                              {item.description || "-"}
                            </TableCell>
                            <TableCell className="text-right">
                              {item.quantity} {item.unit}
                            </TableCell>
                            <TableCell className="text-right">
                              {formatCurrency(item.unit_price)}
                            </TableCell>
                            <TableCell className="text-right font-medium">
                              {formatCurrency(item.total_price)}
                            </TableCell>
                            <TableCell>
                              <div className="flex gap-1">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => setItemToEdit(item)}
                                >
                                  <Edit2 className="h-4 w-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => setItemToDelete(item.id)}
                                >
                                  <Trash2 className="h-4 w-4 text-destructive" />
                                </Button>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ),
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Item Dialog */}
      <Dialog open={isAddItemDialogOpen} onOpenChange={setIsAddItemDialogOpen}>
        <DialogContent>
          <form onSubmit={handleAddItem}>
            <DialogHeader>
              <DialogTitle>Přidat položku</DialogTitle>
              <DialogDescription>
                Přidejte novou položku do kalkulace
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="cost_type">Typ nákladu *</Label>
                <Select
                  value={newItem.cost_type}
                  onValueChange={(value) =>
                    setNewItem({ ...newItem, cost_type: value as CostType })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="material">Materiál</SelectItem>
                    <SelectItem value="labor">Práce</SelectItem>
                    <SelectItem value="cooperation">Kooperace</SelectItem>
                    <SelectItem value="overhead">Režie</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">Název *</Label>
                {newItem.cost_type === "material" ? (
                  <MaterialCombobox
                    id="name"
                    value={newItem.name}
                    onChange={(value) =>
                      setNewItem({ ...newItem, name: value })
                    }
                    onSelect={(material: MaterialPrice) =>
                      setNewItem({
                        ...newItem,
                        name: material.name + (material.dimension ? ` ${material.dimension}` : ""),
                        unit: material.unit,
                        unit_price: material.unit_price,
                        description: material.specification || material.material_grade || "",
                      })
                    }
                    required
                  />
                ) : (
                  <Input
                    id="name"
                    value={newItem.name}
                    onChange={(e) =>
                      setNewItem({ ...newItem, name: e.target.value })
                    }
                    required
                  />
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Popis</Label>
                <Textarea
                  id="description"
                  value={newItem.description}
                  onChange={(e) =>
                    setNewItem({ ...newItem, description: e.target.value })
                  }
                  rows={2}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="quantity">Množství *</Label>
                  <Input
                    id="quantity"
                    type="number"
                    step="0.01"
                    min="0"
                    value={newItem.quantity}
                    onChange={(e) =>
                      setNewItem({
                        ...newItem,
                        quantity: parseFloat(e.target.value),
                      })
                    }
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="unit">Jednotka *</Label>
                  <Input
                    id="unit"
                    value={newItem.unit}
                    onChange={(e) =>
                      setNewItem({ ...newItem, unit: e.target.value })
                    }
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="unit_price">Jednotková cena *</Label>
                <Input
                  id="unit_price"
                  type="number"
                  step="0.01"
                  min="0"
                  value={newItem.unit_price}
                  onChange={(e) =>
                    setNewItem({
                      ...newItem,
                      unit_price: parseFloat(e.target.value),
                    })
                  }
                  required
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsAddItemDialogOpen(false)}
              >
                Zrušit
              </Button>
              <Button type="submit" disabled={addItemMutation.isPending}>
                {addItemMutation.isPending ? "Přidávání..." : "Přidat"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Item Dialog */}
      {itemToEdit && (
        <Dialog open={!!itemToEdit} onOpenChange={() => setItemToEdit(null)}>
          <DialogContent>
            <form onSubmit={handleUpdateItem}>
              <DialogHeader>
                <DialogTitle>Upravit položku</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="edit_cost_type">Typ nákladu *</Label>
                  <Select
                    value={itemToEdit.cost_type}
                    onValueChange={(value) =>
                      setItemToEdit({
                        ...itemToEdit,
                        cost_type: value as CostType,
                      })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="material">Materiál</SelectItem>
                      <SelectItem value="labor">Práce</SelectItem>
                      <SelectItem value="cooperation">Kooperace</SelectItem>
                      <SelectItem value="overhead">Režie</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit_name">Název *</Label>
                  {itemToEdit.cost_type === "material" ? (
                    <MaterialCombobox
                      id="edit_name"
                      value={itemToEdit.name}
                      onChange={(value) =>
                        setItemToEdit({ ...itemToEdit, name: value })
                      }
                      onSelect={(material: MaterialPrice) =>
                        setItemToEdit({
                          ...itemToEdit,
                          name: material.name + (material.dimension ? ` ${material.dimension}` : ""),
                          unit: material.unit,
                          unit_price: material.unit_price,
                          description: material.specification || material.material_grade || "",
                        })
                      }
                      required
                    />
                  ) : (
                    <Input
                      id="edit_name"
                      value={itemToEdit.name}
                      onChange={(e) =>
                        setItemToEdit({ ...itemToEdit, name: e.target.value })
                      }
                      required
                    />
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit_description">Popis</Label>
                  <Textarea
                    id="edit_description"
                    value={itemToEdit.description || ""}
                    onChange={(e) =>
                      setItemToEdit({
                        ...itemToEdit,
                        description: e.target.value,
                      })
                    }
                    rows={2}
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit_quantity">Množství *</Label>
                    <Input
                      id="edit_quantity"
                      type="number"
                      step="0.01"
                      min="0"
                      value={itemToEdit.quantity}
                      onChange={(e) =>
                        setItemToEdit({
                          ...itemToEdit,
                          quantity: parseFloat(e.target.value),
                        })
                      }
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="edit_unit">Jednotka *</Label>
                    <Input
                      id="edit_unit"
                      value={itemToEdit.unit}
                      onChange={(e) =>
                        setItemToEdit({ ...itemToEdit, unit: e.target.value })
                      }
                      required
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit_unit_price">Jednotková cena *</Label>
                  <Input
                    id="edit_unit_price"
                    type="number"
                    step="0.01"
                    min="0"
                    value={itemToEdit.unit_price}
                    onChange={(e) =>
                      setItemToEdit({
                        ...itemToEdit,
                        unit_price: parseFloat(e.target.value),
                      })
                    }
                    required
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setItemToEdit(null)}
                >
                  Zrušit
                </Button>
                <Button type="submit" disabled={updateItemMutation.isPending}>
                  {updateItemMutation.isPending ? "Ukládání..." : "Uložit"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}

      {/* Delete Item Confirmation */}
      <AlertDialog
        open={!!itemToDelete}
        onOpenChange={() => setItemToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Smazat položku?</AlertDialogTitle>
            <AlertDialogDescription>
              Tato akce je nevratná. Položka bude trvale smazána z kalkulace.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Zrušit</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (itemToDelete) {
                  deleteItemMutation.mutate(itemToDelete);
                }
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Smazat
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Edit Calculation Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <form onSubmit={handleUpdateCalculation}>
            <DialogHeader>
              <DialogTitle>Upravit kalkulaci</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit_calc_name">Název *</Label>
                <Input
                  id="edit_calc_name"
                  value={editData.name}
                  onChange={(e) =>
                    setEditData({ ...editData, name: e.target.value })
                  }
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_margin">Marže (%)</Label>
                <Input
                  id="edit_margin"
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={editData.margin_percent}
                  onChange={(e) =>
                    setEditData({
                      ...editData,
                      margin_percent: parseFloat(e.target.value),
                    })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_status">Status</Label>
                <Select
                  value={editData.status}
                  onValueChange={(value) =>
                    setEditData({
                      ...editData,
                      status: value as CalculationStatus,
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft">Koncept</SelectItem>
                    <SelectItem value="approved">Schváleno</SelectItem>
                    <SelectItem value="offered">Nabídnuto</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit_note">Poznámka</Label>
                <Textarea
                  id="edit_note"
                  value={editData.note}
                  onChange={(e) =>
                    setEditData({ ...editData, note: e.target.value })
                  }
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsEditDialogOpen(false)}
              >
                Zrušit
              </Button>
              <Button type="submit" disabled={updateCalcMutation.isPending}>
                {updateCalcMutation.isPending ? "Ukládání..." : "Uložit"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Generate Offer Dialog */}
      <Dialog open={isOfferDialogOpen} onOpenChange={setIsOfferDialogOpen}>
        <DialogContent>
          <form onSubmit={handleGenerateOffer}>
            <DialogHeader>
              <DialogTitle>Generovat nabídku</DialogTitle>
              <DialogDescription>
                Vytvořte nabídku z této kalkulace
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="offer_number">Číslo nabídky</Label>
                <Input
                  id="offer_number"
                  value={offerData.offer_number}
                  onChange={(e) =>
                    setOfferData({ ...offerData, offer_number: e.target.value })
                  }
                  placeholder="Automaticky (NAB-XXXXXX)"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="valid_days">Platnost (dny)</Label>
                <Input
                  id="valid_days"
                  type="number"
                  min="1"
                  value={offerData.valid_days}
                  onChange={(e) =>
                    setOfferData({
                      ...offerData,
                      valid_days: parseInt(e.target.value),
                    })
                  }
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsOfferDialogOpen(false)}
              >
                Zrušit
              </Button>
              <Button type="submit" disabled={generateOfferMutation.isPending}>
                {generateOfferMutation.isPending
                  ? "Generování..."
                  : "Generovat"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* AI Estimate Dialog */}
      <Dialog open={isAIEstimateOpen} onOpenChange={setIsAIEstimateOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              AI Kalkulace
            </DialogTitle>
            <DialogDescription>
              Automatický odhad nákladů pomocí AI
            </DialogDescription>
          </DialogHeader>
          {aiEstimateMutation.isPending ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
                <p className="mt-4 text-sm text-muted-foreground">
                  AI analyzuje položky zakázky...
                </p>
              </div>
            </div>
          ) : aiEstimateMutation.data ? (
            <div className="space-y-4">
              <div className="grid gap-3 grid-cols-2 sm:grid-cols-4">
                <div className="rounded-lg bg-blue-50 p-3 text-center">
                  <p className="text-xs text-muted-foreground">Materiál</p>
                  <p className="text-lg font-bold">{formatCurrency(aiEstimateMutation.data.material_cost_czk)}</p>
                </div>
                <div className="rounded-lg bg-green-50 p-3 text-center">
                  <p className="text-xs text-muted-foreground">Práce</p>
                  <p className="text-lg font-bold">{formatCurrency(aiEstimateMutation.data.labor_cost_czk)}</p>
                </div>
                <div className="rounded-lg bg-orange-50 p-3 text-center">
                  <p className="text-xs text-muted-foreground">Režie</p>
                  <p className="text-lg font-bold">{formatCurrency(aiEstimateMutation.data.overhead_czk)}</p>
                </div>
                <div className="rounded-lg bg-purple-50 p-3 text-center">
                  <p className="text-xs text-muted-foreground">Celkem</p>
                  <p className="text-lg font-bold">{formatCurrency(aiEstimateMutation.data.total_czk)}</p>
                </div>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-xs font-medium text-muted-foreground mb-1">Marže: {aiEstimateMutation.data.margin_percent}%</p>
                <p className="text-xs font-medium text-muted-foreground">Pracnost: {aiEstimateMutation.data.labor_hours} hodin</p>
              </div>
              {aiEstimateMutation.data.items.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Rozpad položek</h4>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Název</TableHead>
                        <TableHead className="text-right">Materiál</TableHead>
                        <TableHead className="text-right">Hodiny</TableHead>
                        <TableHead>Poznámky</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {aiEstimateMutation.data.items.map((item: { name: string; material_cost_czk: number; labor_hours: number; notes: string }, idx: number) => (
                        <TableRow key={idx}>
                          <TableCell className="font-medium text-sm">{item.name}</TableCell>
                          <TableCell className="text-right text-sm">{formatCurrency(item.material_cost_czk)}</TableCell>
                          <TableCell className="text-right text-sm">{item.labor_hours}h</TableCell>
                          <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">{item.notes}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
              {aiEstimateMutation.data.reasoning && (
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs font-medium mb-1">Zdůvodnění AI:</p>
                  <p className="text-xs text-muted-foreground whitespace-pre-line">{aiEstimateMutation.data.reasoning}</p>
                </div>
              )}
            </div>
          ) : aiEstimateMutation.error ? (
            <div className="text-center py-8 text-destructive">
              <p>Chyba při generování AI kalkulace</p>
              <p className="text-xs mt-1">{String(aiEstimateMutation.error)}</p>
            </div>
          ) : null}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAIEstimateOpen(false)}>
              Zavřít
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
