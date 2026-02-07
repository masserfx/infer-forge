/**
 * API client for INFER FORGE backend.
 * All API calls go through this module for consistent error handling.
 */

import type {
  Calculation,
  CalculationItem,
  CalculationStatus,
  CostType,
  Customer,
  CustomerReport,
  DashboardStats,
  Document,
  DocumentCategory,
  InboxMessage,
  Order,
  OrderStatus,
  PipelineReport,
  PohodaSyncLog,
  PohodaSyncResult,
  ProductionReport,
  RevenueReport,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }

  return res.json() as Promise<T>;
}

// --- Orders ---

export async function getOrders(params?: {
  skip?: number;
  limit?: number;
  status?: OrderStatus;
}): Promise<Order[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip) searchParams.set("skip", String(params.skip));
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.status) searchParams.set("status", params.status);
  const qs = searchParams.toString();
  return fetchApi<Order[]>(`/zakazky${qs ? `?${qs}` : ""}`);
}

export async function getOrder(id: string): Promise<Order> {
  return fetchApi<Order>(`/zakazky/${id}`);
}

export async function createOrder(data: {
  customer_id: string;
  number: string;
  items: { name: string; quantity: number; unit: string }[];
}): Promise<Order> {
  return fetchApi<Order>("/zakazky", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateOrderStatus(
  id: string,
  status: OrderStatus,
): Promise<Order> {
  return fetchApi<Order>(`/zakazky/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

// --- Customers ---

export async function getCustomers(): Promise<Customer[]> {
  return fetchApi<Customer[]>("/zakaznici");
}

export async function getCustomer(id: string): Promise<Customer> {
  return fetchApi<Customer>(`/zakaznici/${id}`);
}

// --- Inbox ---

export async function getInboxMessages(params?: {
  skip?: number;
  limit?: number;
  status?: string;
}): Promise<InboxMessage[]> {
  const searchParams = new URLSearchParams();
  if (params?.skip) searchParams.set("skip", String(params.skip));
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.status) searchParams.set("status", params.status);
  const qs = searchParams.toString();
  return fetchApi<InboxMessage[]>(`/inbox${qs ? `?${qs}` : ""}`);
}

// --- Pohoda ---

export async function syncEntity(
  entityType: string,
  entityId: string,
): Promise<PohodaSyncResult> {
  return fetchApi<PohodaSyncResult>(
    `/pohoda/sync/${entityType}/${entityId}`,
    { method: "POST" },
  );
}

export async function getSyncLogs(params?: {
  entity_type?: string;
  entity_id?: string;
}): Promise<PohodaSyncLog[]> {
  const searchParams = new URLSearchParams();
  if (params?.entity_type) searchParams.set("entity_type", params.entity_type);
  if (params?.entity_id) searchParams.set("entity_id", params.entity_id);
  const qs = searchParams.toString();
  return fetchApi<PohodaSyncLog[]>(`/pohoda/logs${qs ? `?${qs}` : ""}`);
}

// --- Documents ---

export async function getEntityDocuments(
  entityType: string,
  entityId: string,
  category?: DocumentCategory,
): Promise<Document[]> {
  const searchParams = new URLSearchParams();
  if (category) searchParams.set("category", category);
  const qs = searchParams.toString();
  return fetchApi<Document[]>(
    `/dokumenty/entity/${entityType}/${entityId}${qs ? `?${qs}` : ""}`,
  );
}

export async function uploadDocument(
  file: File,
  entityType: string,
  entityId: string,
  category: DocumentCategory,
  description?: string,
): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("entity_type", entityType);
  formData.append("entity_id", entityId);
  formData.append("category", category);
  if (description) formData.append("description", description);

  const url = `${API_BASE}/dokumenty/upload`;
  const res = await fetch(url, { method: "POST", body: formData });
  if (!res.ok) {
    const body = await res.text();
    throw new ApiError(res.status, body || res.statusText);
  }
  return res.json() as Promise<Document>;
}

export async function deleteDocument(id: string): Promise<void> {
  await fetchApi<void>(`/dokumenty/${id}`, { method: "DELETE" });
}

export function getDocumentDownloadUrl(id: string): string {
  return `${API_BASE}/dokumenty/${id}/download`;
}

// --- Calculations ---

export async function getCalculations(params?: {
  status?: CalculationStatus;
  skip?: number;
  limit?: number;
}): Promise<Calculation[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.skip) searchParams.set("skip", String(params.skip));
  if (params?.limit) searchParams.set("limit", String(params.limit));
  const qs = searchParams.toString();
  return fetchApi<Calculation[]>(`/kalkulace${qs ? `?${qs}` : ""}`);
}

export async function getCalculation(id: string): Promise<Calculation> {
  return fetchApi<Calculation>(`/kalkulace/${id}`);
}

export async function getOrderCalculations(
  orderId: string,
): Promise<Calculation[]> {
  return fetchApi<Calculation[]>(`/kalkulace/zakazka/${orderId}`);
}

export async function createCalculation(data: {
  order_id: string;
  name: string;
  margin_percent?: number;
  note?: string;
  items?: {
    cost_type: CostType;
    name: string;
    quantity: number;
    unit: string;
    unit_price: number;
    description?: string;
  }[];
}): Promise<Calculation> {
  return fetchApi<Calculation>("/kalkulace", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function addCalculationItem(
  calculationId: string,
  item: {
    cost_type: CostType;
    name: string;
    quantity: number;
    unit: string;
    unit_price: number;
    description?: string;
  },
): Promise<Calculation> {
  return fetchApi<Calculation>(`/kalkulace/${calculationId}/polozky`, {
    method: "POST",
    body: JSON.stringify(item),
  });
}

export async function updateCalculationItem(
  calculationId: string,
  itemId: string,
  data: Partial<Omit<CalculationItem, "id" | "calculation_id" | "total_price">>,
): Promise<Calculation> {
  return fetchApi<Calculation>(
    `/kalkulace/${calculationId}/polozky/${itemId}`,
    {
      method: "PUT",
      body: JSON.stringify(data),
    },
  );
}

export async function removeCalculationItem(
  calculationId: string,
  itemId: string,
): Promise<Calculation> {
  return fetchApi<Calculation>(
    `/kalkulace/${calculationId}/polozky/${itemId}`,
    {
      method: "DELETE",
    },
  );
}

export async function updateCalculation(
  id: string,
  data: {
    name?: string;
    margin_percent?: number;
    status?: CalculationStatus;
    note?: string;
  },
): Promise<Calculation> {
  return fetchApi<Calculation>(`/kalkulace/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteCalculation(id: string): Promise<void> {
  await fetchApi<void>(`/kalkulace/${id}`, { method: "DELETE" });
}

export async function generateOffer(
  calculationId: string,
  offerNumber: string,
  validDays = 30,
): Promise<{
  offer_id: string;
  number: string;
  total_price: string;
  valid_until: string;
}> {
  const searchParams = new URLSearchParams();
  searchParams.set("offer_number", offerNumber);
  searchParams.set("valid_days", String(validDays));
  return fetchApi<{
    offer_id: string;
    number: string;
    total_price: string;
    valid_until: string;
  }>(`/kalkulace/${calculationId}/nabidka?${searchParams.toString()}`, {
    method: "POST",
  });
}

// --- Reporting ---

export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchApi<DashboardStats>("/reporting/dashboard");
}

export async function getPipelineReport(): Promise<PipelineReport> {
  return fetchApi<PipelineReport>("/reporting/pipeline");
}

export async function getRevenueReport(months?: number): Promise<RevenueReport> {
  const searchParams = new URLSearchParams();
  if (months) searchParams.set("months", String(months));
  const qs = searchParams.toString();
  return fetchApi<RevenueReport>(`/reporting/revenue${qs ? `?${qs}` : ""}`);
}

export async function getProductionReport(): Promise<ProductionReport> {
  return fetchApi<ProductionReport>("/reporting/production");
}

export async function getCustomerReport(limit?: number): Promise<CustomerReport> {
  const searchParams = new URLSearchParams();
  if (limit) searchParams.set("limit", String(limit));
  const qs = searchParams.toString();
  return fetchApi<CustomerReport>(`/reporting/customers${qs ? `?${qs}` : ""}`);
}
