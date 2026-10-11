"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
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
      <div className="card w-full max-w-md p-8 text-center">
        <p className="text-mist/80">{error}</p>
        <Link href="/cabinet" className="btn-ghost mt-6">В личный кабинет</Link>
      </div>
    );
  }
  if (!order) return <div className="text-mist/60">Загружаем заказ…</div>;

  if (order.status === "paid") {
    return (
      <div className="card w-full max-w-md p-8 text-center">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-accent/15 text-2xl text-accent">✓</div>
        <h1 className="font-display mt-5 text-3xl font-semibold">Оплата прошла</h1>
        <p className="mt-2 text-mist/70">{order.title}. Подписка уже активна — осталось добавить её в Happ.</p>
        <Link href="/cabinet" className="btn-primary mt-7 w-full">Перейти в кабинет</Link>
      </div>
    );
  }

  return (
    <div className="card w-full max-w-md p-8">
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-copper">Ожидаем оплату</div>
      <h1 className="font-display mt-3 text-3xl font-semibold">{formatRub(order.amount)}</h1>
      <p className="mt-2 text-sm text-mist/70">{order.title}</p>
      <p className="mt-6 text-sm leading-relaxed text-mist/70">
        Оплата проходит на сайте ЮMoney. После оплаты эта страница обновится сама — обычно в течение минуты. Вкладку можно не закрывать.
      </p>
      {order.payment_url && (
        <a href={order.payment_url} className="btn-primary mt-6 w-full">Перейти к оплате</a>
      )}
      <div className="mt-4 flex items-center justify-center gap-2 text-xs text-mist/50">
        <span className="h-2 w-2 animate-pulse rounded-full bg-copper" /> Проверяем статус платежа…
      </div>
      <Link href="/cabinet" className="mt-5 block text-center text-sm text-mist/60 hover:text-mist">Вернуться в кабинет</Link>
    </div>
  );
}
