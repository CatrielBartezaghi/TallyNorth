import Cookies from "js-cookie";
import type { RecurrenceRule, TransactionType } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

export type RecurringDestinationType = "account" | "credit_card";

export interface RecurringEntry {
  id: string;
  type: TransactionType;
  amount: number;
  description: string;
  category_id: string | null;
  category: string | null;
  frequency: RecurrenceRule;
  start_date: string;
  end_date: string | null;
  active: boolean;
  destination_type: RecurringDestinationType;
  account_id: string | null;
  credit_card_id: string | null;
  last_generated_date: string | null;
  created_at: string;
}

export interface RecurringEntryPayload {
  type: TransactionType;
  amount: number;
  description: string;
  category_id?: string | null;
  frequency: RecurrenceRule;
  start_date: string;
  end_date?: string | null;
  active: boolean;
  destination_type: RecurringDestinationType;
  account_id?: string | null;
  credit_card_id?: string | null;
}

async function recurringFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = Cookies.get("token");
  const headers = new Headers(options?.headers);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_V1}${path}`, {
    ...options,
    headers,
    credentials: options?.credentials ?? "include",
  });
  if (res.status === 401 && typeof window !== "undefined") {
    Cookies.remove("token", { path: "/" });
    window.location.href = "/login";
  }
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const recurringEntriesApi = {
  list: () => recurringFetch<RecurringEntry[]>("/recurring-entries/"),
  create: (data: RecurringEntryPayload) =>
    recurringFetch<RecurringEntry>("/recurring-entries/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  update: (id: string, data: Partial<RecurringEntryPayload>) =>
    recurringFetch<RecurringEntry>(`/recurring-entries/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  delete: (id: string) =>
    recurringFetch<void>(`/recurring-entries/${id}`, { method: "DELETE" }),
};
