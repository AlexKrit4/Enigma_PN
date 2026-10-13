"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Check, CreditCard, ArrowUpRight, WarningCircle } from "@phosphor-icons/react";
import { formatRub, getToken, siteApi, type Order } from "@/lib/siteApi";

export default function PaymentStatus({ orderId }: { orderId: string }) {
  const router = useRouter();
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    let stop = false;
    const load = async () => {
      try {
        const o = await siteApi.order(orderId);
        if (!stop) setOrder(o);
        if (o.status === "paid") return;
      } catch (e) {
        if (!stop) setError(e instanceof Error ? e.message : "Не удалось получить статус оплаты.");
      }
      if (!stop) setTimeout(load, 5000);
    };
    load();
    return () => {
      stop = true;
    };
  }, [orderId, router]);

  if (error && !order) {
    return (
      <div className="payment-panel">
        <div className="payment-icon"><WarningCircle size={28} aria-hidden /></div>
        <h1>Не удалось загрузить заказ</h1>
        <p role="alert">{error}</p>
        <Link href="/cabinet" className="site-btn site-btn--outline site-btn--full form-submit">В личный кабинет</Link>
      </div>
    );
  }
  if (!order) return <div className="loading-state" role="status">Загружаем заказ…</div>;

  if (order.status === "paid") {
    return (
      <div className="payment-panel" role="status">
        <div className="payment-icon payment-icon--success"><Check size={28} aria-hidden /></div>
        <div className="site-eyebrow">ВСЁ ГОТОВО</div>
        <h1>Оплата прошла.</h1>
        <p>{order.title}. Подписка уже активна — осталось добавить её в Happ.</p>
        <Link href="/cabinet" className="site-btn site-btn--dark site-btn--full form-submit">Перейти в кабинет <ArrowUpRight size={18} aria-hidden /></Link>
      </div>
    );
  }

  return (
    <div className="payment-panel">
      <div className="payment-icon"><CreditCard size={28} aria-hidden /></div>
      <div className="site-eyebrow">ОЖИДАЕМ ОПЛАТУ</div>
      <h1>{formatRub(order.amount)}</h1>
      <p>{order.title}</p>
      <p>
        Оплата проходит на сайте ЮMoney. После оплаты эта страница обновится сама — обычно в течение минуты. Вкладку можно не закрывать.
      </p>
      {order.payment_url && (
        <a href={order.payment_url} className="site-btn site-btn--dark site-btn--full form-submit">Перейти к оплате <ArrowUpRight size={18} aria-hidden /></a>
      )}
      <div className="payment-poll" role="status">
        <span className="status-dot" /> Проверяем статус платежа…
      </div>
      <Link href="/cabinet" className="payment-back site-link">Вернуться в кабинет</Link>
    </div>
  );
}
