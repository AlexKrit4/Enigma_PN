"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ArrowLeft, Check, TelegramLogo, X } from "@phosphor-icons/react";
import {
  formatDate,
  formatRub,
  getToken,
  siteApi,
  type AdminOverview,
  type AdminPayment,
  type AdminUser,
} from "@/lib/siteApi";

function subStatusLabel(status: string): string {
  if (status === "trial") return "пробный период";
  if (status === "active") return "оплаченная";
  return status;
}

export default function AdminPanel() {
  const router = useRouter();
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [payments, setPayments] = useState<AdminPayment[]>([]);
  const [pending, setPending] = useState<AdminPayment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const [o, u, p, pend] = await Promise.all([
          siteApi.adminOverview(),
          siteApi.adminUsers(),
          siteApi.adminPayments("paid"),
          siteApi.adminPayments("pending"),
        ]);
        setOverview(o);
        setUsers(u);
        setPayments(p);
        setPending(pend);
      } catch (e) {
        const status = e instanceof Error && "status" in e ? (e as { status: number }).status : 0;
        if (status === 401) {
          router.replace("/login");
          return;
        }
        if (status === 403) {
          setDenied(true);
          return;
        }
        setError(e instanceof Error ? e.message : "Не удалось загрузить данные.");
      }
    })();
  }, [router]);

  const chart = useMemo(() => {
    if (!overview) return [];
    const byDay = new Map(overview.revenue_daily.map((d) => [d.day, Number(d.amount)]));
    const days: { day: string; amount: number }[] = [];
    const today = new Date();
    for (let i = 29; i >= 0; i--) {
      const d = new Date(today.getTime() - i * 86400000);
      const key = d.toISOString().slice(0, 10);
      days.push({ day: key, amount: byDay.get(key) ?? 0 });
    }
    const max = Math.max(...days.map((d) => d.amount), 1);
    return days.map((d) => ({ ...d, pct: Math.max(2, Math.round((d.amount / max) * 100)) }));
  }, [overview]);

  if (denied) {
    return (
      <div className="site-container">
        <div className="page-heading">
          <h1>Страница не найдена.</h1>
          <Link href="/" className="site-link">На главную</Link>
        </div>
      </div>
    );
  }

  if (!overview) {
    return <div className="loading-state" role="status">{error ?? "Загружаем панель…"}</div>;
  }

  const activeSubs = users.filter((u) => u.subscription);
  const expiringSoon = activeSubs.filter((u) => u.subscription!.days_left <= 3);

  const stats = [
    { label: "зарегистрировано на сайте", value: overview.users_site },
    { label: "подтвердили почту", value: overview.users_verified },
    { label: "новых за 7 дней", value: overview.users_new_7d },
    { label: "новых за 30 дней", value: overview.users_new_30d },
    { label: "активных подписок", value: overview.subscriptions_active },
    { label: "из них пробных", value: overview.subscriptions_trial },
    { label: "из них оплаченных", value: overview.subscriptions_paid },
    { label: "истекает ≤3 дн.", value: overview.subscriptions_expiring_3d },
    { label: "успешных платежей", value: overview.orders_paid },
    { label: "ожидают оплаты", value: overview.orders_pending },
    { label: "выручка всего", value: formatRub(overview.revenue_rub), raw: true },
    { label: "выручка за 30 дней", value: formatRub(overview.revenue_30d), raw: true },
    { label: "выручка за 7 дней", value: formatRub(overview.revenue_7d), raw: true },
    { label: "средний чек", value: formatRub(overview.avg_check), raw: true },
  ];

  const funnel = [
    { label: "зарегистрировались", value: overview.users_site },
    { label: "подтвердили почту", value: overview.users_verified },
    { label: "с активной подпиской", value: overview.site_users_with_sub },
    { label: "оплатили хотя бы раз", value: overview.paying_site_users },
  ];
  const funnelBase = funnel[0].value || 1;

  return (
    <div className="site-container">
      <div className="page-heading dashboard-top">
        <div>
          <div className="site-eyebrow">АДМИН-ПАНЕЛЬ</div>
          <h1>Сводка по сайту.</h1>
        </div>
        <Link href="/cabinet" className="site-btn site-btn--outline site-btn--small">
          <ArrowLeft size={16} aria-hidden /> В кабинет
        </Link>
      </div>

      {error && <div className="site-alert" role="alert">{error}</div>}

      <div className="admin-stats">
        {stats.map((s) => (
          <div className="admin-stat" key={s.label}>
            <strong>{s.value}</strong>
            <span>{s.label}</span>
          </div>
        ))}
      </div>

      <section className="site-panel">
        <h2>Конверсия сайта</h2>
        <div className="funnel">
          {funnel.map((f) => (
            <div className="funnel-row" key={f.label}>
              <span className="funnel-label">{f.label}</span>
              <div className="funnel-bar">
                <div
                  className="funnel-fill"
                  style={{ width: `${Math.max(2, Math.round((f.value / funnelBase) * 100))}%` }}
                />
              </div>
              <span className="funnel-value">
                {f.value} · {Math.round((f.value / funnelBase) * 100)}%
              </span>
            </div>
          ))}
        </div>
      </section>

      <section className="site-panel">
        <h2>Выручка по дням — 30 дней</h2>
        {chart.every((d) => d.amount === 0) ? (
          <p className="site-panel-description">За последние 30 дней оплат не было.</p>
        ) : (
          <div className="admin-chart" role="img" aria-label="Выручка по дням за 30 дней">
            {chart.map((d) => (
              <div
                key={d.day}
                className={`admin-chart-bar${d.amount > 0 ? " is-filled" : ""}`}
                style={{ height: `${d.pct}%` }}
                title={`${d.day}: ${formatRub(d.amount)}`}
              />
            ))}
          </div>
        )}
      </section>

      <section className="site-panel">
        <h2>Активные подписки ({activeSubs.length})</h2>
        {activeSubs.length === 0 ? (
          <p className="site-panel-description">Сейчас нет пользователей с активной подпиской.</p>
        ) : (
          <ul className="order-list">
            {activeSubs.map((u) => {
              const s = u.subscription!;
              return (
                <li key={u.id}>
                  <div className="order-info">
                    <strong>{u.email}</strong>
                    <small>
                      {subStatusLabel(s.status)} · {s.devices_connected}/{s.device_limit} устр. подключено
                      {" · "}трафик {s.traffic_used_gb} ГБ · осталось {s.days_left} дн.
                      {s.days_left <= 3 ? " · скоро истекает" : ""}
                    </small>
                  </div>
                  <div className="order-amount"><div>до {formatDate(s.ends_at)}</div></div>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {expiringSoon.length > 0 && (
        <section className="site-panel">
          <h2>Истекают в ближайшие 3 дня ({expiringSoon.length})</h2>
          <ul className="order-list">
            {expiringSoon.map((u) => (
              <li key={u.id}>
                <div className="order-info">
                  <strong>{u.email}</strong>
                  <small>
                    {subStatusLabel(u.subscription!.status)} · осталось {u.subscription!.days_left} дн.
                  </small>
                </div>
                <div className="order-amount"><div>до {formatDate(u.subscription!.ends_at)}</div></div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="site-panel">
        <h2>Успешные платежи ({payments.length})</h2>
        {payments.length === 0 ? (
          <p className="site-panel-description">Оплаченных заказов пока нет.</p>
        ) : (
          <ul className="order-list">
            {payments.map((p) => (
              <li key={p.id}>
                <div className="order-info">
                  <strong>{p.title || "Подписка"}</strong>
                  <small>
                    {p.user} · оплачен {formatDate(p.paid_at)} · {p.provider}
                    {p.kind ? ` · ${p.kind}` : ""}
                  </small>
                </div>
                <div className="order-amount">
                  <div>{formatRub(p.amount)}</div>
                  <span className="order-paid">Оплачен</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="site-panel">
        <h2>Ожидают оплаты ({pending.length})</h2>
        {pending.length === 0 ? (
          <p className="site-panel-description">Нет неоплаченных заказов.</p>
        ) : (
          <ul className="order-list">
            {pending.map((p) => (
              <li key={p.id}>
                <div className="order-info">
                  <strong>{p.title || "Подписка"}</strong>
                  <small>{p.user} · создан {formatDate(p.created_at)}</small>
                </div>
                <div className="order-amount">
                  <div>{formatRub(p.amount)}</div>
                  <small>не оплачен</small>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="site-panel">
        <h2>Пользователи ({users.length})</h2>
        {users.length === 0 ? (
          <p className="site-panel-description">Пока никто не регистрировался.</p>
        ) : (
          <ul className="order-list">
            {users.map((u) => (
              <li key={u.id}>
                <div className="order-info">
                  <strong>
                    {u.email}
                    {u.telegram_linked && (
                      <TelegramLogo size={14} aria-hidden className="admin-tg" />
                    )}
                  </strong>
                  <small>
                    с {formatDate(u.created_at)} ·{" "}
                    {u.subscription
                      ? `${u.subscription.status === "trial" ? "триал" : "активна"} до ${formatDate(u.subscription.ends_at)}`
                      : u.last_sub_ends_at
                        ? `подписка была до ${formatDate(u.last_sub_ends_at)}`
                        : "без подписки"}
                    {" · "}оплат: {u.orders_paid} на {formatRub(u.total_paid)}
                    {u.is_admin ? " · админ" : ""}
                  </small>
                </div>
                <div className="order-amount">
                  {u.email_verified
                    ? <span className="order-paid"><Check size={14} aria-hidden /> почта</span>
                    : <small><X size={14} aria-hidden /> не подтверждена</small>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
