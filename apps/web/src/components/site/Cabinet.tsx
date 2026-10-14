"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { ArrowUpRight, Copy, Check, DeviceMobile, SignOut, ArrowRight, Plus, Minus, Headset } from "@phosphor-icons/react";
import PriceCalculator from "@/components/site/PriceCalculator";
import { devicesLabel, formatDate, formatRub, getToken, monthsLabel, setToken, siteApi, type DevicesQuote, type Me, type Order } from "@/lib/siteApi";

export default function Cabinet() {
  const router = useRouter();
  const params = useSearchParams();
  const [me, setMe] = useState<Me | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [showBuy, setShowBuy] = useState(params.get("buy") === "1");
  const [copied, setCopied] = useState(false);
  const [extra, setExtra] = useState(1);
  const [devQuote, setDevQuote] = useState<DevicesQuote | null>(null);
  const [devBusy, setDevBusy] = useState(false);
  const [kicking, setKicking] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, o] = await Promise.all([siteApi.me(), siteApi.orders()]);
      setMe(m);
      setOrders(o);
      setError(null);
    } catch (e) {
      if (!getToken()) {
        router.replace("/login");
        return;
      }
      setError(e instanceof Error ? e.message : "Не удалось загрузить данные.");
    }
  }, [router]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    load();
    if (params.get("paid") === "1") setNotice("Оплата получена. Если подписка ещё не обновилась — подождите минуту, страница обновится сама.");
    if (params.get("welcome") === "1") setNotice("Почта подтверждена. Пробный период уже активен — добавьте подписку в Happ и проверьте подключение.");
  }, [load, params, router]);

  useEffect(() => {
    if (params.get("paid") !== "1") return;
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [params, load]);

  useEffect(() => {
    if (!me?.subscription || me.subscription.status !== "active") return;
    siteApi.devicesQuote(extra).then(setDevQuote).catch(() => setDevQuote(null));
  }, [extra, me]);

  const sub = me?.subscription ?? null;
  const isTrial = sub?.status === "trial";

  async function buy(months: number, extraDevices: number) {
    const order = await siteApi.createOrder(months, extraDevices);
    if (order.payment_url) window.location.href = order.payment_url;
    else router.push(`/pay/${order.id}`);
  }

  async function buyDevices() {
    setDevBusy(true);
    try {
      const order = await siteApi.createDevicesOrder(extra);
      if (order.payment_url) window.location.href = order.payment_url;
      else router.push(`/pay/${order.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось создать заказ.");
    } finally {
      setDevBusy(false);
    }
  }

  async function kick(id: string) {
    setKicking(id);
    try {
      await siteApi.kickDevice(id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось отключить устройство.");
    } finally {
      setKicking(null);
    }
  }

  function copyLink() {
    if (!sub?.sub_url) return;
    navigator.clipboard?.writeText(sub.sub_url).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function logout() {
    setToken(null);
    router.replace("/");
  }

  if (!me) {
    return <div className="loading-state" role="status">{error ?? "Загружаем кабинет…"}</div>;
  }

  const initialMonths = Number(params.get("months")) || 1;
  const initialDevices = Number(params.get("devices")) || undefined;

  return (
    <div className="site-container">
      <div className="page-heading dashboard-top">
        <div>
          <div className="site-eyebrow">ЛИЧНЫЙ КАБИНЕТ</div>
          <h1>Ваше подключение.</h1>
          <div className="account-email">{me.email}</div>
        </div>
        <div className="dashboard-actions">
          {me.is_admin && <Link href="/panel" className="site-btn site-btn--outline site-btn--small">Панель</Link>}
          <button onClick={logout} className="site-btn site-btn--outline site-btn--small">Выйти <SignOut size={16} aria-hidden /></button>
        </div>
      </div>
      {notice && <div className="site-alert site-alert--success" role="status">{notice}</div>}
      {error && <div className="site-alert" role="alert">{error}</div>}
      <div className="dashboard-grid">
        <div className="dashboard-stack">
          <section className="site-panel subscription-panel">
            {sub ? (
              <>
                <div className="subscription-heading">
                  <div>
                    <span className="site-badge">{isTrial ? "Пробный период" : "Подписка активна"}</span>
                    <h2>{isTrial ? "Обход белых списков" : sub.title || "Обход белых списков"}</h2>
                  </div>
                  <div className="subscription-expiry"><span>Действует до</span>{formatDate(sub.ends_at)}</div>
                </div>
                <dl className="subscription-stats">
                  <div><dt>Осталось</dt><dd>{sub.days_left ?? 0} дн.</dd></div>
                  <div><dt>Устройства</dt><dd>{sub.devices_used} / {sub.device_limit}</dd></div>
                  <div><dt>Трафик</dt><dd>{sub.traffic_limit_gb == null ? "∞" : `${sub.traffic_limit_gb} ГБ`}</dd></div>
                </dl>
                <div className="connect-area">
                  <h3>Добавьте подписку в Happ</h3>
                  <p>Установите приложение и нажмите кнопку. Подписка появится автоматически.</p>
                  <div className="button-row">
                    {(sub.happ_open_url || sub.happ_deep_link) && (
                      <a href={sub.happ_open_url || sub.happ_deep_link || "#"} className="site-btn site-btn--dark">Добавить в Happ <ArrowUpRight size={18} aria-hidden /></a>
                    )}
                    <button type="button" onClick={copyLink} className="site-btn site-btn--outline" aria-live="polite">{copied ? <Check size={17} aria-hidden /> : <Copy size={17} aria-hidden />}{copied ? "Скопировано" : "Скопировать ссылку"}</button>
                  </div>
                </div>
                <div className="panel-bottom">
                  <button type="button" onClick={() => setShowBuy((v) => !v)} className={`site-btn ${isTrial ? "site-btn--orange" : "site-btn--outline"} site-btn--small`} aria-expanded={showBuy}>
                    {isTrial ? "Оформить подписку" : showBuy ? "Скрыть продление" : "Продлить подписку"}
                  </button>
                  <Link href="/setup" className="site-link">Инструкция по подключению</Link>
                </div>
              </>
            ) : (
              <>
                <h2>Подписки пока нет</h2>
                <p className="site-panel-description">Выберите срок и количество устройств — доступ появится сразу после оплаты.</p>
              </>
            )}
          </section>
          {(showBuy || !sub) && (
            <section id="buy">
              <PriceCalculator mode="cabinet" initialMonths={initialMonths} initialDevices={initialDevices} onSubmit={buy} submitLabel={sub && !isTrial ? "Продлить и оплатить" : "Перейти к оплате"} />
              {sub && !isTrial && <p className="calculator-help">Новый срок прибавится к текущему — вы ничего не потеряете.</p>}
            </section>
          )}
          {sub && sub.status === "active" && (
            <section className="site-panel">
              <h2>Ещё устройства?</h2>
              <p className="site-panel-description">20 ₽ за устройство за каждый оставшийся месяц подписки.</p>
              <div className="devices-buy">
                <div className="device-selector">
                  <button type="button" className="site-stepper" aria-label="Меньше дополнительных устройств" disabled={extra <= 1} onClick={() => setExtra((v) => Math.max(1, v - 1))}><Minus size={17} aria-hidden /></button>
                  <div className="device-value">+{devicesLabel(extra)}</div>
                  <button type="button" className="site-stepper" aria-label="Больше дополнительных устройств" onClick={() => setExtra((v) => v + 1)}><Plus size={17} aria-hidden /></button>
                </div>
                <div>
                  <div className="devices-price">{devQuote ? formatRub(devQuote.total) : "—"}</div>
                  <div className="calculator-help">{devQuote ? `до конца подписки · ${monthsLabel(devQuote.months)}` : ""}</div>
                </div>
              </div>
              <button type="button" onClick={buyDevices} disabled={devBusy || !devQuote} className="site-btn site-btn--outline site-btn--full form-submit">{devBusy ? "Секунду…" : "Доплатить и добавить"}<ArrowRight size={17} aria-hidden /></button>
            </section>
          )}
        </div>
        <div className="dashboard-stack">
          <section className="site-panel">
            <h2>Ваши устройства</h2>
            {sub?.devices && sub.devices.length > 0 ? (
              <ul className="device-list">
                {sub.devices.map((d) => (
                  <li key={d.id}>
                    <div className="device-info">
                      <span className="device-icon"><DeviceMobile size={19} aria-hidden /></span>
                      <div><strong>{d.label || d.device_model || "Устройство"}</strong><small>{[d.device_os, d.last_seen_at ? `был в сети ${formatDate(d.last_seen_at)}` : null].filter(Boolean).join(" · ")}</small></div>
                    </div>
                    <button type="button" onClick={() => kick(d.id)} disabled={kicking === d.id} className="site-btn site-btn--outline site-btn--small">{kicking === d.id ? "…" : "Отключить"}</button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="site-panel-description">Пока ни одно устройство не подключалось. Добавьте подписку в Happ — оно появится здесь.</p>
            )}
          </section>
          <section className="site-panel">
            <h2>История платежей</h2>
            {orders.length === 0 ? (
              <p className="site-panel-description">Здесь появятся ваши оплаты и продления. Платежей пока не было.</p>
            ) : (
              <ul className="order-list">
                {orders.map((o) => (
                  <li key={o.id}>
                    <div className="order-info"><strong>{o.title || "Подписка"}</strong><small>{formatDate(o.created_at)}</small></div>
                    <div className="order-amount">
                      <div>{formatRub(o.amount)}</div>
                      {o.status === "paid" ? (
                        <span className="order-paid">Оплачен</span>
                      ) : o.status === "pending" ? (
                        <Link href={`/pay/${o.id}`} className="site-link calculator-help">Оплатить</Link>
                      ) : (
                        <small>Отменён</small>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section className="site-panel support-panel">
            <Headset size={28} aria-hidden />
            <h2 className="form-submit">Поможем подключиться.</h2>
            <p className="site-panel-description">Если что-то не получается — начните с инструкции или напишите нам.</p>
            <Link href="/setup" className="site-btn site-btn--small form-submit">Открыть инструкцию <ArrowUpRight size={16} aria-hidden /></Link>
          </section>
        </div>
      </div>
    </div>
  );
}
