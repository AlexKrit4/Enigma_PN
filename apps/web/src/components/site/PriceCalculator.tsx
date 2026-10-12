"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { devicesLabel, formatRub, getToken, monthsLabel, pluralRu, siteApi, type Pricing } from "@/lib/siteApi";

const FALLBACK: Pricing = {
  plan_name: "Обход белых списков",
  base_devices: 5,
  max_devices: 50,
  extra_device_price_per_month: 20,
  trial_days: 3,
  periods: [
    { months: 1, price: 200, per_month: 200 },
    { months: 3, price: 550, per_month: 183 },
    { months: 6, price: 1050, per_month: 175 },
    { months: 12, price: 2000, per_month: 167 },
  ],
};

type Props = {
  mode?: "landing" | "cabinet";
  initialMonths?: number;
  initialDevices?: number;
  onSubmit?: (months: number, extraDevices: number) => Promise<void> | void;
  submitLabel?: string;
};

export default function PriceCalculator({ mode = "landing", initialMonths = 1, initialDevices, onSubmit, submitLabel }: Props) {
  const router = useRouter();
  const [pricing, setPricing] = useState<Pricing>(FALLBACK);
  const [months, setMonths] = useState(initialMonths);
  const [devices, setDevices] = useState(initialDevices ?? FALLBACK.base_devices);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    siteApi.pricing().then(setPricing).catch(() => undefined);
  }, []);

  const period = pricing.periods.find((p) => p.months === months) ?? pricing.periods[0];
  const extra = Math.max(0, devices - pricing.base_devices);
  const extraPrice = extra * months * pricing.extra_device_price_per_month;
  const total = period.price + extraPrice;
  const perMonth = Math.round(total / months);
  const discount = useMemo(() => {
    const full = pricing.periods[0].price * months;
    return full > period.price ? Math.round((1 - period.price / full) * 100) : 0;
  }, [pricing, months, period]);

  async function submit() {
    setError(null);
    if (onSubmit) {
      setBusy(true);
      try {
        await onSubmit(months, extra);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Что-то пошло не так. Попробуйте ещё раз.");
      } finally {
        setBusy(false);
      }
      return;
    }
    const q = `?months=${months}&devices=${devices}`;
    router.push(getToken() ? `/cabinet${q}&buy=1` : `/register${q}`);
  }

  return (
    <div className="card p-6 sm:p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Единый тариф</div>
          <h3 className="font-display mt-2 text-2xl font-semibold sm:text-3xl">{pricing.plan_name}</h3>
          <p className="mt-2 text-sm text-mist/70">Безлимитный трафик · {pricing.base_devices} устройств включено · все страны выхода</p>
        </div>
        <div className="hidden text-right sm:block">
          <div className="font-display text-4xl font-semibold">{formatRub(perMonth)}</div>
          <div className="text-xs text-mist/60">в месяц</div>
        </div>
      </div>

      <div className="mt-7">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium">Срок</span>
          {discount > 0 && <span className="rounded-full bg-copper/15 px-2.5 py-0.5 text-xs font-semibold text-copper">выгода {discount}%</span>}
        </div>
        <div className="grid grid-cols-4 gap-2">
          {pricing.periods.map((p) => (
            <button
              key={p.months}
              type="button"
              onClick={() => setMonths(p.months)}
              className={`rounded-xl border px-2 py-3 text-center transition ${
                p.months === months ? "border-accent bg-accent/15 text-mist" : "border-white/10 bg-white/[0.03] text-mist/70 hover:border-white/25"
              }`}
            >
              <div className="text-sm font-semibold">{monthsLabel(p.months)}</div>
              <div className="mt-0.5 text-xs text-mist/60">{formatRub(p.price)}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium">Устройства</span>
          <span className="text-xs text-mist/60">
            сверх {pricing.base_devices} — {formatRub(pricing.extra_device_price_per_month)} за устройство в месяц
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button type="button" className="stepper" aria-label="Меньше устройств" disabled={devices <= pricing.base_devices} onClick={() => setDevices((d) => Math.max(pricing.base_devices, d - 1))}>−</button>
          <div className="min-w-[9rem] flex-1 text-center">
            <div className="font-display text-2xl font-semibold">{devicesLabel(devices)}</div>
            <div className="text-xs text-mist/60">{extra > 0 ? `+${extra} сверх тарифа` : "входит в тариф"}</div>
          </div>
          <button type="button" className="stepper" aria-label="Больше устройств" disabled={devices >= pricing.max_devices} onClick={() => setDevices((d) => Math.min(pricing.max_devices, d + 1))}>+</button>
        </div>
      </div>

      <div className="mt-7 rounded-2xl bg-white/[0.04] p-4 text-sm">
        <div className="flex justify-between text-mist/70"><span>Тариф на {monthsLabel(months)}</span><span>{formatRub(period.price)}</span></div>
        {extra > 0 && (
          <div className="mt-1.5 flex justify-between text-mist/70"><span>+{devicesLabel(extra)} × {months} мес.</span><span>{formatRub(extraPrice)}</span></div>
        )}
        <div className="mt-3 flex items-end justify-between border-t border-white/10 pt-3">
          <span className="font-medium">Итого</span>
          <span className="font-display text-3xl font-semibold">{formatRub(total)}</span>
        </div>
      </div>

      {error && <p className="mt-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>}

      <button type="button" onClick={submit} disabled={busy} className="btn-primary mt-5 w-full">
        {busy ? "Секунду…" : submitLabel ?? (mode === "landing" ? "Оформить подписку" : "Перейти к оплате")}
      </button>
      {mode === "landing" && (
        <p className="mt-3 text-center text-xs text-mist/55">
          После регистрации — {pricing.trial_days} {pluralRu(pricing.trial_days, "день", "дня", "дней")} бесплатно, без карты. Оплата через ЮMoney.
        </p>
      )}
    </div>
  );
}
