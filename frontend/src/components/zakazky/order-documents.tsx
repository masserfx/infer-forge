"use client";

import { useState } from "react";
import { useQueryClient, useMutation, useQuery } from "@tanstack/react-query";
import {
  deleteDocument,
  getDocumentDownloadUrl,
  getEntityDocuments,
  uploadDocument,
} from "@/lib/api";
import type { DocumentCategory } from "@/types";
import { DOCUMENT_CATEGORY_LABELS } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
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
import { FileText, Upload, Download, Trash2, FileIcon } from "lucide-react";
import { format } from "date-fns";
import { cs } from "date-fns/locale/cs";

interface OrderDocumentsProps {
  entityType: string;
  entityId: string;
}

export function OrderDocuments({ entityType, entityId }: OrderDocumentsProps) {
  const queryClient = useQueryClient();
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedCategory, setSelectedCategory] =
    useState<DocumentCategory>("ostatni");
  const [description, setDescription] = useState("");

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ["documents", entityType, entityId],
    queryFn: () => getEntityDocuments(entityType, entityId),
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!selectedFile) throw new Error("Není vybrán žádný soubor");
      return uploadDocument(
        selectedFile,
        entityType,
        entityId,
        selectedCategory,
        description || undefined,
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", entityType, entityId],
      });
      setIsUploadOpen(false);
      setSelectedFile(null);
      setDescription("");
      setSelectedCategory("ostatni");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["documents", entityType, entityId],
      });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleUpload = () => {
    uploadMutation.mutate();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="h-6 w-6 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-muted-foreground" />
          <h2 className="text-xl font-semibold">Dokumenty</h2>
          <span className="text-sm text-muted-foreground">
            ({documents.length})
          </span>
        </div>

        <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
          <DialogTrigger asChild>
            <Button>
              <Upload className="mr-2 h-4 w-4" />
              Nahrát dokument
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Nahrát dokument</DialogTitle>
              <DialogDescription>
                Vyberte soubor a doplňte informace o dokumentu.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="file">Soubor</Label>
                <Input
                  id="file"
                  type="file"
                  onChange={handleFileChange}
                  accept=".pdf,.jpg,.jpeg,.png,.xlsx,.xls,.dwg,.dxf"
                />
                {selectedFile && (
                  <p className="text-sm text-muted-foreground">
                    {selectedFile.name} ({formatFileSize(selectedFile.size)})
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="category">Kategorie</Label>
                <Select
                  value={selectedCategory}
                  onValueChange={(value) =>
                    setSelectedCategory(value as DocumentCategory)
                  }
                >
                  <SelectTrigger id="category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(DOCUMENT_CATEGORY_LABELS).map(
                      ([value, label]) => (
                        <SelectItem key={value} value={value}>
                          {label}
                        </SelectItem>
                      ),
                    )}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Popis (nepovinné)</Label>
                <Textarea
                  id="description"
                  placeholder="Doplňující informace o dokumentu..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                />
              </div>
            </div>

            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setIsUploadOpen(false)}
              >
                Zrušit
              </Button>
              <Button
                onClick={handleUpload}
                disabled={!selectedFile || uploadMutation.isPending}
              >
                {uploadMutation.isPending ? "Nahrávání..." : "Nahrát"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {documents.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <FileIcon className="mx-auto h-12 w-12 text-muted-foreground" />
          <p className="mt-2 text-sm font-medium">Žádné dokumenty</p>
          <p className="text-sm text-muted-foreground">
            Nahrajte první dokument pro tuto zakázku
          </p>
        </div>
      ) : (
        <div className="rounded-lg border">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium">
                    Název
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium">
                    Kategorie
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium">
                    Popis
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium">
                    Velikost
                  </th>
                  <th className="px-4 py-3 text-left text-sm font-medium">
                    Nahráno
                  </th>
                  <th className="px-4 py-3 text-right text-sm font-medium">
                    Akce
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-muted/30">
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{doc.file_name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <Badge variant="outline">
                        {DOCUMENT_CATEGORY_LABELS[doc.category]}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {doc.description || "—"}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {formatFileSize(doc.file_size)}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {format(new Date(doc.created_at), "d. M. yyyy", {
                        locale: cs,
                      })}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          asChild
                        >
                          <a
                            href={getDocumentDownloadUrl(doc.id)}
                            download
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Download className="h-4 w-4" />
                          </a>
                        </Button>

                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>
                                Smazat dokument?
                              </AlertDialogTitle>
                              <AlertDialogDescription>
                                Opravdu chcete smazat dokument{" "}
                                <strong>{doc.file_name}</strong>? Tuto akci
                                nelze vrátit zpět.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Zrušit</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => deleteMutation.mutate(doc.id)}
                                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              >
                                Smazat
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
