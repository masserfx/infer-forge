"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getDocuments, downloadDocument } from "@/lib/api";
import type { Document } from "@/types";
import { DOCUMENT_CATEGORY_LABELS } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { FileText, Download, Search } from "lucide-react";
import { format } from "date-fns";
import { cs } from "date-fns/locale/cs";

export default function DocumentsPage() {
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const { data: documents = [], isLoading } = useQuery<Document[]>({
    queryKey: ["documents", "all"],
    queryFn: () => getDocuments({ limit: 100 }),
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const filteredDocuments = documents.filter((doc) => {
    const matchesCategory =
      categoryFilter === "all" || doc.category === categoryFilter;
    const matchesEntityType =
      entityTypeFilter === "all" || doc.entity_type === entityTypeFilter;
    const matchesSearch =
      searchQuery === "" ||
      doc.file_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.description?.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesCategory && matchesEntityType && matchesSearch;
  });

  const uniqueEntityTypes = Array.from(
    new Set(documents.map((doc) => doc.entity_type)),
  );

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="mt-4 text-sm text-muted-foreground">
            Načítání dokumentů...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dokumenty</h1>
        <p className="text-muted-foreground">
          Přehled všech dokumentů v systému
        </p>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 items-center gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Hledat dokumenty..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Select value={categoryFilter} onValueChange={setCategoryFilter}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Kategorie" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Všechny kategorie</SelectItem>
              {Object.entries(DOCUMENT_CATEGORY_LABELS).map(
                ([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ),
              )}
            </SelectContent>
          </Select>

          <Select
            value={entityTypeFilter}
            onValueChange={setEntityTypeFilter}
          >
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Typ entity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Všechny typy</SelectItem>
              {uniqueEntityTypes.map((type) => (
                <SelectItem key={type} value={type}>
                  {type === "order" ? "Zakázka" : type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="rounded-lg border bg-card">
        <div className="border-b p-4">
          <p className="text-sm text-muted-foreground">
            Zobrazeno <strong>{filteredDocuments.length}</strong> z{" "}
            <strong>{documents.length}</strong> dokumentů
          </p>
        </div>

        {filteredDocuments.length === 0 ? (
          <div className="p-8 text-center">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-2 text-sm font-medium">Žádné dokumenty</p>
            <p className="text-sm text-muted-foreground">
              {documents.length === 0
                ? "V systému zatím nejsou žádné dokumenty"
                : "Zkuste změnit filtry"}
            </p>
          </div>
        ) : (
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
                    Entita
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
                {filteredDocuments.map((doc) => (
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
                    <td className="px-4 py-3 text-sm">
                      <div className="flex flex-col">
                        <span className="font-medium">
                          {doc.entity_type === "order" ? "Zakázka" : doc.entity_type}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          ID: {doc.entity_id.slice(0, 8)}...
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {doc.description || "—"}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {formatFileSize(doc.file_size)}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {format(new Date(doc.created_at), "d. M. yyyy HH:mm", {
                        locale: cs,
                      })}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => downloadDocument(doc.id, doc.file_name)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
