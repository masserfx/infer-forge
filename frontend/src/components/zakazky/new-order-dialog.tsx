"use client";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { createOrder, getCustomers } from "@/lib/api";
import type { OrderPriority } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

interface OrderItem {
  name: string;
  quantity: number;
  unit: string;
  material?: string;
}

export function NewOrderDialog() {
  const [open, setOpen] = useState(false);
  const [customerId, setCustomerId] = useState<string>("");
  const [orderNumber, setOrderNumber] = useState<string>(
    () => `ORD-${Math.random().toString(36).substring(2, 8).toUpperCase()}`
  );
  const [priority, setPriority] = useState<OrderPriority>("normal");
  const [dueDate, setDueDate] = useState<string>("");
  const [note, setNote] = useState<string>("");
  const [items, setItems] = useState<OrderItem[]>([
    { name: "", quantity: 1, unit: "ks", material: "" },
  ]);

  const queryClient = useQueryClient();

  const { data: customers, isLoading: loadingCustomers } = useQuery({
    queryKey: ["customers"],
    queryFn: getCustomers,
  });

  const createOrderMutation = useMutation({
    mutationFn: createOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      toast.success("Zakázka úspěšně vytvořena");
      setOpen(false);
      resetForm();
    },
    onError: (error: Error) => {
      toast.error("Chyba při vytváření zakázky", {
        description: error.message,
      });
    },
  });

  const resetForm = () => {
    setCustomerId("");
    setOrderNumber(`ORD-${Math.random().toString(36).substring(2, 8).toUpperCase()}`);
    setPriority("normal");
    setDueDate("");
    setNote("");
    setItems([{ name: "", quantity: 1, unit: "ks", material: "" }]);
  };

  const addItem = () => {
    setItems([...items, { name: "", quantity: 1, unit: "ks", material: "" }]);
  };

  const removeItem = (index: number) => {
    if (items.length > 1) {
      setItems(items.filter((_, i) => i !== index));
    }
  };

  const updateItem = (index: number, field: keyof OrderItem, value: string | number) => {
    const updatedItems = [...items];
    updatedItems[index] = { ...updatedItems[index], [field]: value };
    setItems(updatedItems);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!customerId) {
      toast.error("Vyberte zákazníka");
      return;
    }

    if (!orderNumber.trim()) {
      toast.error("Vyplňte číslo zakázky");
      return;
    }

    const validItems = items.filter((item) => item.name.trim() !== "");
    if (validItems.length === 0) {
      toast.error("Přidejte alespoň jednu položku");
      return;
    }

    createOrderMutation.mutate({
      customer_id: customerId,
      number: orderNumber,
      items: validItems.map((item) => ({
        name: item.name,
        quantity: item.quantity,
        unit: item.unit,
      })),
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="w-full sm:w-auto min-h-[44px]">
          <Plus className="mr-2 h-4 w-4" />
          Nová zakázka
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nová zakázka</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Zákazník */}
          <div className="space-y-2">
            <Label htmlFor="customer">
              Zákazník <span className="text-red-500">*</span>
            </Label>
            <Select value={customerId} onValueChange={setCustomerId}>
              <SelectTrigger id="customer" className="w-full">
                <SelectValue placeholder="Vyberte zákazníka" />
              </SelectTrigger>
              <SelectContent>
                {loadingCustomers ? (
                  <SelectItem value="loading" disabled>
                    Načítání...
                  </SelectItem>
                ) : customers && customers.length > 0 ? (
                  customers.map((customer) => (
                    <SelectItem key={customer.id} value={customer.id}>
                      {customer.company_name} ({customer.ico})
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="no-customers" disabled>
                    Žádní zákazníci
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
          </div>

          {/* Číslo zakázky */}
          <div className="space-y-2">
            <Label htmlFor="order-number">
              Číslo zakázky <span className="text-red-500">*</span>
            </Label>
            <Input
              id="order-number"
              value={orderNumber}
              onChange={(e) => setOrderNumber(e.target.value)}
              placeholder="ORD-XXXXXX"
            />
          </div>

          {/* Priorita */}
          <div className="space-y-2">
            <Label htmlFor="priority">Priorita</Label>
            <Select
              value={priority}
              onValueChange={(value) => setPriority(value as OrderPriority)}
            >
              <SelectTrigger id="priority" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Nízká</SelectItem>
                <SelectItem value="normal">Normální</SelectItem>
                <SelectItem value="high">Vysoká</SelectItem>
                <SelectItem value="urgent">Urgentní</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Termín dodání */}
          <div className="space-y-2">
            <Label htmlFor="due-date">Termín dodání</Label>
            <Input
              id="due-date"
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>

          {/* Poznámka */}
          <div className="space-y-2">
            <Label htmlFor="note">Poznámka</Label>
            <Textarea
              id="note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Doplňující informace k zakázce"
              rows={3}
            />
          </div>

          {/* Položky */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>
                Položky <span className="text-red-500">*</span>
              </Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addItem}
                className="h-8"
              >
                <Plus className="mr-1 h-3 w-3" />
                Přidat položku
              </Button>
            </div>

            <div className="space-y-3">
              {items.map((item, index) => (
                <div
                  key={index}
                  className="grid grid-cols-1 sm:grid-cols-12 gap-2 p-3 rounded-md border bg-muted/30"
                >
                  {/* Název */}
                  <div className="sm:col-span-5 space-y-1">
                    <Label htmlFor={`item-name-${index}`} className="text-xs">
                      Název
                    </Label>
                    <Input
                      id={`item-name-${index}`}
                      value={item.name}
                      onChange={(e) => updateItem(index, "name", e.target.value)}
                      placeholder="Název položky"
                    />
                  </div>

                  {/* Množství */}
                  <div className="sm:col-span-2 space-y-1">
                    <Label htmlFor={`item-quantity-${index}`} className="text-xs">
                      Množství
                    </Label>
                    <Input
                      id={`item-quantity-${index}`}
                      type="number"
                      min="1"
                      value={item.quantity}
                      onChange={(e) =>
                        updateItem(index, "quantity", Number(e.target.value))
                      }
                    />
                  </div>

                  {/* Jednotka */}
                  <div className="sm:col-span-2 space-y-1">
                    <Label htmlFor={`item-unit-${index}`} className="text-xs">
                      Jednotka
                    </Label>
                    <Input
                      id={`item-unit-${index}`}
                      value={item.unit}
                      onChange={(e) => updateItem(index, "unit", e.target.value)}
                      placeholder="ks"
                    />
                  </div>

                  {/* Materiál */}
                  <div className="sm:col-span-2 space-y-1">
                    <Label htmlFor={`item-material-${index}`} className="text-xs">
                      Materiál
                    </Label>
                    <Input
                      id={`item-material-${index}`}
                      value={item.material}
                      onChange={(e) =>
                        updateItem(index, "material", e.target.value)
                      }
                      placeholder="Nepovinné"
                    />
                  </div>

                  {/* Odstranit */}
                  {items.length > 1 && (
                    <div className="sm:col-span-1 flex items-end">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeItem(index)}
                        className="h-9 w-full sm:w-9 text-red-600 hover:text-red-700 hover:bg-red-50"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Tlačítka */}
          <div className="flex flex-col sm:flex-row gap-2 sm:justify-end pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              className="w-full sm:w-auto"
            >
              Zrušit
            </Button>
            <Button
              type="submit"
              disabled={createOrderMutation.isPending}
              className="w-full sm:w-auto"
            >
              {createOrderMutation.isPending ? "Vytváření..." : "Vytvořit zakázku"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
