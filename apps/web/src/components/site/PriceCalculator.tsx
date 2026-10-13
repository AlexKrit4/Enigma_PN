"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import NumberFlow from "@number-flow/react";
import { ArrowRight, Minus, Plus, GlobeHemisphereWest } from "@phosphor-icons/react";
import { devicesLabel, formatRub, getToken, monthsLabel, pluralRu, siteApi, type Pricing } from "@/lib/siteApi";

const FALLBACK: Pricing = {
  plan_name: "Обход белых списков",
  base_devices: 5,
  max_devices: 50,
  extra_device_price_per_month: 50,
  trial_days: 1,
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
    <div className="price-calculator">
      <div className="calculator-heading">
        <div>
          <div className="site-eyebrow">ВАША ПОДПИСКА</div>
          <h3>{pricing.plan_name}</h3>
        </div>
        <GlobeHemisphereWest aria-hidden />
      </div>
      <div className="calculator-field">
        <div className="field-heading">
          <span id="period-label">01 / Срок подписки</span>
          {discount > 0 && <span className="discount-badge">выгода {discount}%</span>}
        </div>
        <div className="period-selector" role="group" aria-labelledby="period-label">
          {pricing.periods.map((p) => (
            <button key={p.months} type="button" onClick={() => setMonths(p.months)} className="period-option" aria-pressed={p.months === months}>
              <strong>{monthsLabel(p.months)}</strong>
              <span>{formatRub(p.price)}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="calculator-field">
        <div className="field-heading">
          <span id="devices-label">02 / Количество устройств</span>
          <span className="site-muted">до {pricing.max_devices}</span>
        </div>
        <div className="device-selector" role="group" aria-labelledby="devices-label">
          <button type="button" className="site-stepper" aria-label="Меньше устройств" disabled={devices <= pricing.base_devices} onClick={() => setDevices((d) => Math.max(pricing.base_devices, d - 1))}><Minus size={18} aria-hidden /></button>
          <div className="device-value" aria-live="polite">
            {devicesLabel(devices)}
            <small>{extra > 0 ? `+${extra} сверх тарифа` : "включены в подписку"}</small>
          </div>
          <button type="button" className="site-stepper" aria-label="Больше устройств" disabled={devices >= pricing.max_devices} onClick={() => setDevices((d) => Math.min(pricing.max_devices, d + 1))}><Plus size={18} aria-hidden /></button>
        </div>
        <p className="calculator-help">{pricing.base_devices} включено. Каждое дополнительное — {formatRub(pricing.extra_device_price_per_month)} / месяц.</p>
      </div>
      <div className="price-breakdown">
        <div><span>Тариф на {monthsLabel(months)}</span><span>{formatRub(period.price)}</span></div>
        {extra > 0 && <div><span>+{devicesLabel(extra)} × {months} мес.</span><span>{formatRub(extraPrice)}</span></div>}
      </div>
      <div className="price-total" aria-live="polite" aria-atomic="true">
        <span>Итого за {monthsLabel(months)}</span>
        <div><strong><NumberFlow value={total} locales="ru-RU" format={{ useGrouping: true }} suffix=" ₽" /></strong><small>{formatRub(perMonth)} / месяц</small></div>
      </div>
      {error && <p className="site-alert" role="alert">{error}</p>}
      <button type="button" onClick={submit} disabled={busy} className="site-btn site-btn--orange site-btn--full">
        {busy ? "Секунду…" : submitLabel ?? (mode === "landing" ? "Оформить подписку" : "Перейти к оплате")}
        <ArrowRight size={18} aria-hidden />
      </button>
      {mode === "landing" && (
        <p className="calculator-note">
          {`Сначала ${pricing.trial_days} ${pluralRu(pricing.trial_days, "день", "дня", "дней")} бесплатно. Оплата подписки через ЮMoney.`}
        </p>
      )}
    </div>
  );
}
