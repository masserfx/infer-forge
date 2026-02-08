"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Users, Plus, Pencil, Trash2, Star, Mail, Phone, Building2 } from "lucide-react";
import {
  getSubcontractors,
  createSubcontractor,
  updateSubcontractor,
  deleteSubcontractor,
} from "@/lib/api";
import type { Subcontractor, SubcontractorCreate } from "@/types";
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
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

export default function SubdodavatelePage() {
  const [isActiveFilter, setIsActiveFilter] = useState<boolean | undefined>(true);
  const [specializationFilter, setSpecializationFilter] = useState("");
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [editingSubcontractor, setEditingSubcontractor] = useState<Subcontractor | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const queryClient = useQueryClient();

  const { data: subcontractors, isLoading } = useQuery({
    queryKey: [
      "subcontractors",
      {
        is_active: isActiveFilter,
        specialization: specializationFilter || undefined,
      },
    ],
    queryFn: () =>
      getSubcontractors({
        is_active: isActiveFilter,
        specialization: specializationFilter || undefined,
      }),
  });

  const createMutation = useMutation({
    mutationFn: createSubcontractor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subcontractors"] });
      setIsCreateDialogOpen(false);
      toast.success("Subdodavatel byl úspěšně vytvořen.");
    },
    onError: (error: Error) => {
      toast.error(`Chyba: ${error.message}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<SubcontractorCreate> }) =>
      updateSubcontractor(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subcontractors"] });
      setIsEditDialogOpen(false);
      setEditingSubcontractor(null);
      toast.success("Subdodavatel byl úspěšně upraven.");
    },
    onError: (error: Error) => {
      toast.error(`Chyba: ${error.message}`);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSubcontractor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subcontractors"] });
      setDeleteId(null);
      toast.success("Subdodavatel byl úspěšně smazán.");
    },
    onError: (error: Error) => {
      toast.error(`Chyba: ${error.message}`);
    },
  });

  const handleCreate = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const rating = formData.get("rating");
    createMutation.mutate({
      name: formData.get("name") as string,
      ico: formData.get("ico") as string || undefined,
      contact_email: formData.get("contact_email") as string || undefined,
      contact_phone: formData.get("contact_phone") as string || undefined,
      specialization: formData.get("specialization") as string || undefined,
      rating: rating ? parseFloat(rating as string) : undefined,
      is_active: formData.get("is_active") === "on",
      notes: formData.get("notes") as string || undefined,
    });
  };

  const handleEdit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!editingSubcontractor) return;
    const formData = new FormData(e.currentTarget);
    const rating = formData.get("rating");
    updateMutation.mutate({
      id: editingSubcontractor.id,
      data: {
        name: formData.get("name") as string,
        ico: formData.get("ico") as string || undefined,
        contact_email: formData.get("contact_email") as string || undefined,
        contact_phone: formData.get("contact_phone") as string || undefined,
        specialization: formData.get("specialization") as string || undefined,
        rating: rating ? parseFloat(rating as string) : undefined,
        is_active: formData.get("is_active") === "on",
        notes: formData.get("notes") as string || undefined,
      },
    });
  };

  const handleDelete = () => {
    if (deleteId) {
      deleteMutation.mutate(deleteId);
    }
  };

  const openEditDialog = (subcontractor: Subcontractor) => {
    setEditingSubcontractor(subcontractor);
    setIsEditDialogOpen(true);
  };

  const renderRating = (rating: number | null) => {
    if (rating === null) return <span className="text-muted-foreground">—</span>;
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`h-4 w-4 ${star <= rating ? "fill-yellow-400 text-yellow-400" : "text-gray-300"}`}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="flex h-full flex-col gap-4 sm:gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3">
          <Users className="h-8 w-8 text-primary" />
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">
              Subdodavatelé
            </h1>
            <p className="text-sm sm:text-base text-muted-foreground">
              Správa subdodavatelů a kooperací
            </p>
          </div>
        </div>
        <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button className="w-full sm:w-auto">
              <Plus className="mr-2 h-4 w-4" />
              Přidat subdodavatele
            </Button>
          </DialogTrigger>
          <DialogContent className="max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Nový subdodavatel</DialogTitle>
              <DialogDescription>
                Přidejte nového subdodavatele do systému.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <SubcontractorForm />
              <DialogFooter>
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? "Vytvářím..." : "Vytvořit"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Input
          placeholder="Filtrovat podle specializace..."
          value={specializationFilter}
          onChange={(e) => setSpecializationFilter(e.target.value)}
        />
        <Select
          value={isActiveFilter === undefined ? "all" : isActiveFilter ? "active" : "inactive"}
          onValueChange={(value) =>
            setIsActiveFilter(value === "all" ? undefined : value === "active")
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Stav" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Všichni</SelectItem>
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
              Načítání subdodavatelů...
            </p>
          </div>
        </div>
      ) : subcontractors && subcontractors.length === 0 ? (
        <div className="flex min-h-[400px] items-center justify-center rounded-lg border border-dashed">
          <div className="text-center">
            <p className="text-base sm:text-lg font-medium text-muted-foreground">
              Žádní subdodavatelé
            </p>
            <p className="text-sm text-muted-foreground">
              Zkuste změnit filtry nebo přidat nového subdodavatele
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Mobile: Card layout */}
          <div className="md:hidden space-y-3">
            {subcontractors?.map((subcontractor) => (
              <Card key={subcontractor.id}>
                <CardContent className="p-4">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-semibold text-sm">{subcontractor.name}</p>
                        {subcontractor.specialization && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {subcontractor.specialization}
                          </p>
                        )}
                      </div>
                      <Badge variant={subcontractor.is_active ? "default" : "secondary"}>
                        {subcontractor.is_active ? "Aktivní" : "Neaktivní"}
                      </Badge>
                    </div>
                    <div className="grid gap-2 text-xs">
                      {subcontractor.ico && (
                        <div className="flex items-center gap-2">
                          <Building2 className="h-3 w-3 text-muted-foreground" />
                          <span className="text-muted-foreground">IČO: </span>
                          <span className="font-medium">{subcontractor.ico}</span>
                        </div>
                      )}
                      {subcontractor.contact_email && (
                        <div className="flex items-center gap-2">
                          <Mail className="h-3 w-3 text-muted-foreground" />
                          <span className="font-medium">{subcontractor.contact_email}</span>
                        </div>
                      )}
                      {subcontractor.contact_phone && (
                        <div className="flex items-center gap-2">
                          <Phone className="h-3 w-3 text-muted-foreground" />
                          <span className="font-medium">{subcontractor.contact_phone}</span>
                        </div>
                      )}
                      {subcontractor.rating !== null && (
                        <div className="flex items-center gap-2">
                          <span className="text-muted-foreground">Hodnocení:</span>
                          {renderRating(subcontractor.rating)}
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => openEditDialog(subcontractor)}
                        className="flex-1"
                      >
                        <Pencil className="mr-2 h-3 w-3" />
                        Upravit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setDeleteId(subcontractor.id)}
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
                  <TableHead className="min-w-[100px]">IČO</TableHead>
                  <TableHead className="min-w-[180px]">Email</TableHead>
                  <TableHead className="min-w-[120px]">Telefon</TableHead>
                  <TableHead className="min-w-[150px]">Specializace</TableHead>
                  <TableHead className="min-w-[120px]">Hodnocení</TableHead>
                  <TableHead className="min-w-[80px]">Aktivní</TableHead>
                  <TableHead className="min-w-[120px]">Akce</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {subcontractors?.map((subcontractor) => (
                  <TableRow key={subcontractor.id}>
                    <TableCell className="font-medium">
                      {subcontractor.name}
                    </TableCell>
                    <TableCell>{subcontractor.ico || "—"}</TableCell>
                    <TableCell>
                      {subcontractor.contact_email ? (
                        <a
                          href={`mailto:${subcontractor.contact_email}`}
                          className="text-primary hover:underline"
                        >
                          {subcontractor.contact_email}
                        </a>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      {subcontractor.contact_phone ? (
                        <a
                          href={`tel:${subcontractor.contact_phone}`}
                          className="text-primary hover:underline"
                        >
                          {subcontractor.contact_phone}
                        </a>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>{subcontractor.specialization || "—"}</TableCell>
                    <TableCell>{renderRating(subcontractor.rating)}</TableCell>
                    <TableCell>
                      <Badge variant={subcontractor.is_active ? "default" : "secondary"}>
                        {subcontractor.is_active ? "Ano" : "Ne"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => openEditDialog(subcontractor)}
                        >
                          <Pencil className="h-4 w-4" />
                          <span className="sr-only">Upravit</span>
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDeleteId(subcontractor.id)}
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
            <DialogTitle>Upravit subdodavatele</DialogTitle>
            <DialogDescription>
              Upravte údaje subdodavatele.
            </DialogDescription>
          </DialogHeader>
          {editingSubcontractor && (
            <form onSubmit={handleEdit} className="space-y-4">
              <SubcontractorForm subcontractor={editingSubcontractor} />
              <DialogFooter>
                <Button type="submit" disabled={updateMutation.isPending}>
                  {updateMutation.isPending ? "Ukládám..." : "Uložit"}
                </Button>
              </DialogFooter>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Opravdu chcete smazat subdodavatele?</AlertDialogTitle>
            <AlertDialogDescription>
              Tato akce je nevratná. Subdodavatel bude trvale odstraněn ze systému.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Zrušit</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Smazat
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

interface SubcontractorFormProps {
  subcontractor?: Subcontractor;
}

function SubcontractorForm({ subcontractor }: SubcontractorFormProps) {
  return (
    <>
      <div>
        <Label htmlFor="name">Název *</Label>
        <Input
          id="name"
          name="name"
          defaultValue={subcontractor?.name}
          required
          placeholder="Název subdodavatele"
        />
      </div>
      <div>
        <Label htmlFor="ico">IČO</Label>
        <Input
          id="ico"
          name="ico"
          defaultValue={subcontractor?.ico || ""}
          placeholder="12345678"
        />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label htmlFor="contact_email">Email</Label>
          <Input
            id="contact_email"
            name="contact_email"
            type="email"
            defaultValue={subcontractor?.contact_email || ""}
            placeholder="kontakt@subdodavatel.cz"
          />
        </div>
        <div>
          <Label htmlFor="contact_phone">Telefon</Label>
          <Input
            id="contact_phone"
            name="contact_phone"
            type="tel"
            defaultValue={subcontractor?.contact_phone || ""}
            placeholder="+420 123 456 789"
          />
        </div>
      </div>
      <div>
        <Label htmlFor="specialization">Specializace</Label>
        <Input
          id="specialization"
          name="specialization"
          defaultValue={subcontractor?.specialization || ""}
          placeholder="Např. Svařování, Obrábění, Povrchové úpravy"
        />
      </div>
      <div>
        <Label htmlFor="rating">Hodnocení (1-5)</Label>
        <Select
          name="rating"
          defaultValue={subcontractor?.rating?.toString() || ""}
        >
          <SelectTrigger>
            <SelectValue placeholder="Vyberte hodnocení" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Nehodnoceno</SelectItem>
            <SelectItem value="1">⭐</SelectItem>
            <SelectItem value="2">⭐⭐</SelectItem>
            <SelectItem value="3">⭐⭐⭐</SelectItem>
            <SelectItem value="4">⭐⭐⭐⭐</SelectItem>
            <SelectItem value="5">⭐⭐⭐⭐⭐</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label htmlFor="notes">Poznámky</Label>
        <Textarea
          id="notes"
          name="notes"
          defaultValue={subcontractor?.notes || ""}
          placeholder="Doplňující informace o subdodavateli..."
          rows={3}
        />
      </div>
      <div className="flex items-center space-x-2">
        <Checkbox
          id="is_active"
          name="is_active"
          defaultChecked={subcontractor?.is_active !== false}
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
