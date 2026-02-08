"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Package, Plus, Upload, Pencil, Trash2, Search } from "lucide-react";
import {
  getMaterialPrices,
  createMaterialPrice,
  updateMaterialPrice,
  deleteMaterialPrice,
  importMaterialPrices,
} from "@/lib/api";
import type { MaterialPrice } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

const formatPrice = (price: number) => {
  return new Intl.NumberFormat("cs-CZ", {
    style: "currency",
    currency: "CZK",
  }).format(price);
};

export default function MaterialyPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [materialGradeFilter, setMaterialGradeFilter] = useState<string>("all");
  const [formFilter, setFormFilter] = useState<string>("all");
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>(true);
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);
  const [editingMaterial, setEditingMaterial] = useState<MaterialPrice | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const queryClient = useQueryClient();

  const { data: materials, isLoading } = useQuery({
    queryKey: [
      "materials",
      {
        search: searchQuery,
        material_grade: materialGradeFilter !== "all" ? materialGradeFilter : undefined,
        form: formFilter !== "all" ? formFilter : undefined,
        is_active: activeFilter,
      },
    ],
    queryFn: () =>
      getMaterialPrices({
        search: searchQuery || undefined,
        material_grade: materialGradeFilter !== "all" ? materialGradeFilter : undefined,
        form: formFilter !== "all" ? formFilter : undefined,
        is_active: activeFilter,
      }),
  });

  const createMutation = useMutation({
    mutationFn: createMaterialPrice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["materials"] });
      setIsCreateDialogOpen(false);
      toast.success("Nová cenová položka byla úspěšně vytvořena.");
    },
    onError: (error: Error) => {
      toast.error(`Chyba: ${error.message}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<MaterialPrice> }) =>
      updateMaterialPrice(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["materials"] });
      setIsEditDialogOpen(false);
      setEditingMaterial(null);
      toast.success("Cenová položka byla úspěšně upravena.");
    },
    onError: (error: Error) => {
      toast.error(`Chyba: ${error.message}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteMaterialPrice,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["materials"] });
      toast.success("Cenová položka byla úspěšně smazána.");
    },
    onError: (error: Error) => {
      toast.error(`Chyba: ${error.message}`);
    },
  });

  const importMutation = useMutation({
    mutationFn: importMaterialPrices,
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["materials"] });
      setIsImportDialogOpen(false);
      setSelectedFile(null);
      toast.success(
        `Import dokončen: ${result.imported} položek. ${result.errors.length > 0 ? `Chyby: ${result.errors.length}` : ""}`
      );
    },
    onError: (error: Error) => {
      toast.error(`Chyba importu: ${error.message}`);
    },
  });

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    createMutation.mutate({
      name: formData.get("name") as string,
      specification: formData.get("specification") as string || null,
      material_grade: formData.get("material_grade") as string || null,
      form: formData.get("form") as string || null,
      dimension: formData.get("dimension") as string || null,
      unit: formData.get("unit") as string,
      unit_price: parseFloat(formData.get("unit_price") as string),
      supplier: formData.get("supplier") as string || null,
      valid_from: formData.get("valid_from") as string,
      valid_to: formData.get("valid_to") as string || null,
      is_active: formData.get("is_active") === "on",
      notes: formData.get("notes") as string || null,
    });
  };

  const handleEdit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editingMaterial) return;
    const formData = new FormData(e.currentTarget);
    updateMutation.mutate({
      id: editingMaterial.id,
      data: {
        name: formData.get("name") as string,
        specification: formData.get("specification") as string || null,
        material_grade: formData.get("material_grade") as string || null,
        form: formData.get("form") as string || null,
        dimension: formData.get("dimension") as string || null,
        unit: formData.get("unit") as string,
        unit_price: parseFloat(formData.get("unit_price") as string),
        supplier: formData.get("supplier") as string || null,
        valid_from: formData.get("valid_from") as string,
        valid_to: formData.get("valid_to") as string || null,
        is_active: formData.get("is_active") === "on",
        notes: formData.get("notes") as string || null,
      },
    });
  };

  const handleImport = () => {
    if (!selectedFile) return;
    importMutation.mutate(selectedFile);
  };

  const handleDelete = (id: string) => {
    if (confirm("Opravdu chcete smazat tento materiál?")) {
      deleteMutation.mutate(id);
    }
  };

  const openEditDialog = (material: MaterialPrice) => {
    setEditingMaterial(material);
    setIsEditDialogOpen(true);
  };

  // Extract unique values for filters
  const materialGrades = Array.from(
    new Set(materials?.map((m) => m.material_grade).filter(Boolean) as string[])
  ).sort();
  const forms = Array.from(
    new Set(materials?.map((m) => m.form).filter(Boolean) as string[])
  ).sort();

  return (
    <div className="flex h-full flex-col gap-4 sm:gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <Package className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Ceník materiálů
            </h1>
            <p className="text-sm sm:text-base text-muted-foreground">
              Správa cen materiálů a dodavatelů
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Dialog open={isImportDialogOpen} onOpenChange={setIsImportDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" className="w-full sm:w-auto">
                <Upload className="mr-2 h-4 w-4" />
                Import z Excelu
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Import materiálů z Excelu</DialogTitle>
                <DialogDescription>
                  Nahrajte Excel soubor s cenami materiálů.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="import-file">Soubor Excel</Label>
                  <Input
                    id="import-file"
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  onClick={handleImport}
                  disabled={!selectedFile || importMutation.isPending}
                >
                  {importMutation.isPending ? "Importuji..." : "Importovat"}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogTrigger asChild>
              <Button className="w-full sm:w-auto">
                <Plus className="mr-2 h-4 w-4" />
                Přidat
              </Button>
            </DialogTrigger>
            <DialogContent className="max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Nový materiál</DialogTitle>
                <DialogDescription>
                  Vytvořte novou cenovou položku materiálu.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4">
                <MaterialPriceForm />
                <DialogFooter>
                  <Button type="submit" disabled={createMutation.isPending}>
                    {createMutation.isPending ? "Vytvářím..." : "Vytvořit"}
                  </Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Hledat..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={materialGradeFilter} onValueChange={setMaterialGradeFilter}>
          <SelectTrigger>
            <SelectValue placeholder="Materiálová třída" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Všechny třídy</SelectItem>
            {materialGrades.map((grade) => (
              <SelectItem key={grade} value={grade}>
                {grade}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={formFilter} onValueChange={setFormFilter}>
          <SelectTrigger>
            <SelectValue placeholder="Forma" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Všechny formy</SelectItem>
            {forms.map((form) => (
              <SelectItem key={form} value={form}>
                {form}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={activeFilter === undefined ? "all" : activeFilter ? "active" : "inactive"}
          onValueChange={(value) =>
            setActiveFilter(value === "all" ? undefined : value === "active")
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Stav" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Vše</SelectItem>
            <SelectItem value="active">Aktivní</SelectItem>
            <SelectItem value="inactive">Neaktivní</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex min-h-[400px] items-center justify-center rounded-lg border">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="mt-4 text-sm text-muted-foreground">
              Načítání materiálů...
            </p>
          </div>
        </div>
      ) : materials && materials.length === 0 ? (
        <div className="flex min-h-[400px] items-center justify-center rounded-lg border border-dashed">
          <div className="text-center">
            <p className="text-base sm:text-lg font-medium text-muted-foreground">
              Žádné materiály
            </p>
            <p className="text-sm text-muted-foreground">
              Zkuste změnit filtry nebo přidat nový materiál
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Mobile: Card layout */}
          <div className="md:hidden space-y-3">
            {materials?.map((material) => (
              <Card key={material.id}>
                <CardContent className="p-4">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-sm">{material.name}</p>
                        {material.specification && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {material.specification}
                          </p>
                        )}
                      </div>
                      <Badge variant={material.is_active ? "default" : "secondary"}>
                        {material.is_active ? "Aktivní" : "Neaktivní"}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {material.material_grade && (
                        <div>
                          <span className="text-muted-foreground">Třída: </span>
                          <span className="font-medium">{material.material_grade}</span>
                        </div>
                      )}
                      {material.form && (
                        <div>
                          <span className="text-muted-foreground">Forma: </span>
                          <span className="font-medium">{material.form}</span>
                        </div>
                      )}
                      {material.dimension && (
                        <div>
                          <span className="text-muted-foreground">Rozměr: </span>
                          <span className="font-medium">{material.dimension}</span>
                        </div>
                      )}
                      <div>
                        <span className="text-muted-foreground">Cena: </span>
                        <span className="font-medium">
                          {formatPrice(material.unit_price)}/{material.unit}
                        </span>
                      </div>
                      {material.supplier && (
                        <div className="col-span-2">
                          <span className="text-muted-foreground">Dodavatel: </span>
                          <span className="font-medium">{material.supplier}</span>
                        </div>
                      )}
                      <div>
                        <span className="text-muted-foreground">Platnost od: </span>
                        <span className="font-medium">
                          {new Date(material.valid_from).toLocaleDateString("cs-CZ")}
                        </span>
                      </div>
                      {material.valid_to && (
                        <div>
                          <span className="text-muted-foreground">Platnost do: </span>
                          <span className="font-medium">
                            {new Date(material.valid_to).toLocaleDateString("cs-CZ")}
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEditDialog(material)}
                        className="flex-1"
                      >
                        <Pencil className="mr-2 h-3 w-3" />
                        Upravit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDelete(material.id)}
                        className="flex-1"
                      >
                        <Trash2 className="mr-2 h-3 w-3" />
                        Smazat
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Desktop: Table */}
          <div className="hidden md:block rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[150px]">Název</TableHead>
                  <TableHead className="min-w-[100px]">Třída</TableHead>
                  <TableHead className="min-w-[100px]">Forma</TableHead>
                  <TableHead className="min-w-[100px]">Rozměr</TableHead>
                  <TableHead className="min-w-[120px]">Cena/jednotka</TableHead>
                  <TableHead className="min-w-[150px]">Dodavatel</TableHead>
                  <TableHead className="min-w-[100px]">Platnost od</TableHead>
                  <TableHead className="min-w-[100px]">Platnost do</TableHead>
                  <TableHead className="min-w-[80px]">Aktivní</TableHead>
                  <TableHead className="min-w-[120px]">Akce</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {materials?.map((material) => (
                  <TableRow key={material.id}>
                    <TableCell className="font-medium">
                      <div>
                        <p>{material.name}</p>
                        {material.specification && (
                          <p className="text-xs text-muted-foreground">
                            {material.specification}
                          </p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{material.material_grade || "—"}</TableCell>
                    <TableCell>{material.form || "—"}</TableCell>
                    <TableCell>{material.dimension || "—"}</TableCell>
                    <TableCell>
                      {formatPrice(material.unit_price)}/{material.unit}
                    </TableCell>
                    <TableCell>{material.supplier || "—"}</TableCell>
                    <TableCell>
                      {new Date(material.valid_from).toLocaleDateString("cs-CZ")}
                    </TableCell>
                    <TableCell>
                      {material.valid_to
                        ? new Date(material.valid_to).toLocaleDateString("cs-CZ")
                        : "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={material.is_active ? "default" : "secondary"}>
                        {material.is_active ? "Ano" : "Ne"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openEditDialog(material)}
                        >
                          <Pencil className="h-4 w-4" />
                          <span className="sr-only">Upravit</span>
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(material.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                          <span className="sr-only">Smazat</span>
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Upravit materiál</DialogTitle>
            <DialogDescription>
              Upravte cenovou položku materiálu.
            </DialogDescription>
          </DialogHeader>
          {editingMaterial && (
            <form onSubmit={handleEdit} className="space-y-4">
              <MaterialPriceForm material={editingMaterial} />
              <DialogFooter>
                <Button type="submit" disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? "Ukládám..." : "Uložit"}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface MaterialPriceFormProps {
  material?: MaterialPrice;
}

function MaterialPriceForm({ material }: MaterialPriceFormProps) {
  return (
    <>
      <div>
        <Label htmlFor="name">Název *</Label>
        <Input
          id="name"
          name="name"
          defaultValue={material?.name}
          required
          placeholder="Např. Plech ocelový"
        />
      </div>
      <div>
        <Label htmlFor="specification">Specifikace</Label>
        <Input
          id="specification"
          name="specification"
          defaultValue={material?.specification || ""}
          placeholder="Např. Za tepla válcovaný"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="material_grade">Materiálová třída</Label>
          <Input
            id="material_grade"
            name="material_grade"
            defaultValue={material?.material_grade || ""}
            placeholder="Např. S235JR"
          />
        </div>
        <div>
          <Label htmlFor="form">Forma</Label>
          <Input
            id="form"
            name="form"
            defaultValue={material?.form || ""}
            placeholder="Např. Plech, Trubka"
          />
        </div>
      </div>
      <div>
        <Label htmlFor="dimension">Rozměr</Label>
        <Input
          id="dimension"
          name="dimension"
          defaultValue={material?.dimension || ""}
          placeholder="Např. 10x2000x6000"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="unit_price">Jednotková cena * (Kč)</Label>
          <Input
            id="unit_price"
            name="unit_price"
            type="number"
            step="0.01"
            defaultValue={material?.unit_price}
            required
            placeholder="Např. 150.50"
          />
        </div>
        <div>
          <Label htmlFor="unit">Jednotka *</Label>
          <Input
            id="unit"
            name="unit"
            defaultValue={material?.unit || "kg"}
            required
            placeholder="Např. kg, m, ks"
          />
        </div>
      </div>
      <div>
        <Label htmlFor="supplier">Dodavatel</Label>
        <Input
          id="supplier"
          name="supplier"
          defaultValue={material?.supplier || ""}
          placeholder="Název dodavatele"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="valid_from">Platnost od *</Label>
          <Input
            id="valid_from"
            name="valid_from"
            type="date"
            defaultValue={material?.valid_from?.split("T")[0] || new Date().toISOString().split("T")[0]}
            required
          />
        </div>
        <div>
          <Label htmlFor="valid_to">Platnost do</Label>
          <Input
            id="valid_to"
            name="valid_to"
            type="date"
            defaultValue={material?.valid_to?.split("T")[0] || ""}
          />
        </div>
      </div>
      <div>
        <Label htmlFor="notes">Poznámky</Label>
        <Textarea
          id="notes"
          name="notes"
          defaultValue={material?.notes || ""}
          placeholder="Doplňující informace..."
          rows={3}
        />
      </div>
      <div className="flex items-center space-x-2">
        <Checkbox
          id="is_active"
          name="is_active"
          defaultChecked={material?.is_active !== false}
        />
        <Label
          htmlFor="is_active"
          className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
          Aktivní
        </Label>
      </div>
    </>
  );
}
