/**
 * TypeScript types matching backend Pydantic schemas.
 * All API response types are defined here for type safety.
 */

// --- Enums ---

export type UserRole = "admin" | "obchodnik" | "technolog" | "vedeni" | "ucetni";

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

// --- Auth ---

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  phone: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Administrátor",
  obchodnik: "Obchodník",
  technolog: "Technolog",
  vedeni: "Vedení",
  ucetni: "Účetní",
};

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

// --- Reporting ---

export interface StatusCount {
  status: string;
  count: number;
  label: string;
}

export interface PipelineReport {
  statuses: StatusCount[];
  total_orders: number;
}

export interface RevenueItem {
  period: string;
  total_calculations: number;
  total_offers: number;
  offers_count: number;
  calculations_count: number;
}

export interface RevenueReport {
  total_calculation_value: number;
  total_offer_value: number;
  approved_calculations: number;
  pending_offers: number;
  accepted_offers: number;
  monthly: RevenueItem[];
}

export interface ProductionItem {
  order_id: string;
  order_number: string;
  customer_name: string;
  status: string;
  priority: string;
  due_date: string | null;
  days_until_due: number | null;
  items_count: number;
}

export interface ProductionReport {
  in_production: number;
  in_expedition: number;
  overdue: number;
  due_this_week: number;
  due_this_month: number;
  orders: ProductionItem[];
}

export interface CustomerStats {
  customer_id: string;
  company_name: string;
  ico: string;
  orders_count: number;
  total_value: number;
  active_orders: number;
}

export interface CustomerReport {
  total_customers: number;
  active_customers: number;
  top_customers: CustomerStats[];
}

export interface DashboardStats {
  total_orders: number;
  orders_in_production: number;
  new_inbox_messages: number;
  pending_invoicing: number;
  total_documents: number;
  total_calculations: number;
  total_revenue: number;
  overdue_orders: number;
  pipeline: PipelineReport;
}

// --- Notifications ---

export type NotificationType =
  | "EMAIL_NEW"
  | "EMAIL_CLASSIFIED"
  | "POHODA_SYNC_COMPLETE"
  | "CALCULATION_COMPLETE"
  | "ORDER_STATUS_CHANGED"
  | "DOCUMENT_UPLOADED";

export interface Notification {
  id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  message: string;
  link: string | null;
  read: boolean;
  created_at: string;
}

export const NOTIFICATION_TYPE_LABELS: Record<NotificationType, string> = {
  EMAIL_NEW: "Nový email",
  EMAIL_CLASSIFIED: "Email klasifikován",
  POHODA_SYNC_COMPLETE: "Synchronizace Pohoda",
  CALCULATION_COMPLETE: "Kalkulace dokončena",
  ORDER_STATUS_CHANGED: "Změna stavu zakázky",
  DOCUMENT_UPLOADED: "Nový dokument",
};

// --- Gamification ---

export type PointsAction = "order_status_change" | "calculation_complete" | "document_upload" | "order_complete";
export type PointsPeriod = "daily" | "weekly" | "monthly" | "all_time";

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  user_name: string;
  user_email: string;
  points_earned: number;
  tasks_completed: number;
  bonus_points: number;
  total_points: number;
}

export interface LeaderboardResponse {
  period: string;
  entries: LeaderboardEntry[];
  total_users: number;
}

export interface PointsEntry {
  id: string;
  action: PointsAction;
  points: number;
  description: string | null;
  earned_at: string;
}

export interface UserStats {
  user_id: string;
  user_name: string;
  total_points: number;
  rank: number;
  orders_completed: number;
  calculations_done: number;
  documents_uploaded: number;
  recent_points: PointsEntry[];
}

export const POINTS_ACTION_LABELS: Record<PointsAction, string> = {
  order_status_change: "Změna stavu zakázky",
  calculation_complete: "Dokončení kalkulace",
  document_upload: "Nahrání dokumentu",
  order_complete: "Dokončení zakázky",
};

export const PERIOD_LABELS: Record<PointsPeriod, string> = {
  daily: "Dnes",
  weekly: "Tento týden",
  monthly: "Tento měsíc",
  all_time: "Celkem",
};
