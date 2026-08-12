export type Sub = {
  status?: string;
  ends_at?: string;
  days_left?: number;
  traffic_limit_gb?: number | null;
  traffic_used_gb?: number;
  device_limit?: number;
  devices_used?: number;
  sub_url?: string;
  happ_open_url?: string;
  title?: string;
  plan?: { name?: string };
};

export type Me = {
  telegram_id?: number;
  username?: string | null;
  subscription?: Sub | null;
};

const API = (process.env.NEXT_PUBLIC_API_URL || "https://api.bigwinzone.ru").replace(/\/$/, "");

export function apiUrl(path: string) {
  return `${API}${path}`;
}

export async function miniappAuth(initData: string) {
  const res = await fetch(apiUrl("/api/v1/miniapp/auth"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: initData }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function apiGet<T>(path: string, token: string): Promise<T> {
  const res = await fetch(apiUrl(path), {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function apiPost<T>(path: string, token: string, body?: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = await res.text();
    try {
      const j = JSON.parse(detail);
      detail = j.detail || detail;
    } catch {
      /* keep text */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}

export async function fetchPlans() {
  const res = await fetch(apiUrl("/api/v1/plans"));
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<
    Array<{
      id: string;
      name: string;
      group_name?: string;
      price_rub: number;
      traffic_gb?: number | null;
      duration_days?: number;
    }>
  >;
}
