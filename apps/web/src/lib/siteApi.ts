"use client";

const API = (process.env.NEXT_PUBLIC_API_URL || "https://api.bigwinzone.ru").replace(/\/$/, "");
const TOKEN_KEY = "enigma_site_token";

export const GENERIC_ERROR = "Не удалось связаться с сервером. Проверьте интернет и попробуйте ещё раз.";

export type Device = {
  id: string;
  label: string;
  device_os?: string | null;
  device_model?: string | null;
  last_seen_at?: string | null;
};

export type Subscription = {
  id: string;
  status: "trial" | "active" | string;
  ends_at: string;
  days_left?: number | null;
  traffic_limit_gb: number | null;
  device_limit: number;
  devices_used: number;
  devices?: Device[] | null;
  title?: string | null;
  sub_url?: string | null;
  happ_deep_link?: string | null;
  happ_open_url?: string | null;
};

export type Me = {
  id: string;
  email: string;
  created_at?: string | null;
  subscription: Subscription | null;
};

export type Session = { access_token: string; user: Me };

export type Pricing = {
  plan_name: string;
  base_devices: number;
  max_devices: number;
  extra_device_price_per_month: number;
  trial_days: number;
  periods: { months: number; price: number; per_month: number }[];
};

export type Quote = {
  months: number;
  days: number;
  devices: number;
  extra_devices: number;
  base_price: number;
  extra_price: number;
  total: number;
  title: string;
};

export type DevicesQuote = { extra_devices: number; devices: number; months: number; total: number; title: string };

export type Order = {
  id: string;
  status: "pending" | "paid" | "canceled" | string;
  amount: string;
  payment_url?: string | null;
  created_at: string;
  paid_at?: string | null;
  title?: string | null;
  meta?: Record<string, unknown> | null;
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
  window.dispatchEvent(new Event("enigma-auth"));
}

async function request<T>(path: string, init: RequestInit = {}, auth = true): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (auth && token) headers.Authorization = `Bearer ${token}`;
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, { ...init, headers: { ...headers, ...(init.headers as Record<string, string>) } });
  } catch {
    throw new ApiError(0, GENERIC_ERROR);
  }
  if (!res.ok) {
    let message = GENERIC_ERROR;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) message = humanizeValidation(data.detail[0]);
    } catch {
      /* keep generic message */
    }
    if (res.status === 401 && auth) {
      setToken(null);
      if (!path.startsWith("/api/v1/site/login")) message = "Сессия истекла. Войдите ещё раз.";
    }
    if (res.status >= 500) message = "На сервере что-то пошло не так. Мы уже разбираемся — попробуйте через минуту.";
    throw new ApiError(res.status, message);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

function humanizeValidation(item: { loc?: unknown[]; msg?: string }): string {
  const field = String(item.loc?.[item.loc.length - 1] ?? "");
  if (field === "email") return "Введите корректный адрес электронной почты.";
  if (field === "password") return "Пароль должен быть не короче 8 символов.";
  return "Проверьте правильность заполнения формы.";
}

export const siteApi = {
  pricing: () => request<Pricing>("/api/v1/site/pricing", {}, false),
  quote: (months: number, extra_devices: number) =>
    request<Quote>("/api/v1/site/orders/quote", { method: "POST", body: JSON.stringify({ months, extra_devices }) }, false),
  register: (email: string, password: string) =>
    request<Session>("/api/v1/site/register", { method: "POST", body: JSON.stringify({ email, password }) }, false),
  login: (email: string, password: string) =>
    request<Session>("/api/v1/site/login", { method: "POST", body: JSON.stringify({ email, password }) }, false),
  me: () => request<Me>("/api/v1/site/me"),
  createOrder: (months: number, extra_devices: number) =>
    request<Order>("/api/v1/site/orders", { method: "POST", body: JSON.stringify({ months, extra_devices }) }),
  devicesQuote: (extra_devices: number) =>
    request<DevicesQuote>("/api/v1/site/orders/devices/quote", { method: "POST", body: JSON.stringify({ extra_devices }) }),
  createDevicesOrder: (extra_devices: number) =>
    request<Order>("/api/v1/site/orders/devices", { method: "POST", body: JSON.stringify({ extra_devices }) }),
  orders: () => request<Order[]>("/api/v1/site/orders"),
  order: (id: string) => request<Order>(`/api/v1/site/orders/${id}`),
  kickDevice: (id: string) => request<unknown>(`/api/v1/me/devices/${id}`, { method: "DELETE" }),
};

export function formatRub(value: number | string): string {
  const n = typeof value === "string" ? Number(value) : value;
  return `${new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(n)} ₽`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric" }).format(new Date(iso));
}

export function pluralRu(n: number, one: string, few: string, many: string): string {
  const abs = Math.abs(n) % 100;
  const last = abs % 10;
  if (abs > 10 && abs < 20) return many;
  if (last > 1 && last < 5) return few;
  if (last === 1) return one;
  return many;
}

export function monthsLabel(n: number) {
  return `${n} ${pluralRu(n, "месяц", "месяца", "месяцев")}`;
}

export function devicesLabel(n: number) {
  return `${n} ${pluralRu(n, "устройство", "устройства", "устройств")}`;
}
