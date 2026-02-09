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

export type CustomerCategory = "A" | "B" | "C";

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
  category: CustomerCategory | null;
  discount_percent: number | null;
  payment_terms_days: number | null;
  credit_limit: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export const CUSTOMER_CATEGORY_LABELS: Record<CustomerCategory, string> = {
  A: "Klíčový zákazník",
  B: "Běžný zákazník",
  C: "Nový/jednorázový",
};

export const CUSTOMER_CATEGORY_DEFAULTS: Record<
  CustomerCategory,
  { discount: number; paymentDays: number }
> = {
  A: { discount: 15, paymentDays: 30 },
  B: { discount: 5, paymentDays: 14 },
  C: { discount: 0, paymentDays: 7 },
};

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
  assigned_to: string | null;
  assigned_to_name: string | null;
  pohoda_id: number | null;
  source_offer_id: string | null;
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
  processing_status?: "pending" | "processing" | "completed" | "error" | null;
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
  offered: "Nabídka vytvořena",
};

// --- Offers ---

export type OfferStatus = "draft" | "sent" | "accepted" | "rejected" | "expired";

export interface Offer {
  id: string;
  number: string;
  total_price: number;
  valid_until: string;
  status: OfferStatus;
  created_at: string;
}

export const OFFER_STATUS_LABELS: Record<OfferStatus, string> = {
  draft: "Vytvořena",
  sent: "Odesláno",
  accepted: "Přijato",
  rejected: "Odmítnuto",
  expired: "Expirováno",
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
  | "email_new"
  | "email_classified"
  | "pohoda_sync_complete"
  | "calculation_complete"
  | "order_status_changed"
  | "document_uploaded";

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
  email_new: "Nový email",
  email_classified: "Email klasifikován",
  pohoda_sync_complete: "Synchronizace Pohoda",
  calculation_complete: "Kalkulace dokončena",
  order_status_changed: "Změna stavu zakázky",
  document_uploaded: "Nový dokument",
};

// --- Gamification ---

export type PointsAction = "order_status_change" | "order_claim" | "calculation_complete" | "document_upload" | "order_complete";
export type PointsPeriod = "daily" | "weekly" | "monthly" | "all_time";

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  user_name: string;
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
  order_claim: "Převzetí zakázky",
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

// --- Material Prices ---

export interface MaterialPrice {
  id: string;
  name: string;
  specification: string | null;
  material_grade: string | null;
  form: string | null;
  dimension: string | null;
  unit: string;
  unit_price: number;
  supplier: string | null;
  valid_from: string;
  valid_to: string | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// --- Operations ---

export interface Operation {
  id: string;
  order_id: string;
  name: string;
  description: string | null;
  sequence: number;
  duration_hours: number | null;
  responsible: string | null;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  status: "planned" | "in_progress" | "completed" | "cancelled";
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface OperationCreate {
  name: string;
  description?: string;
  sequence: number;
  duration_hours?: number;
  responsible?: string;
  planned_start?: string;
  planned_end?: string;
  notes?: string;
}

// --- Subcontractors ---

export interface Subcontractor {
  id: string;
  name: string;
  ico: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  specialization: string | null;
  rating: number | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubcontractorCreate {
  name: string;
  ico?: string;
  contact_email?: string;
  contact_phone?: string;
  specialization?: string;
  rating?: number;
  is_active?: boolean;
  notes?: string;
}

// --- Recommendations ---

export type RecommendationSeverity = "critical" | "warning" | "info";

export interface Recommendation {
  type: string;
  severity: RecommendationSeverity;
  title: string;
  description: string;
  action_url: string;
  entity_id: string;
}

// --- AI Estimate ---

export interface AIEstimateItem {
  name: string;
  material_cost_czk: number;
  labor_hours: number;
  notes: string;
}

export interface AIEstimate {
  order_id: string;
  order_number: string;
  material_cost_czk: number;
  labor_hours: number;
  labor_cost_czk: number;
  overhead_czk: number;
  margin_percent: number;
  total_czk: number;
  reasoning: string;
  items: AIEstimateItem[];
}

// --- Feature Flags ---

export interface FeatureFlags {
  ORCHESTRATION_ENABLED: boolean;
  ORCHESTRATION_AUTO_CREATE_ORDERS: boolean;
  ORCHESTRATION_AUTO_CALCULATE: boolean;
  ORCHESTRATION_AUTO_OFFER: boolean;
  POHODA_AUTO_SYNC: boolean;
}

export interface IntegrationStatus {
  name: string;
  status: "connected" | "disconnected" | "configured";
  details: string | null;
}

// --- Anomaly ---

export interface CalculationAnomaly {
  type: string;
  severity: "warning" | "info";
  message: string;
  expected: number;
  actual: number;
}

// --- Prediction ---

export interface DueDatePrediction {
  predicted_days: number;
  predicted_range_low?: number;
  predicted_range_high?: number;
  confidence: number;
  method: string;
  message: string;
  sample_size?: number;
}

// --- Assignment ---

export interface AssignmentSuggestion {
  user_id: string;
  user_name: string;
  role: string;
  active_orders: number;
  reason: string;
}

export interface AssignmentResponse {
  suggestion: AssignmentSuggestion | null;
  alternatives: AssignmentSuggestion[];
  reason?: string;
}

// --- Insights ---

export interface Insight {
  type: "warning" | "info" | "success";
  text: string;
  icon: string;
}

export interface InsightsResponse {
  insights: Insight[];
  generated_at: string;
}

// --- AI Token Usage ---

export interface AITokenCategoryUsage {
  category: string;
  tokens_input: number;
  tokens_output: number;
  calls: number;
  cost_czk: number;
}

export interface AITokenTimePoint {
  label: string;
  cost_czk: number;
  calls: number;
}

export interface AITokenUsageResponse {
  period: string;
  categories: AITokenCategoryUsage[];
  timeline: AITokenTimePoint[];
  total_cost_czk: number;
  total_calls: number;
  total_tokens: number;
}

// --- Calculation Feedback ---

export interface CalculationFeedback {
  original_items: Record<string, unknown>[];
  corrected_items: Record<string, unknown>[];
  correction_type: "price" | "quantity" | "added" | "removed" | "margin";
}

// --- Drawing Analysis ---

export interface DrawingAnalysisResult {
  document_id: string;
  dimensions: { type: string; value: number; unit: string; tolerance?: string }[];
  materials: { grade: string; standard?: string; type?: string }[];
  tolerances: { type: string; value: string; standard?: string }[];
  surface_treatments: string[];
  welding_requirements: {
    wps?: string[];
    wpqr?: string[];
    ndt_methods?: string[];
    acceptance_criteria?: string[];
  };
  notes: string[];
  analyzed_at: string | null;
}

// --- Bulk Actions ---

export interface BulkStatusUpdate {
  order_ids: string[];
  status: OrderStatus;
}

export interface BulkAssignUpdate {
  order_ids: string[];
  assignee_id: string;
}

export interface BulkResult {
  updated: number;
  errors: string[];
}
