/**
 * API client for INFER FORGE backend.
 * All API calls go through this module for consistent error handling.
 */

import type {
  Customer,
  Document,
  DocumentCategory,
  InboxMessage,
  Order,
  OrderStatus,
  PohodaSyncLog,
  PohodaSyncResult,
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
