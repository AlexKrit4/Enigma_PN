"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { adminFetch, getAdminToken, setAdminToken } from "@/lib/adminApi";

type Tab =
  | "stats"
  | "health"
  | "users"
  | "orders"
  | "actions"
  | "proxy"
  | "broadcast"
  | "plans"
  | "promos";

const TABS: { id: Tab; label: string }[] = [
  { id: "stats", label: "Статистика" },
  { id: "health", label: "Здоровье" },
  { id: "users", label: "Пользователи" },
  { id: "orders", label: "Оплаты" },
  { id: "actions", label: "Действия" },
  { id: "proxy", label: "Прокси" },
  { id: "broadcast", label: "Рассылка" },
  { id: "plans", label: "Тарифы" },
  { id: "promos", label: "Промо" },
];

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-5">
      <h2 className="mb-4 text-lg font-semibold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

function Field({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="block text-sm">
      <span className="text-white/65">{label}</span>
      <input
        {...props}
        className="mt-1 w-full rounded-lg border border-white/10 bg-black/25 px-3 py-2 outline-none focus:border-sky-400"
      />
    </label>
  );
}

function TextArea({
  label,
  ...props
}: { label: string } & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <label className="block text-sm">
      <span className="text-white/65">{label}</span>
      <textarea
        {...props}
        className="mt-1 w-full rounded-lg border border-white/10 bg-black/25 px-3 py-2 outline-none focus:border-sky-400"
      />
    </label>
  );
}

function Btn({
  children,
  tone = "default",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "default" | "danger" | "primary" }) {
  const cls =
    tone === "primary"
      ? "bg-sky-400 text-black hover:bg-sky-300"
      : tone === "danger"
        ? "bg-rose-500/20 text-rose-200 hover:bg-rose-500/30"
        : "bg-white/10 hover:bg-white/15";
  return (
    <button
      {...props}
      className={`rounded-lg px-3 py-2 text-sm font-medium transition disabled:opacity-50 ${cls} ${props.className || ""}`}
    >
      {children}
    </button>
  );
}

function pre(data: unknown) {
  return JSON.stringify(data, null, 2);
}

export default function AdminPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [tab, setTab] = useState<Tab>("stats");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const [stats, setStats] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [userStatus, setUserStatus] = useState("active");
  const [lookup, setLookup] = useState("");
  const [userCard, setUserCard] = useState<any>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [plans, setPlans] = useState<any[]>([]);
  const [promos, setPromos] = useState<any[]>([]);

  // actions form
  const [tgId, setTgId] = useState("");
  const [days, setDays] = useState("30");
  const [trafficGb, setTrafficGb] = useState("");
  const [deviceLimit, setDeviceLimit] = useState("3");
  const [clearTraffic, setClearTraffic] = useState(false);

  // broadcast
  const [broadcastText, setBroadcastText] = useState("");
  const [audience, setAudience] = useState("active");

  // plan create
  const [planSlug, setPlanSlug] = useState("");
  const [planName, setPlanName] = useState("");
  const [planDays, setPlanDays] = useState("30");
  const [planPrice, setPlanPrice] = useState("100");
  const [planGroup, setPlanGroup] = useState("ограниченный");
  const [planGb, setPlanGb] = useState("30");
  const [planDevices, setPlanDevices] = useState("3");

  // promo
  const [promoCode, setPromoCode] = useState("");
  const [promoDays, setPromoDays] = useState("30");

  // proxy
  const [proxyInfo, setProxyInfo] = useState<any>(null);
  const [proxyTgId, setProxyTgId] = useState("");
  const [proxyDays, setProxyDays] = useState("30");

  useEffect(() => {
    if (!getAdminToken()) {
      router.replace("/admin/login");
      return;
    }
    setReady(true);
  }, [router]);

  const flash = useCallback((text: string, isErr = false) => {
    if (isErr) {
      setErr(text);
      setMsg("");
    } else {
      setMsg(text);
      setErr("");
    }
  }, []);

  const run = useCallback(
    async (fn: () => Promise<void>) => {
      setBusy(true);
      setErr("");
      try {
        await fn();
      } catch (e) {
        flash(e instanceof Error ? e.message : String(e), true);
      } finally {
        setBusy(false);
      }
    },
    [flash],
  );

  const loadStats = useCallback(
    () =>
      run(async () => {
        setStats(await adminFetch("/stats"));
      }),
    [run],
  );
  const loadHealth = useCallback(
    () =>
      run(async () => {
        setHealth(await adminFetch("/health"));
      }),
    [run],
  );
  const loadUsers = useCallback(
    () =>
      run(async () => {
        const data = await adminFetch(`/users?status=${encodeURIComponent(userStatus)}&limit=30`);
        setUsers(Array.isArray(data) ? data : data.items || []);
      }),
    [run, userStatus],
  );
  const loadOrders = useCallback(
    () =>
      run(async () => {
        const data = await adminFetch("/orders?status=pending&limit=40");
        setOrders(Array.isArray(data) ? data : data.items || []);
      }),
    [run],
  );
  const loadPlans = useCallback(
    () =>
      run(async () => {
        const data = await adminFetch("/plans");
        setPlans(Array.isArray(data) ? data : []);
      }),
    [run],
  );
  const loadPromos = useCallback(
    () =>
      run(async () => {
        const data = await adminFetch("/promos");
        setPromos(Array.isArray(data) ? data : data.items || []);
      }),
    [run],
  );
  const loadProxyInfo = useCallback(
    () =>
      run(async () => {
        setProxyInfo(await adminFetch("/proxy/info"));
      }),
    [run],
  );

  useEffect(() => {
    if (!ready) return;
    if (tab === "stats") loadStats();
    if (tab === "health") loadHealth();
    if (tab === "users") loadUsers();
    if (tab === "orders") loadOrders();
    if (tab === "plans") loadPlans();
    if (tab === "promos") loadPromos();
    if (tab === "proxy") loadProxyInfo();
  }, [ready, tab, loadStats, loadHealth, loadUsers, loadOrders, loadPlans, loadPromos, loadProxyInfo]);

  const userRows = useMemo(() => (Array.isArray(users) ? users : []), [users]);
  const orderRows = useMemo(() => (Array.isArray(orders) ? orders : []), [orders]);
  const planRows = useMemo(() => (Array.isArray(plans) ? plans : []), [plans]);
  const promoRows = useMemo(() => (Array.isArray(promos) ? promos : []), [promos]);

  if (!ready) {
    return <main className="p-8 text-white/60">Загрузка…</main>;
  }

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-6 md:px-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-serif text-3xl tracking-tight">Enigma_PN Admin</h1>
          <p className="text-sm text-white/55">Те же действия, что в Telegram /admin</p>
        </div>
        <div className="flex gap-2">
          <Btn
            onClick={() =>
              run(async () => {
                const blob = (await adminFetch("/export.csv", {})) as Blob;
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "enigma_users.csv";
                a.click();
                URL.revokeObjectURL(url);
                flash("CSV скачан");
              })
            }
          >
            Экспорт CSV
          </Btn>
          <Btn
            tone="danger"
            onClick={() => {
              setAdminToken(null);
              router.replace("/admin/login");
            }}
          >
            Выйти
          </Btn>
        </div>
      </header>

      <nav className="mb-5 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-full px-3 py-1.5 text-sm ${
              tab === t.id ? "bg-sky-400 text-black" : "bg-white/10 text-white/80 hover:bg-white/15"
            }`}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {(msg || err) && (
        <div
          className={`mb-4 rounded-xl px-4 py-3 text-sm ${
            err ? "bg-rose-500/15 text-rose-200" : "bg-emerald-500/15 text-emerald-200"
          }`}
        >
          {err || msg}
        </div>
      )}

      {busy ? <p className="mb-3 text-sm text-white/45">Запрос…</p> : null}

      {tab === "stats" && (
        <Card title="Статистика">
          <pre className="overflow-auto whitespace-pre-wrap text-sm text-white/80">{pre(stats)}</pre>
          <div className="mt-3">
            <Btn onClick={loadStats}>Обновить</Btn>
          </div>
        </Card>
      )}

      {tab === "health" && (
        <Card title="Здоровье сервера">
          <pre className="overflow-auto whitespace-pre-wrap text-sm text-white/80">{pre(health)}</pre>
          <div className="mt-3">
            <Btn onClick={loadHealth}>Обновить</Btn>
          </div>
        </Card>
      )}

      {tab === "users" && (
        <div className="space-y-4">
          <Card title="Поиск">
            <div className="flex flex-wrap gap-2">
              <input
                value={lookup}
                onChange={(e) => setLookup(e.target.value)}
                placeholder="telegram id или @username"
                className="min-w-[220px] flex-1 rounded-lg border border-white/10 bg-black/25 px-3 py-2"
              />
              <Btn
                tone="primary"
                onClick={() =>
                  run(async () => {
                    const data = await adminFetch(`/users/lookup?q=${encodeURIComponent(lookup)}`);
                    setUserCard(data);
                    flash("Найден");
                  })
                }
              >
                Найти
              </Btn>
            </div>
            {userCard ? (
              <pre className="mt-4 overflow-auto whitespace-pre-wrap text-xs text-white/75">{pre(userCard)}</pre>
            ) : null}
          </Card>

          <Card title="Список">
            <div className="mb-3 flex flex-wrap gap-2">
              {["active", "recent", "trial", "all"].map((s) => (
                <Btn key={s} onClick={() => setUserStatus(s)} className={userStatus === s ? "!bg-sky-400 !text-black" : ""}>
                  {s}
                </Btn>
              ))}
              <Btn onClick={loadUsers}>Обновить</Btn>
            </div>
            <div className="overflow-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-white/50">
                  <tr>
                    <th className="py-2 pr-3">TG</th>
                    <th className="py-2 pr-3">User</th>
                    <th className="py-2 pr-3">Sub</th>
                    <th className="py-2">Ends</th>
                  </tr>
                </thead>
                <tbody>
                  {userRows.map((u: any, i: number) => {
                    const tid = u.telegram_id || u.user?.telegram_id;
                    const username = u.username || u.user?.username;
                    const status = u.status || u.user?.subscription?.status || "—";
                    const ends = u.ends_at || u.user?.subscription?.ends_at || "—";
                    return (
                      <tr key={i} className="border-t border-white/5">
                        <td className="py-2 pr-3">
                          <button
                            className="text-sky-300 hover:underline"
                            onClick={() =>
                              run(async () => {
                                setUserCard(await adminFetch(`/users/${tid}`));
                                setTgId(String(tid || ""));
                              })
                            }
                          >
                            {tid}
                          </button>
                        </td>
                        <td className="py-2 pr-3">@{username || "—"}</td>
                        <td className="py-2 pr-3">{status}</td>
                        <td className="py-2">{ends}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {tab === "orders" && (
        <Card title="Ожидают оплаты">
          <div className="mb-3">
            <Btn onClick={loadOrders}>Обновить</Btn>
          </div>
          <div className="space-y-3">
            {orderRows.length === 0 ? <p className="text-white/50">Пусто</p> : null}
            {orderRows.map((o: any, i: number) => (
              <div key={i} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 px-3 py-3">
                <div className="text-sm">
                  <div>
                    <span className="text-white/50">label:</span> <code>{o.payment_label || o.label}</code>
                  </div>
                  <div>
                    {o.amount} {o.currency || "RUB"} · tg {o.telegram_id || o.user?.telegram_id || "—"} ·{" "}
                    {o.plan || o.plan_name || o.meta?.title || "—"}
                  </div>
                </div>
                <Btn
                  tone="primary"
                  onClick={() =>
                    run(async () => {
                      const label = o.payment_label || o.label;
                      const res = await adminFetch(`/orders/${encodeURIComponent(label)}/confirm`, {
                        method: "POST",
                      });
                      flash(`Подтверждено: ${pre(res)}`);
                      await loadOrders();
                    })
                  }
                >
                  Подтвердить
                </Btn>
              </div>
            ))}
          </div>
        </Card>
      )}

      {tab === "proxy" && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card title="MTProto на сервере">
            <pre className="overflow-auto whitespace-pre-wrap text-sm text-white/80">{pre(proxyInfo)}</pre>
            <div className="mt-3">
              <Btn onClick={loadProxyInfo}>Обновить</Btn>
            </div>
          </Card>
          <Card title="Выдать / продлить / отключить прокси">
            <div className="space-y-3">
              <Field label="Telegram ID" value={proxyTgId} onChange={(e) => setProxyTgId(e.target.value)} />
              <Field label="Дни" value={proxyDays} onChange={(e) => setProxyDays(e.target.value)} />
              <div className="flex flex-wrap gap-2 pt-2">
                <Btn
                  tone="primary"
                  onClick={() =>
                    run(async () => {
                      const res = await adminFetch(`/users/${proxyTgId}/proxy/grant`, {
                        method: "POST",
                        body: JSON.stringify({ days: Number(proxyDays), stack: false }),
                      });
                      flash(`Прокси выдан: ${pre(res)}`);
                    })
                  }
                >
                  Выдать
                </Btn>
                <Btn
                  onClick={() =>
                    run(async () => {
                      const res = await adminFetch(`/users/${proxyTgId}/proxy/grant`, {
                        method: "POST",
                        body: JSON.stringify({ days: Number(proxyDays), stack: true }),
                      });
                      flash(`Прокси продлён: ${pre(res)}`);
                    })
                  }
                >
                  Продлить
                </Btn>
                <Btn
                  tone="danger"
                  onClick={() =>
                    run(async () => {
                      if (!confirm(`Снять прокси у ${proxyTgId}?`)) return;
                      const res = await adminFetch(`/users/${proxyTgId}/proxy/revoke`, { method: "POST" });
                      flash(`Прокси отключён: ${pre(res)}`);
                    })
                  }
                >
                  Отключить
                </Btn>
              </div>
              <p className="text-xs text-white/45">Без уведомления пользователю. Доступ на аккаунт в боте.</p>
            </div>
          </Card>
        </div>
      )}

      {tab === "actions" && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card title="Выдать / продлить / лимиты / отключить">
            <div className="space-y-3">
              <Field label="Telegram ID" value={tgId} onChange={(e) => setTgId(e.target.value)} />
              <Field label="Дни" value={days} onChange={(e) => setDays(e.target.value)} />
              <Field
                label="Трафик GB (пусто = не менять)"
                value={trafficGb}
                onChange={(e) => setTrafficGb(e.target.value)}
              />
              <label className="flex items-center gap-2 text-sm text-white/70">
                <input type="checkbox" checked={clearTraffic} onChange={(e) => setClearTraffic(e.target.checked)} />
                ∞ без лимита трафика
              </label>
              <Field label="Устройства" value={deviceLimit} onChange={(e) => setDeviceLimit(e.target.value)} />
              <div className="flex flex-wrap gap-2 pt-2">
                <Btn
                  tone="primary"
                  onClick={() =>
                    run(async () => {
                      const body: any = { days: Number(days) };
                      if (clearTraffic) body.clear_traffic_limit = true;
                      else if (trafficGb !== "") body.traffic_gb = Number(trafficGb);
                      if (deviceLimit) body.device_limit = Number(deviceLimit);
                      const res = await adminFetch(`/users/${tgId}/grant`, {
                        method: "POST",
                        body: JSON.stringify(body),
                      });
                      flash(`Выдано: ${pre(res)}`);
                    })
                  }
                >
                  Выдать
                </Btn>
                <Btn
                  onClick={() =>
                    run(async () => {
                      const res = await adminFetch(`/users/${tgId}/extend`, {
                        method: "POST",
                        body: JSON.stringify({ days: Number(days) }),
                      });
                      flash(`Продлено: ${pre(res)}`);
                    })
                  }
                >
                  Продлить
                </Btn>
                <Btn
                  onClick={() =>
                    run(async () => {
                      const body: any = { clear_traffic_limit: clearTraffic };
                      if (!clearTraffic && trafficGb !== "") body.traffic_gb = Number(trafficGb);
                      if (deviceLimit) body.device_limit = Number(deviceLimit);
                      const res = await adminFetch(`/users/${tgId}/limits`, {
                        method: "POST",
                        body: JSON.stringify(body),
                      });
                      flash(`Лимиты: ${pre(res)}`);
                    })
                  }
                >
                  Лимиты
                </Btn>
                <Btn
                  tone="danger"
                  onClick={() =>
                    run(async () => {
                      if (!confirm(`Отключить ${tgId}?`)) return;
                      const res = await adminFetch(`/users/${tgId}/revoke`, { method: "POST" });
                      flash(`Отключено: ${pre(res)}`);
                    })
                  }
                >
                  Отключить
                </Btn>
              </div>
            </div>
          </Card>
          <Card title="Подтвердить оплату по метке">
            <Field label="payment_label" value={lookup} onChange={(e) => setLookup(e.target.value)} />
            <div className="mt-3">
              <Btn
                tone="primary"
                onClick={() =>
                  run(async () => {
                    const res = await adminFetch(`/orders/${encodeURIComponent(lookup)}/confirm`, {
                      method: "POST",
                    });
                    flash(`OK: ${pre(res)}`);
                  })
                }
              >
                Подтвердить
              </Btn>
            </div>
          </Card>
        </div>
      )}

      {tab === "broadcast" && (
        <Card title="Рассылка (единственное действие с уведами)">
          <div className="space-y-3">
            <TextArea
              label="Текст"
              rows={6}
              value={broadcastText}
              onChange={(e) => setBroadcastText(e.target.value)}
            />
            <div className="flex gap-2">
              {["active", "all"].map((a) => (
                <Btn key={a} onClick={() => setAudience(a)} className={audience === a ? "!bg-sky-400 !text-black" : ""}>
                  {a}
                </Btn>
              ))}
            </div>
            <Btn
              tone="primary"
              onClick={() =>
                run(async () => {
                  if (!confirm("Отправить рассылку?")) return;
                  const res = await adminFetch("/broadcast", {
                    method: "POST",
                    body: JSON.stringify({ text: broadcastText, audience }),
                  });
                  flash(`Отправлено: ${pre(res)}`);
                })
              }
            >
              Отправить
            </Btn>
          </div>
        </Card>
      )}

      {tab === "plans" && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card title="Тарифы">
            <Btn onClick={loadPlans}>Обновить</Btn>
            <div className="mt-3 space-y-2 text-sm">
              {planRows.map((p: any) => (
                <div key={p.id} className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2">
                  <div>
                    <div className="font-medium">
                      {p.is_active ? "✅" : "⏸"} {p.name}
                    </div>
                    <div className="text-white/50">
                      {p.slug} · {p.group_name} · {p.duration_days}д · {p.traffic_gb ?? "∞"}GB · {p.price_rub}₽
                    </div>
                  </div>
                  <Btn
                    onClick={() =>
                      run(async () => {
                        await adminFetch(`/plans/${p.id}`, {
                          method: "PATCH",
                          body: JSON.stringify({ is_active: !p.is_active }),
                        });
                        flash("Тариф обновлён");
                        await loadPlans();
                      })
                    }
                  >
                    {p.is_active ? "Выкл" : "Вкл"}
                  </Btn>
                </div>
              ))}
            </div>
          </Card>
          <Card title="Создать тариф">
            <div className="space-y-3">
              <Field label="slug" value={planSlug} onChange={(e) => setPlanSlug(e.target.value)} />
              <Field label="name" value={planName} onChange={(e) => setPlanName(e.target.value)} />
              <Field label="group_name" value={planGroup} onChange={(e) => setPlanGroup(e.target.value)} />
              <Field label="days" value={planDays} onChange={(e) => setPlanDays(e.target.value)} />
              <Field label="traffic_gb (пусто = ∞)" value={planGb} onChange={(e) => setPlanGb(e.target.value)} />
              <Field label="devices" value={planDevices} onChange={(e) => setPlanDevices(e.target.value)} />
              <Field label="price_rub" value={planPrice} onChange={(e) => setPlanPrice(e.target.value)} />
              <Btn
                tone="primary"
                onClick={() =>
                  run(async () => {
                    await adminFetch("/plans", {
                      method: "POST",
                      body: JSON.stringify({
                        slug: planSlug,
                        name: planName,
                        group_name: planGroup,
                        duration_days: Number(planDays),
                        traffic_gb: planGb === "" ? null : Number(planGb),
                        device_limit: Number(planDevices),
                        price_rub: planPrice,
                        is_active: true,
                      }),
                    });
                    flash("Тариф создан");
                    await loadPlans();
                  })
                }
              >
                Создать
              </Btn>
            </div>
          </Card>
        </div>
      )}

      {tab === "promos" && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card title="Промокоды">
            <Btn onClick={loadPromos}>Обновить</Btn>
            <div className="mt-3 space-y-2 text-sm">
              {promoRows.map((p: any) => (
                <div key={p.id || p.code} className="flex items-center justify-between gap-2 rounded-lg border border-white/10 px-3 py-2">
                  <div>
                    <div className="font-medium">
                      {p.is_active ? "✅" : "⏸"} {p.code}
                    </div>
                    <div className="text-white/50">
                      {p.days}д · used {p.used_count}/{p.max_uses ?? "∞"}
                    </div>
                  </div>
                  {p.is_active ? (
                    <Btn
                      tone="danger"
                      onClick={() =>
                        run(async () => {
                          await adminFetch(`/promos/${encodeURIComponent(p.code)}/disable`, { method: "POST" });
                          flash("Промо отключено");
                          await loadPromos();
                        })
                      }
                    >
                      Disable
                    </Btn>
                  ) : null}
                </div>
              ))}
            </div>
          </Card>
          <Card title="Создать промо">
            <div className="space-y-3">
              <Field label="code" value={promoCode} onChange={(e) => setPromoCode(e.target.value)} />
              <Field label="days" value={promoDays} onChange={(e) => setPromoDays(e.target.value)} />
              <Btn
                tone="primary"
                onClick={() =>
                  run(async () => {
                    await adminFetch("/promos", {
                      method: "POST",
                      body: JSON.stringify({ code: promoCode, days: Number(promoDays) }),
                    });
                    flash("Промо создано");
                    await loadPromos();
                  })
                }
              >
                Создать
              </Btn>
            </div>
          </Card>
        </div>
      )}
    </main>
  );
}
