"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, Check, X } from "@phosphor-icons/react";
import {
  devicesLabel,
  formatDate,
  formatRub,
  getToken,
  siteApi,
  type AdminOverview,
  type AdminPayment,
  type AdminUser,
} from "@/lib/siteApi";

export default function AdminPanel() {
  const router = useRouter();
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [payments, setPayments] = useState<AdminPayment[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const [o, u, p] = await Promise.all([
          siteApi.adminOverview(),
          siteApi.adminUsers(),
          siteApi.adminPayments(),
        ]);
        setOverview(o);
        setUsers(u);
        setPayments(p);
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
  const stats = [
    { label: "зарегистрировано на сайте", value: overview.users_site },
    { label: "подтвердили почту", value: overview.users_verified },
    { label: "активных подписок", value: overview.subscriptions_active },
    { label: "успешных платежей", value: overview.orders_paid },
    { label: "ожидают оплаты", value: overview.orders_pending },
    { label: "выручка", value: formatRub(overview.revenue_rub), raw: true },
  ];

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
        <h2>Активные подписки</h2>
        {activeSubs.length === 0 ? (
          <p className="site-panel-description">Сейчас нет пользователей с активной подпиской.</p>
        ) : (
          <ul className="order-list">
            {activeSubs.map((u) => (
              <li key={u.id}>
                <div className="order-info">
                  <strong>{u.email}</strong>
                  <small>
                    {u.subscription!.status === "trial" ? "пробный период" : "оплаченная"} ·{" "}
                    {devicesLabel(u.subscription!.device_limit)} · осталось {u.subscription!.days_left} дн.
                  </small>
                </div>
                <div className="order-amount"><div>до {formatDate(u.subscription!.ends_at)}</div></div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="site-panel">
        <h2>Успешные платежи</h2>
        {payments.length === 0 ? (
          <p className="site-panel-description">Оплаченных заказов пока нет.</p>
        ) : (
          <ul className="order-list">
            {payments.map((p) => (
              <li key={p.id}>
                <div className="order-info">
                  <strong>{p.title || "Подписка"}</strong>
                  <small>{p.email} · оплачен {formatDate(p.paid_at)}</small>
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
        <h2>Пользователи ({users.length})</h2>
        {users.length === 0 ? (
          <p className="site-panel-description">Пока никто не регистрировался.</p>
        ) : (
          <ul className="order-list">
            {users.map((u) => (
              <li key={u.id}>
                <div className="order-info">
                  <strong>{u.email}</strong>
                  <small>
                    с {formatDate(u.created_at)} ·{" "}
                    {u.subscription
                      ? `${u.subscription.status === "trial" ? "триал" : "активна"} до ${formatDate(u.subscription.ends_at)}`
                      : "без подписки"}
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
