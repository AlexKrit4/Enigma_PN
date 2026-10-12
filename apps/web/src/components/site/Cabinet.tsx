"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
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
    return <div className="py-24 text-center text-mist/60">{error ?? "Загружаем кабинет…"}</div>;
  }

  const initialMonths = Number(params.get("months")) || 1;
  const initialDevices = Number(params.get("devices")) || undefined;

  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Личный кабинет</div>
          <h1 className="font-display mt-2 text-3xl font-semibold sm:text-4xl">{me.email}</h1>
        </div>
        <button onClick={logout} className="btn-ghost !px-4 !py-2 !text-sm">Выйти</button>
      </div>

      {notice && <div className="mt-6 rounded-2xl border border-accent/30 bg-accent/10 px-5 py-4 text-sm text-mist">{notice}</div>}
      {error && <div className="mt-6 rounded-2xl bg-red-500/10 px-5 py-4 text-sm text-red-200">{error}</div>}

      <div className="mt-8 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <section className="card p-6 sm:p-8">
            {sub ? (
              <>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${isTrial ? "bg-copper/15 text-copper" : "bg-accent/15 text-accent"}`}>
                        {isTrial ? "Пробный период" : "Подписка активна"}
                      </span>
                    </div>
                    <h2 className="font-display mt-3 text-2xl font-semibold">{isTrial ? "Обход белых списков · пробный период" : sub.title || "Обход белых списков"}</h2>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-mist/55">действует до</div>
                    <div className="mt-0.5 font-medium">{formatDate(sub.ends_at)}</div>
                  </div>
                </div>
                <dl className="mt-6 grid grid-cols-3 gap-4 text-sm">
                  <div className="rounded-xl bg-white/[0.04] p-4"><dt className="text-xs text-mist/55">Осталось</dt><dd className="font-display mt-1 text-xl">{sub.days_left ?? 0} дн.</dd></div>
                  <div className="rounded-xl bg-white/[0.04] p-4"><dt className="text-xs text-mist/55">Устройства</dt><dd className="font-display mt-1 text-xl">{sub.devices_used} из {sub.device_limit}</dd></div>
                  <div className="rounded-xl bg-white/[0.04] p-4"><dt className="text-xs text-mist/55">Трафик</dt><dd className="font-display mt-1 text-xl">{sub.traffic_limit_gb == null ? "∞" : `${sub.traffic_limit_gb} ГБ`}</dd></div>
                </dl>

                <div className="mt-7">
                  <div className="text-sm font-semibold">Подключение</div>
                  <p className="mt-1 text-sm text-mist/65">Установите приложение Happ и нажмите кнопку — подписка добавится сама.</p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    {(sub.happ_open_url || sub.happ_deep_link) && (
                      <a href={sub.happ_open_url || sub.happ_deep_link || "#"} className="btn-primary">Добавить в Happ</a>
                    )}
                    <button type="button" onClick={copyLink} className="btn-ghost">{copied ? "Скопировано" : "Скопировать ссылку подписки"}</button>
                    <Link href="/setup" className="btn-ghost">Инструкция</Link>
                  </div>
                </div>

                <div className="mt-7 flex flex-wrap gap-3 border-t border-white/10 pt-6">
                  <button type="button" onClick={() => setShowBuy((v) => !v)} className={isTrial ? "btn-primary" : "btn-ghost"}>
                    {isTrial ? "Оформить подписку" : showBuy ? "Скрыть продление" : "Продлить подписку"}
                  </button>
                </div>
              </>
            ) : (
              <>
                <h2 className="font-display text-2xl font-semibold">Подписки пока нет</h2>
                <p className="mt-2 text-sm text-mist/65">Выберите срок и количество устройств — доступ появится сразу после оплаты.</p>
              </>
            )}
          </section>

          {(showBuy || !sub) && (
            <section id="buy" className="scroll-mt-24">
              <PriceCalculator mode="cabinet" initialMonths={initialMonths} initialDevices={initialDevices} onSubmit={buy} submitLabel={sub && !isTrial ? "Продлить и оплатить" : "Перейти к оплате"} />
              {sub && !isTrial && <p className="mt-3 text-xs text-mist/55">Новый срок прибавится к текущему — вы ничего не потеряете.</p>}
            </section>
          )}

          {sub && sub.status === "active" && (
            <section className="card p-6 sm:p-8">
              <h2 className="font-display text-xl font-semibold">Добавить устройства</h2>
              <p className="mt-1 text-sm text-mist/65">Доплата — 20 ₽ за устройство за каждый оставшийся месяц подписки.</p>
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <button type="button" className="stepper" disabled={extra <= 1} onClick={() => setExtra((v) => Math.max(1, v - 1))}>−</button>
                <div className="min-w-[8rem] text-center font-display text-xl">+{devicesLabel(extra)}</div>
                <button type="button" className="stepper" onClick={() => setExtra((v) => v + 1)}>+</button>
                <div className="ml-auto text-right">
                  <div className="text-xs text-mist/55">{devQuote ? `до конца подписки · ${monthsLabel(devQuote.months)}` : ""}</div>
                  <div className="font-display text-2xl font-semibold">{devQuote ? formatRub(devQuote.total) : "—"}</div>
                </div>
              </div>
              <button type="button" onClick={buyDevices} disabled={devBusy || !devQuote} className="btn-ghost mt-5 w-full">{devBusy ? "Секунду…" : "Доплатить и добавить"}</button>
            </section>
          )}
        </div>

        <div className="space-y-6">
          <section className="card p-6 sm:p-8">
            <h2 className="font-display text-xl font-semibold">Устройства</h2>
            {sub?.devices && sub.devices.length > 0 ? (
              <ul className="mt-4 divide-y divide-white/10">
                {sub.devices.map((d) => (
                  <li key={d.id} className="flex items-center justify-between gap-3 py-3 text-sm">
                    <div>
                      <div className="font-medium">{d.label || d.device_model || "Устройство"}</div>
                      <div className="text-xs text-mist/55">{[d.device_os, d.last_seen_at ? `был в сети ${formatDate(d.last_seen_at)}` : null].filter(Boolean).join(" · ")}</div>
                    </div>
                    <button type="button" onClick={() => kick(d.id)} disabled={kicking === d.id} className="text-xs text-mist/60 hover:text-red-300">{kicking === d.id ? "…" : "Отключить"}</button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-mist/60">Пока ни одно устройство не подключалось. Добавьте подписку в Happ — оно появится здесь.</p>
            )}
          </section>

          <section className="card p-6 sm:p-8">
            <h2 className="font-display text-xl font-semibold">Платежи</h2>
            {orders.length === 0 ? (
              <p className="mt-3 text-sm text-mist/60">Платежей пока не было.</p>
            ) : (
              <ul className="mt-4 divide-y divide-white/10 text-sm">
                {orders.map((o) => (
                  <li key={o.id} className="flex items-center justify-between gap-3 py-3">
                    <div>
                      <div className="font-medium">{o.title || "Подписка"}</div>
                      <div className="text-xs text-mist/55">{formatDate(o.created_at)}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium">{formatRub(o.amount)}</div>
                      {o.status === "paid" ? (
                        <div className="text-xs text-accent">оплачен</div>
                      ) : o.status === "pending" ? (
                        <Link href={`/pay/${o.id}`} className="text-xs text-copper">оплатить</Link>
                      ) : (
                        <div className="text-xs text-mist/50">отменён</div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
