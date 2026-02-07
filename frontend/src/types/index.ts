/**
 * TypeScript types matching backend Pydantic schemas.
 * All API response types are defined here for type safety.
 */

// --- Enums ---

export type OrderStatus =
  | "poptavka"
  | "nabidka"
  | "objednavka"
  | "vyroba"
  | "expedice"
  | "fakturace"
  | "dokonceno";

export type OrderPriority = "low" | "normal" | "high" | "urgent";

export type InboxClassification =
  | "poptavka"
  | "objednavka"
  | "reklamace"
  | "dotaz"
  | "faktura"
  | "ostatni";

export type InboxStatus = "new" | "classified" | "assigned" | "archived";

export type SyncDirection = "export" | "import";
export type SyncStatus = "pending" | "success" | "error";

// --- Customer ---

export interface Customer {
  id: string;
  company_name: string;
  ico: string;
  dic: string | null;
  contact_name: string;
  email: string;
  phone: string | null;
  address: string | null;
  pohoda_id: number | null;
  created_at: string;
  updated_at: string;
}

// --- Order ---

export interface OrderItem {
  id: string;
  name: string;
  material: string | null;
  quantity: number;
  unit: string;
  dn: string | null;
  pn: string | null;
  note: string | null;
  drawing_url: string | null;
}

export interface Order {
  id: string;
  customer_id: string;
  number: string;
  status: OrderStatus;
  priority: OrderPriority;
  due_date: string | null;
  note: string | null;
  created_by: string | null;
  pohoda_id: number | null;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
  customer: Customer | null;
}

// --- Inbox ---

export interface InboxMessage {
  id: string;
  message_id: string;
  from_email: string;
  from_name: string | null;
  subject: string;
  body_text: string | null;
  received_at: string;
  classification: InboxClassification | null;
  confidence: number | null;
  status: InboxStatus;
  assigned_order_id: string | null;
  created_at: string;
}

// --- Pohoda Sync ---

export interface PohodaSyncLog {
  id: string;
  entity_type: string;
  entity_id: string;
  direction: SyncDirection;
  pohoda_doc_number: string | null;
  status: SyncStatus;
  error_message: string | null;
  synced_at: string;
}

export interface PohodaSyncResult {
  success: boolean;
  sync_log_id: string;
  pohoda_id: number | null;
  pohoda_doc_number: string | null;
  error: string | null;
}

// --- UI Helpers ---

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  poptavka: "Poptávka",
  nabidka: "Nabídka",
  objednavka: "Objednávka",
  vyroba: "Výroba",
  expedice: "Expedice",
  fakturace: "Fakturace",
  dokonceno: "Dokončeno",
};

export const ORDER_STATUS_COLORS: Record<OrderStatus, string> = {
  poptavka: "bg-blue-100 text-blue-800",
  nabidka: "bg-purple-100 text-purple-800",
  objednavka: "bg-yellow-100 text-yellow-800",
  vyroba: "bg-orange-100 text-orange-800",
  expedice: "bg-cyan-100 text-cyan-800",
  fakturace: "bg-green-100 text-green-800",
  dokonceno: "bg-gray-100 text-gray-800",
};

export const PRIORITY_LABELS: Record<OrderPriority, string> = {
  low: "Nízká",
  normal: "Normální",
  high: "Vysoká",
  urgent: "Urgentní",
};

export const PRIORITY_COLORS: Record<OrderPriority, string> = {
  low: "bg-gray-100 text-gray-700",
  normal: "bg-blue-100 text-blue-700",
  high: "bg-orange-100 text-orange-700",
  urgent: "bg-red-100 text-red-700",
};

export const INBOX_STATUS_LABELS: Record<InboxStatus, string> = {
  new: "Nový",
  classified: "Klasifikován",
  assigned: "Přiřazen",
  archived: "Archivován",
};

export const CLASSIFICATION_LABELS: Record<InboxClassification, string> = {
  poptavka: "Poptávka",
  objednavka: "Objednávka",
  reklamace: "Reklamace",
  dotaz: "Dotaz",
  faktura: "Faktura",
  ostatni: "Ostatní",
};

// --- Documents ---

export type DocumentCategory =
  | "vykres"
  | "atestace"
  | "wps"
  | "pruvodka"
  | "faktura"
  | "nabidka"
  | "objednavka"
  | "protokol"
  | "ostatni";

export interface Document {
  id: string;
  entity_type: string;
  entity_id: string;
  file_name: string;
  file_path: string;
  mime_type: string;
  file_size: number;
  version: number;
  category: DocumentCategory;
  description: string | null;
  ocr_text: string | null;
  uploaded_by: string | null;
  created_at: string;
  updated_at: string;
}

export const DOCUMENT_CATEGORY_LABELS: Record<DocumentCategory, string> = {
  vykres: "Výkres",
  atestace: "Atestace",
  wps: "WPS",
  pruvodka: "Průvodka",
  faktura: "Faktura",
  nabidka: "Nabídka",
  objednavka: "Objednávka",
  protokol: "Protokol",
  ostatni: "Ostatní",
};

// --- Calculations ---

export type CostType = "material" | "labor" | "cooperation" | "overhead";
export type CalculationStatus = "draft" | "approved" | "offered";

export interface CalculationItem {
  id: string;
  calculation_id: string;
  cost_type: CostType;
  name: string;
  description: string | null;
  quantity: number;
  unit: string;
  unit_price: number;
  total_price: number;
}

export interface Calculation {
  id: string;
  order_id: string;
  name: string;
  status: CalculationStatus;
  note: string | null;
  created_by: string | null;
  material_total: number;
  labor_total: number;
  cooperation_total: number;
  overhead_total: number;
  margin_percent: number;
  margin_amount: number;
  total_price: number;
  items: CalculationItem[];
  created_at: string;
  updated_at: string;
}

export const COST_TYPE_LABELS: Record<CostType, string> = {
  material: "Materiál",
  labor: "Práce",
  cooperation: "Kooperace",
  overhead: "Režie",
};

export const COST_TYPE_COLORS: Record<CostType, string> = {
  material: "bg-blue-100 text-blue-800",
  labor: "bg-green-100 text-green-800",
  cooperation: "bg-purple-100 text-purple-800",
  overhead: "bg-orange-100 text-orange-800",
};

export const CALCULATION_STATUS_LABELS: Record<CalculationStatus, string> = {
  draft: "Koncept",
  approved: "Schváleno",
  offered: "Nabídnuto",
};
