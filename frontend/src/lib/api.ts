const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_V1 = `${API_BASE}/api/v1`;

import Cookies from "js-cookie";

// ---------------------------------------------------------------------------
// Generic fetch helper
// ---------------------------------------------------------------------------
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = Cookies.get("token");
  const headers = { 
    "Content-Type": "application/json", 
    ...options?.headers 
  };
  
  if (token) {
    (headers as any)["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_V1}${path}`, {
    headers,
    ...options,
  });

  if (res.status === 401 && typeof window !== "undefined" && !path.includes("/auth/")) {
    Cookies.remove("token");
    window.location.href = "/login";
  }

  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type AccountType = "checking" | "savings" | "cash";
export type TransactionType = "income" | "expense";
export type RecurrenceRule = "monthly" | "weekly" | "yearly";
export type CategoryType = "income" | "expense" | "both";
export type InvestmentType = "fixed_income" | "fund" | "stock" | "crypto" | "forex" | "other";

export interface Currency {
  id: string;
  code: string;
  name: string;
  symbol: string;
  decimal_places: number;
  is_crypto: boolean;
  created_at: string;
}

export interface Account {
  id: string;
  name: string;
  type: AccountType;
  currency_id: string;
  currency: Currency;
  initial_balance: number;
  created_at: string;
}

export interface CreditCard {
  id: string;
  name: string;
  closing_day: number;
  due_day: number;
  currency_id: string;
  payment_account_id: string | null;
  currency: Currency;
  credit_limit: number | null;
  created_at: string;
}

export interface Transaction {
  id: string;
  account_id: string;
  category_id: string | null;
  type: TransactionType;
  amount: number;
  description: string;
  category: string | null;
  date: string;
  is_recurring: boolean;
  recurrence_rule: RecurrenceRule | null;
  end_date: string | null;
  created_at: string;
}

export interface Installment {
  id: string;
  purchase_id: string;
  installment_number: number;
  due_date: string;
  amount: number;
  is_paid: boolean;
  paid_account_id: string | null;
  paid_at: string | null;
  created_at: string;
}

export interface Purchase {
  id: string;
  credit_card_id: string;
  category_id: string | null;
  description: string;
  total_amount: number;
  installments: number;
  installment_amount: number;
  purchase_date: string;
  first_installment_date: string;
  category: string | null;
  created_at: string;
  installment_rows: Installment[];
}

export interface MonthlyProjection {
  month: string;
  total_income: number;
  total_expenses: number;
  total_installments: number;
  net: number;
}

export interface DashboardSummary {
  current_month: string;
  total_income_mtd: number;
  total_expenses_mtd: number;
  total_installments_mtd: number;
  net_mtd: number;
  upcoming_installments: {
    card_id: string;
    card_name: string;
    total_pending: number;
    next_due_date: string;
  }[];
  projection: MonthlyProjection[];
}

export interface Category {
  id: string;
  name: string;
  type: CategoryType;
  color: string;
  icon: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Budget {
  id: string;
  category_id: string;
  currency_id: string;
  period_start: string;
  amount: number;
  notes: string | null;
  created_at: string;
  category: Category;
  currency: Currency;
}

export interface SavingGoal {
  id: string;
  name: string;
  currency_id: string;
  target_amount: number;
  current_amount: number;
  target_date: string | null;
  color: string;
  icon: string | null;
  created_at: string;
  currency: Currency;
}

export interface Investment {
  id: string;
  name: string;
  type: InvestmentType;
  currency_id: string;
  invested_amount: number;
  current_value: number;
  expected_return_rate: number | null;
  notes: string | null;
  created_at: string;
  currency: Currency;
}

export interface ExchangeRate {
  id: string;
  from_currency_id: string;
  to_currency_id: string;
  rate: number;
  date: string;
  created_at: string;
  from_currency: Currency;
  to_currency: Currency;
}

export interface ExchangeRateQuote {
  from_currency_id: string;
  to_currency_id: string;
  rate: number;
  date: string;
}

export interface FullDashboardSummary {
  currency: string;
  date_from: string;
  date_to: string;
  warnings: string[];
  kpis: Record<"income" | "expenses" | "net_savings" | "wealth", {
    value: number;
    previous_value: number;
    change_pct: number | null;
  }>;
  monthly_flow: { month: string; income: number; expenses: number; net: number }[];
  expenses_by_category: { category: string; amount: number; percent: number; color: string }[];
  account_balances: {
    account_id: string;
    name: string;
    type: AccountType;
    balance: number;
    currency_code: string;
    converted_balance: number | null;
  }[];
  upcoming_installments: {
    installment_id: string;
    description: string;
    current_installment: number;
    total_installments: number;
    due_date: string;
    amount: number;
    converted_amount: number | null;
    card_name: string;
  }[];
  investments: {
    investment_id: string;
    name: string;
    type: InvestmentType;
    invested_amount: number;
    current_value: number;
    gain: number;
    return_pct: number;
    converted_current_value: number | null;
  }[];
  recent_movements: {
    id: string;
    type: TransactionType;
    description: string;
    category: string | null;
    account: string | null;
    date: string;
    amount: number;
    converted_amount: number | null;
  }[];
  budgets: {
    budget_id: string;
    category: string;
    budget_amount: number;
    actual_amount: number;
    percent_used: number;
    color: string;
  }[];
  saving_goals: {
    goal_id: string;
    name: string;
    current_amount: number;
    target_amount: number;
    progress_pct: number;
    target_date: string | null;
    color: string;
    icon: string | null;
  }[];
}

export interface CreditCardPayload {
  name: string;
  closing_day: number;
  due_day: number;
  currency_id: string;
  payment_account_id?: string | null;
  credit_limit: number | null;
}

export interface TransactionPayload {
  account_id: string;
  category_id?: string | null;
  type: TransactionType;
  amount: number;
  description: string;
  category?: string | null;
  date: string;
  is_recurring: boolean;
  recurrence_rule?: RecurrenceRule | null;
  end_date?: string | null;
}

export interface PurchasePayload {
  credit_card_id: string;
  category_id?: string | null;
  description: string;
  total_amount: number;
  installments: number;
  starting_installment?: number;
  purchase_date: string;
  category?: string | null;
}

export interface PurchaseUpdatePayload {
  description?: string;
  category_id?: string | null;
  category?: string | null;
}

export type CategoryPayload = Omit<Category, "id" | "created_at">;
export type BudgetPayload = Omit<Budget, "id" | "created_at" | "category" | "currency">;
export type SavingGoalPayload = Omit<SavingGoal, "id" | "created_at" | "currency">;
export type InvestmentPayload = Omit<Investment, "id" | "created_at" | "currency">;
export type ExchangeRatePayload = Omit<ExchangeRate, "id" | "created_at" | "from_currency" | "to_currency">;

// ---------------------------------------------------------------------------
// Currencies API
// ---------------------------------------------------------------------------
export const currenciesApi = {
  list: () => apiFetch<Currency[]>("/currencies/"),
  get: (id: string) => apiFetch<Currency>(`/currencies/${id}`),
  create: (data: Omit<Currency, "id" | "created_at">) =>
    apiFetch<Currency>("/currencies/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Omit<Currency, "id" | "code" | "created_at">>) =>
    apiFetch<Currency>(`/currencies/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/currencies/${id}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// Accounts API
// ---------------------------------------------------------------------------
export const accountsApi = {
  list: () => apiFetch<Account[]>("/accounts/"),
  get: (id: string) => apiFetch<Account>(`/accounts/${id}`),
  create: (data: { name: string; type: AccountType; currency_id: string; initial_balance: number }) =>
    apiFetch<Account>("/accounts/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: { name?: string; type?: AccountType; currency_id?: string; initial_balance?: number }) =>
    apiFetch<Account>(`/accounts/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/accounts/${id}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// Categories API
// ---------------------------------------------------------------------------
export const categoriesApi = {
  list: () => apiFetch<Category[]>("/categories/"),
  get: (id: string) => apiFetch<Category>(`/categories/${id}`),
  create: (data: CategoryPayload) =>
    apiFetch<Category>("/categories/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<CategoryPayload>) =>
    apiFetch<Category>(`/categories/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/categories/${id}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// Credit Cards API
// ---------------------------------------------------------------------------
export const creditCardsApi = {
  list: () => apiFetch<CreditCard[]>("/credit-cards/"),
  get: (id: string) => apiFetch<CreditCard>(`/credit-cards/${id}`),
  create: (data: CreditCardPayload) =>
    apiFetch<CreditCard>("/credit-cards/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<CreditCardPayload>) =>
    apiFetch<CreditCard>(`/credit-cards/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/credit-cards/${id}`, { method: "DELETE" }),
  listInstallments: (id: string) =>
    apiFetch<Installment[]>(`/credit-cards/${id}/installments`),
};

export const installmentsApi = {
  update: (id: string, data: { is_paid: boolean; paid_account_id?: string | null }) =>
    apiFetch<Installment>(`/installments/${id}`, { method: "PUT", body: JSON.stringify(data) }),
};

// ---------------------------------------------------------------------------
// Transactions API
// ---------------------------------------------------------------------------
export const transactionsApi = {
  list: (params?: { account_id?: string; type?: string; date_from?: string; date_to?: string }) => {
    const searchParams = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== "") {
          searchParams.append(key, value);
        }
      });
    }
    const qs = searchParams.toString() ? "?" + searchParams.toString() : "";
    return apiFetch<Transaction[]>(`/transactions/${qs}`);
  },
  get: (id: string) => apiFetch<Transaction>(`/transactions/${id}`),
  create: (data: TransactionPayload) =>
    apiFetch<Transaction>("/transactions/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<TransactionPayload>) =>
    apiFetch<Transaction>(`/transactions/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/transactions/${id}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// Purchases API
// ---------------------------------------------------------------------------
export const purchasesApi = {
  list: () => apiFetch<Purchase[]>("/purchases/"),
  get: (id: string) => apiFetch<Purchase>(`/purchases/${id}`),
  create: (data: PurchasePayload) =>
    apiFetch<Purchase>("/purchases/", { method: "POST", body: JSON.stringify(data) }),
  createBulk: (data: PurchasePayload[]) =>
    apiFetch<Purchase[]>("/purchases/bulk", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: PurchaseUpdatePayload) =>
    apiFetch<Purchase>(`/purchases/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/purchases/${id}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------------------
// Cashflow API
// ---------------------------------------------------------------------------
export const cashflowApi = {
  projection: (months = 6) =>
    apiFetch<MonthlyProjection[]>(`/cashflow/projection?months=${months}`),
  summary: (month?: string) => {
    const qs = month ? `?month=${month}` : "";
    return apiFetch<MonthlyProjection>(`/cashflow/summary${qs}`);
  },
  dashboard: (projectionMonths = 6) =>
    apiFetch<DashboardSummary>(`/cashflow/dashboard?projection_months=${projectionMonths}`),
};

export const budgetsApi = {
  list: (month?: string) => apiFetch<Budget[]>(`/budgets/${month ? `?month=${month}` : ""}`),
  get: (id: string) => apiFetch<Budget>(`/budgets/${id}`),
  create: (data: BudgetPayload) =>
    apiFetch<Budget>("/budgets/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<BudgetPayload>) =>
    apiFetch<Budget>(`/budgets/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/budgets/${id}`, { method: "DELETE" }),
};

export const savingGoalsApi = {
  list: () => apiFetch<SavingGoal[]>("/saving-goals/"),
  get: (id: string) => apiFetch<SavingGoal>(`/saving-goals/${id}`),
  create: (data: SavingGoalPayload) =>
    apiFetch<SavingGoal>("/saving-goals/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<SavingGoalPayload>) =>
    apiFetch<SavingGoal>(`/saving-goals/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/saving-goals/${id}`, { method: "DELETE" }),
};

export const investmentsApi = {
  list: () => apiFetch<Investment[]>("/investments/"),
  get: (id: string) => apiFetch<Investment>(`/investments/${id}`),
  create: (data: InvestmentPayload) =>
    apiFetch<Investment>("/investments/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<InvestmentPayload>) =>
    apiFetch<Investment>(`/investments/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/investments/${id}`, { method: "DELETE" }),
};

export const exchangeRatesApi = {
  list: () => apiFetch<ExchangeRate[]>("/exchange-rates/"),
  get: (id: string) => apiFetch<ExchangeRate>(`/exchange-rates/${id}`),
  quote: (params: { from_currency_id: string; to_currency_id: string }) => {
    const qs = new URLSearchParams(params).toString();
    return apiFetch<ExchangeRateQuote>(`/exchange-rates/quote?${qs}`);
  },
  sync: (params?: { to?: string; from_codes?: string; rate_date?: string }) => {
    const qs = new URLSearchParams();
    if (params?.to) qs.set("to", params.to);
    if (params?.from_codes) qs.set("from_codes", params.from_codes);
    if (params?.rate_date) qs.set("rate_date", params.rate_date);
    return apiFetch<ExchangeRate[]>(`/exchange-rates/sync${qs.toString() ? `?${qs.toString()}` : ""}`, { method: "POST" });
  },
  create: (data: ExchangeRatePayload) =>
    apiFetch<ExchangeRate>("/exchange-rates/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Pick<ExchangeRatePayload, "rate" | "date">>) =>
    apiFetch<ExchangeRate>(`/exchange-rates/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  delete: (id: string) =>
    apiFetch<void>(`/exchange-rates/${id}`, { method: "DELETE" }),
};

export const dashboardApi = {
  summary: (params: { from: string; to: string; currency?: string }) => {
    const qs = new URLSearchParams({
      from: params.from,
      to: params.to,
      currency: params.currency ?? "USD",
    }).toString();
    return apiFetch<FullDashboardSummary>(`/dashboard/summary?${qs}`);
  },
};

export const authApi = {
  login: (data: FormData) =>
    fetch(`${API_BASE}/api/auth/login`, { method: "POST", body: data }).then(res => {
      if (!res.ok) throw new Error("Login failed");
      return res.json();
    }),
  register: (data: any) =>
    fetch(`${API_BASE}/api/auth/register`, { method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data) }).then(res => {
      if (!res.ok) throw new Error("Register failed");
      return res.json();
    }),
  me: (token: string) =>
    fetch(`${API_BASE}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } }).then(res => {
      if (!res.ok) throw new Error("Auth failed");
      return res.json();
    }),
};
