"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SlotMachine, type BonusRoundView } from "../../components/SlotMachine";
import {
  apiGet,
  apiPost,
  fetchPlans,
  Me,
  miniappAuth,
  Sub,
} from "../../lib/miniappApi";

type Tab = "home" | "plans" | "casino" | "help";

type TgWebApp = {
  initData: string;
  ready: () => void;
  expand: () => void;
  close: () => void;
  openLink: (url: string) => void;
  themeParams?: Record<string, string>;
  MainButton: { hide: () => void };
  HapticFeedback?: { impactOccurred: (style: string) => void };
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TgWebApp };
  }
}

function formatDate(iso?: string) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
  } catch {
    return iso;
  }
}

function SubCard({ sub, brand }: { sub: Sub | null | undefined; brand: string }) {
  if (!sub) {
    return (
      <div className="ma-card">
        <h2>Подписка {brand}</h2>
        <p className="ma-muted">Пока нет активной подписки. Выберите тариф.</p>
      </div>
    );
  }
  const limit = sub.traffic_limit_gb;
  const used = sub.traffic_used_gb ?? 0;
  const traffic = `${used} / ${limit == null ? "∞" : limit} ГБ`;
  return (
    <div className="ma-card">
      <h2>{sub.title || sub.plan?.name || "Подписка"}</h2>
      <ul className="ma-list">
        <li>
          <span>Статус</span>
          <b>{sub.status}</b>
        </li>
        <li>
          <span>До</span>
          <b>{formatDate(sub.ends_at)}</b>
        </li>
        <li>
          <span>Осталось дней</span>
          <b>{sub.days_left ?? "—"}</b>
        </li>
        <li>
          <span>Трафик</span>
          <b>{traffic}</b>
        </li>
        <li>
          <span>Устройства</span>
          <b>
            {sub.devices_used ?? 0} / {sub.device_limit ?? "—"}
          </b>
        </li>
      </ul>
      {sub.happ_open_url ? (
        <a className="ma-btn ma-btn-primary" href={sub.happ_open_url} target="_blank" rel="noreferrer">
          Открыть в Happ
        </a>
      ) : null}
    </div>
  );
}

export default function MiniAppPage() {
  const [tab, setTab] = useState<Tab>("home");
  const [token, setToken] = useState<string>("");
  const [me, setMe] = useState<Me | null>(null);
  const [brand, setBrand] = useState("Enigma_PN");
  const [support, setSupport] = useState("@alexkr1t");
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [plans, setPlans] = useState<
    Array<{
      id: string;
      name: string;
      group_name?: string;
      price_rub: number;
      traffic_gb?: number | null;
      duration_days?: number;
    }>
  >([]);
  const [planGroup, setPlanGroup] = useState<"ограниченный" | "вечный" | "custom">("ограниченный");
  const [casinoMsg, setCasinoMsg] = useState("");
  const [casinoEligible, setCasinoEligible] = useState(false);
  const [casinoHint, setCasinoHint] = useState("");
  const [paytable, setPaytable] = useState<Array<{ symbol: string; pay: number; note?: string }>>([]);
  const [grid, setGrid] = useState<string[]>(Array(9).fill("❓"));
  const [resultGrid, setResultGrid] = useState<string[] | null>(null);
  const pendingBookRef = useRef<string[] | null>(null);
  const pendingMsgRef = useRef("");
  const pendingWinDaysRef = useRef(0);
  const pendingBonusRef = useRef<BonusRoundView[] | null>(null);
  const settleWaiterRef = useRef<(() => void) | null>(null);
  const [winLines, setWinLines] = useState<number[]>([]);
  const [spinning, setSpinning] = useState(false);
  const [inBonus, setInBonus] = useState(false);
  const [multiplier, setMultiplier] = useState(1);
  const [bonusSpinsLeft, setBonusSpinsLeft] = useState<number | null>(null);
  const [bonusIntro, setBonusIntro] = useState(false);
  const [bonusEndTotal, setBonusEndTotal] = useState<number | null>(null);
  const [devices, setDevices] = useState<Array<{ id: string; label?: string }>>([]);
  const [customGb, setCustomGb] = useState(30);
  const [customDays, setCustomDays] = useState(30);
  const [customDev, setCustomDev] = useState(3);
  const [customQuote, setCustomQuote] = useState<{ total?: number; title?: string } | null>(null);

  const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : undefined;

  const refreshMe = useCallback(
    async (jwt: string) => {
      const user = await apiGet<Me>("/api/v1/me", jwt);
      setMe(user);
      try {
        const st = await apiGet<{
          eligible: boolean;
          message: string;
          enabled: boolean;
          paytable?: Array<{ symbol: string; pay: number; note?: string }>;
        }>("/api/v1/miniapp/casino/status", jwt);
        setCasinoEligible(Boolean(st.eligible));
        setCasinoHint(st.message);
        if (st.paytable?.length) setPaytable(st.paytable);
      } catch {
        setCasinoEligible(false);
      }
      try {
        const d = await apiGet<{ devices: Array<{ id: string; label?: string }> }>(
          "/api/v1/me/devices",
          jwt
        );
        setDevices(d.devices || []);
      } catch {
        setDevices([]);
      }
    },
    []
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const webapp = window.Telegram?.WebApp;
        webapp?.ready();
        webapp?.expand();
        webapp?.MainButton?.hide();
        const initData = webapp?.initData || "";
        if (!initData) {
          // Dev fallback outside Telegram
          setError("Откройте приложение из Telegram-бота.");
          setLoading(false);
          return;
        }
        const auth = await miniappAuth(initData);
        if (cancelled) return;
        setToken(auth.access_token);
        setBrand(auth.brand_name || "Enigma_PN");
        setSupport(auth.support_telegram || "@alexkr1t");
        setMe(auth.user);
        await refreshMe(auth.access_token);
        const p = await fetchPlans();
        if (!cancelled) setPlans(p);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshMe]);

  const filteredPlans = useMemo(() => {
    if (planGroup === "custom") return [];
    return plans.filter((p) => (p.group_name || "").toLowerCase() === planGroup);
  }, [plans, planGroup]);

  async function claimTrial() {
    if (!token) return;
    try {
      await apiPost("/api/v1/miniapp/trial", token);
      await refreshMe(token);
      tg?.HapticFeedback?.impactOccurred("medium");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function buyPlan(planId: string) {
    if (!token) return;
    try {
      const order = await apiPost<{ payment_url: string }>("/api/v1/miniapp/orders", token, {
        plan_id: planId,
      });
      if (order.payment_url) {
        tg?.openLink(order.payment_url) || window.open(order.payment_url, "_blank");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function quoteCustom() {
    if (!token) return;
    try {
      const q = await apiPost<{ total: number; title: string }>(
        "/api/v1/miniapp/orders/custom/quote",
        token,
        { traffic_gb: customGb, days: customDays, device_limit: customDev }
      );
      setCustomQuote(q);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function buyCustom() {
    if (!token) return;
    try {
      const order = await apiPost<{ payment_url: string }>("/api/v1/miniapp/orders/custom", token, {
        traffic_gb: customGb,
        days: customDays,
        device_limit: customDev,
      });
      if (order.payment_url) {
        tg?.openLink(order.payment_url) || window.open(order.payment_url, "_blank");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function kickDevice(id: string) {
    if (!token) return;
    try {
      await apiPost(`/api/v1/me/devices/${id}/kick`, token);
      await refreshMe(token);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  async function spin() {
    if (!token || spinning || inBonus || bonusIntro) return;
    setSpinning(true);
    setResultGrid(null);
    pendingBookRef.current = null;
    pendingMsgRef.current = "";
    pendingWinDaysRef.current = 0;
    pendingBonusRef.current = null;
    setCasinoMsg("");
    setWinLines([]);
    try {
      const res = await apiPost<{
        grid: string[];
        winning_lines: number[];
        win_days: number;
        net_days: number;
        message: string;
        days_left: number;
        is_bonus?: boolean;
        bonus_rounds?: BonusRoundView[];
      }>("/api/v1/miniapp/casino/spin", token);
      pendingBookRef.current = res.grid;
      pendingWinDaysRef.current = res.win_days || 0;
      if (res.is_bonus && res.bonus_rounds?.length) {
        pendingBonusRef.current = res.bonus_rounds;
        pendingMsgRef.current = "";
      } else {
        pendingBonusRef.current = null;
        pendingMsgRef.current =
          res.win_days > 0 ? `Выигрыш: +${res.win_days} дн.` : "Не повезло — день списан.";
      }
      setResultGrid(res.grid);
      setWinLines(res.winning_lines || []);
      await refreshMe(token);
    } catch (e) {
      setCasinoMsg(e instanceof Error ? e.message : String(e));
      pendingBookRef.current = null;
      pendingMsgRef.current = "";
      pendingWinDaysRef.current = 0;
      pendingBonusRef.current = null;
      setResultGrid(null);
      setSpinning(false);
    }
  }

  function waitReelSettle() {
    return new Promise<void>((resolve) => {
      settleWaiterRef.current = resolve;
    });
  }

  function onSpinSettled() {
    const book = pendingBookRef.current;
    if (book?.length === 9) {
      setGrid(book);
    }

    const waiter = settleWaiterRef.current;
    if (waiter) {
      settleWaiterRef.current = null;
      waiter();
      return;
    }

    if (pendingBonusRef.current?.length) {
      setResultGrid(null);
      setSpinning(false);
      setBonusIntro(true);
      tg?.HapticFeedback?.impactOccurred("heavy");
      return;
    }

    setCasinoMsg(pendingMsgRef.current);
    tg?.HapticFeedback?.impactOccurred(pendingWinDaysRef.current > 0 ? "heavy" : "light");
    pendingBookRef.current = null;
    pendingMsgRef.current = "";
    pendingWinDaysRef.current = 0;
    setResultGrid(null);
    setSpinning(false);
  }

  async function startBonusGame() {
    const rounds = pendingBonusRef.current;
    const total = pendingWinDaysRef.current;
    setBonusIntro(false);
    if (!rounds?.length) {
      pendingBonusRef.current = null;
      pendingBookRef.current = null;
      setCasinoMsg(total > 0 ? `Выигрыш: +${total} дн.` : "");
      return;
    }

    setInBonus(true);
    setMultiplier(1);
    setCasinoMsg("");

    for (let i = 0; i < rounds.length; i++) {
      const round = rounds[i];
      setBonusSpinsLeft(rounds.length - i);
      setWinLines([]);
      setCasinoMsg("");
      const settled = waitReelSettle();
      setSpinning(true);
      setResultGrid(null);
      pendingBookRef.current = round.grid;
      await new Promise((r) => setTimeout(r, 40));
      setResultGrid(round.grid);
      setWinLines(round.winning_lines || []);
      await settled;
      setGrid(round.grid);
      setMultiplier(round.multiplier);
      setResultGrid(null);
      setSpinning(false);
      if (round.win_days > 0) {
        setCasinoMsg(`+${round.win_days} дн. · ${round.multiplier}×`);
        tg?.HapticFeedback?.impactOccurred("medium");
      } else if (round.x_hit) {
        setCasinoMsg(`Х! Множитель ${round.multiplier}×`);
        tg?.HapticFeedback?.impactOccurred("light");
      }
      await new Promise((r) => setTimeout(r, 450));
    }

    setBonusSpinsLeft(0);
    setInBonus(false);
    pendingBonusRef.current = null;
    pendingBookRef.current = null;
    pendingMsgRef.current = "";
    setBonusEndTotal(total);
    tg?.HapticFeedback?.impactOccurred(total > 0 ? "heavy" : "light");
  }

  function closeBonusEnd() {
    const total = bonusEndTotal ?? 0;
    setBonusEndTotal(null);
    setMultiplier(1);
    setBonusSpinsLeft(null);
    setCasinoMsg(total > 0 ? `Бонус: +${total} дн.` : "Бонус без выигрыша");
    pendingWinDaysRef.current = 0;
  }

  if (loading) {
    return <div className="ma-shell ma-center">Загрузка…</div>;
  }

  return (
    <div className="ma-shell">
      <header className="ma-header">
        <div>
          <p className="ma-eyebrow">{brand}</p>
          <h1>Кабинет</h1>
        </div>
        <p className="ma-muted">@{me?.username || "user"}</p>
      </header>

      {error ? (
        <div className="ma-alert" onClick={() => setError("")}>
          {error}
        </div>
      ) : null}

      <nav className="ma-tabs">
        {(
          [
            ["home", "Подписка"],
            ["plans", "Тарифы"],
            ["casino", "Казино"],
            ["help", "Помощь"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={tab === id ? "active" : ""}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      {tab === "home" ? (
        <section className="ma-stack">
          <SubCard sub={me?.subscription} brand={brand} />
          {!me?.subscription ? (
            <button type="button" className="ma-btn" onClick={claimTrial}>
              Получить пробный день
            </button>
          ) : null}
          {devices.length ? (
            <div className="ma-card">
              <h2>Устройства</h2>
              <ul className="ma-devices">
                {devices.map((d) => (
                  <li key={d.id}>
                    <span>{d.label || d.id.slice(0, 8)}</span>
                    <button type="button" onClick={() => kickDevice(d.id)}>
                      Отключить
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      {tab === "plans" ? (
        <section className="ma-stack">
          <div className="ma-seg">
            <button type="button" className={planGroup === "ограниченный" ? "active" : ""} onClick={() => setPlanGroup("ограниченный")}>
              Пакет ГБ
            </button>
            <button type="button" className={planGroup === "вечный" ? "active" : ""} onClick={() => setPlanGroup("вечный")}>
              Безлимит
            </button>
            <button type="button" className={planGroup === "custom" ? "active" : ""} onClick={() => setPlanGroup("custom")}>
              Свой
            </button>
          </div>

          {planGroup !== "custom" ? (
            <div className="ma-stack">
              {filteredPlans.map((p) => (
                <button key={p.id} type="button" className="ma-plan" onClick={() => buyPlan(p.id)}>
                  <span>{p.name}</span>
                  <b>{p.price_rub} ₽</b>
                </button>
              ))}
              {!filteredPlans.length ? <p className="ma-muted">Тарифы скоро появятся.</p> : null}
            </div>
          ) : (
            <div className="ma-card ma-stack">
              <label>
                ГБ
                <input type="number" min={1} value={customGb} onChange={(e) => setCustomGb(Number(e.target.value))} />
              </label>
              <label>
                Дни
                <input type="number" min={1} value={customDays} onChange={(e) => setCustomDays(Number(e.target.value))} />
              </label>
              <label>
                Устройства
                <input type="number" min={1} max={20} value={customDev} onChange={(e) => setCustomDev(Number(e.target.value))} />
              </label>
              <button type="button" className="ma-btn" onClick={quoteCustom}>
                Посчитать
              </button>
              {customQuote ? (
                <>
                  <p>
                    {customQuote.title}: <b>{customQuote.total} ₽</b>
                  </p>
                  <button type="button" className="ma-btn ma-btn-primary" onClick={buyCustom}>
                    Оплатить
                  </button>
                </>
              ) : null}
            </div>
          )}
        </section>
      ) : null}

      {tab === "casino" ? (
        <section className="ma-stack">
          <div className="ma-card">
            <h2>Слот 3×3</h2>
            <p className="ma-muted">
              Ставка 1 день · RTP 96% · макс. выигрыш 30 дней. В×3 — бонус 7 спинов. Только
              безлимитный трафик.
            </p>
            {!casinoEligible ? <p className="ma-alert soft">{casinoHint || "Недоступно"}</p> : null}
            <SlotMachine
              grid={grid}
              resultGrid={resultGrid}
              winningLines={winLines}
              spinning={spinning}
              disabled={!casinoEligible || inBonus || bonusIntro || bonusEndTotal != null}
              onSpin={spin}
              onSettled={onSpinSettled}
              message={casinoMsg}
              daysLeft={me?.subscription?.days_left}
              paytable={paytable}
              inBonus={inBonus}
              multiplier={multiplier}
              bonusSpinsLeft={bonusSpinsLeft}
            />
          </div>
        </section>
      ) : null}

      {bonusIntro ? (
        <div className="ma-modal-backdrop" role="dialog" aria-modal="true">
          <div className="ma-modal">
            <h3>Bonus! 7 Спинов</h3>
            <p>Три «В» — бесплатные спины с множителем. «Х» увеличивает множитель.</p>
            <button type="button" className="ma-btn ma-btn-primary" onClick={startBonusGame}>
              Продолжить
            </button>
          </div>
        </div>
      ) : null}

      {bonusEndTotal != null ? (
        <div className="ma-modal-backdrop" role="dialog" aria-modal="true">
          <div className="ma-modal">
            <h3>Бонус завершён</h3>
            <p>
              Суммарно за бонусную игру: <b>+{bonusEndTotal} дн.</b>
            </p>
            <button type="button" className="ma-btn ma-btn-primary" onClick={closeBonusEnd}>
              Ок
            </button>
          </div>
        </div>
      ) : null}

      {tab === "help" ? (
        <section className="ma-stack">
          <div className="ma-card">
            <h2>Как подключиться</h2>
            <ol className="ma-ol">
              <li>Установите Happ</li>
              <li>Нажмите «Открыть в Happ» на вкладке подписки</li>
              <li>Обновите подписку и включите сервер</li>
            </ol>
            <p className="ma-muted">Поддержка: {support}</p>
          </div>
        </section>
      ) : null}

      <style jsx global>{`
        .ma-shell {
          max-width: 480px;
          margin: 0 auto;
          padding: 16px 16px 96px;
          font-family: var(--font-sans);
          color: #e8eef7;
        }
        .ma-center {
          display: grid;
          place-items: center;
          min-height: 60vh;
        }
        .ma-header {
          display: flex;
          justify-content: space-between;
          align-items: end;
          margin-bottom: 14px;
        }
        .ma-header h1 {
          margin: 0;
          font-family: var(--font-display);
          font-size: 1.75rem;
          letter-spacing: -0.02em;
        }
        .ma-eyebrow {
          margin: 0;
          color: #1fa97a;
          font-size: 0.75rem;
          font-weight: 700;
          text-transform: uppercase;
          letter-spacing: 0.08em;
        }
        .ma-muted {
          color: rgba(232, 238, 247, 0.62);
        }
        .ma-muted.tiny {
          font-size: 0.85rem;
        }
        .ma-tabs {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 6px;
          margin-bottom: 14px;
        }
        .ma-tabs button {
          border: 1px solid rgba(232, 238, 247, 0.12);
          background: rgba(16, 32, 51, 0.7);
          color: inherit;
          border-radius: 12px;
          padding: 10px 6px;
          font-size: 0.78rem;
          font-weight: 600;
        }
        .ma-tabs button.active {
          background: linear-gradient(180deg, #1fa97a, #14825c);
          border-color: transparent;
          color: #04140f;
        }
        .ma-stack {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .ma-card {
          border: 1px solid rgba(232, 238, 247, 0.12);
          background: rgba(10, 22, 36, 0.88);
          border-radius: 18px;
          padding: 16px;
        }
        .ma-card h2 {
          margin: 0 0 10px;
          font-family: var(--font-display);
          font-size: 1.25rem;
        }
        .ma-list {
          list-style: none;
          margin: 0 0 14px;
          padding: 0;
          display: grid;
          gap: 8px;
        }
        .ma-list li {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          font-size: 0.95rem;
        }
        .ma-list span {
          color: rgba(232, 238, 247, 0.55);
        }
        .ma-btn,
        .ma-plan {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
          width: 100%;
          border: 0;
          border-radius: 14px;
          padding: 12px 14px;
          font-weight: 700;
          cursor: pointer;
          background: rgba(232, 238, 247, 0.08);
          color: inherit;
        }
        .ma-btn-primary {
          background: linear-gradient(180deg, #c4a35a, #9a7a35);
          color: #1a1205;
        }
        .ma-btn:disabled {
          opacity: 0.45;
          cursor: not-allowed;
        }
        .ma-plan {
          justify-content: space-between;
          text-align: left;
          border: 1px solid rgba(232, 238, 247, 0.1);
        }
        .ma-seg {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 6px;
        }
        .ma-seg button {
          border-radius: 12px;
          border: 1px solid rgba(232, 238, 247, 0.12);
          background: transparent;
          color: inherit;
          padding: 10px 6px;
          font-size: 0.8rem;
        }
        .ma-seg button.active {
          background: rgba(31, 169, 122, 0.22);
          border-color: rgba(31, 169, 122, 0.5);
        }
        .ma-card label {
          display: grid;
          gap: 6px;
          font-size: 0.85rem;
          color: rgba(232, 238, 247, 0.7);
        }
        .ma-card input {
          border-radius: 10px;
          border: 1px solid rgba(232, 238, 247, 0.15);
          background: rgba(0, 0, 0, 0.25);
          color: inherit;
          padding: 10px 12px;
        }
        .ma-slot {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
          margin: 14px 0;
        }
        .ma-cell {
          aspect-ratio: 1;
          display: grid;
          place-items: center;
          font-size: 1.8rem;
          border-radius: 14px;
          background: rgba(0, 0, 0, 0.35);
          border: 1px solid rgba(232, 238, 247, 0.1);
        }
        .ma-cell.win {
          border-color: #c4a35a;
          box-shadow: 0 0 0 1px rgba(196, 163, 90, 0.45);
          background: rgba(196, 163, 90, 0.15);
        }
        .ma-cell.spin {
          filter: blur(0.4px);
        }
        .ma-casino-msg {
          margin: 10px 0 0;
          font-weight: 600;
        }
        .ma-alert {
          background: rgba(190, 60, 60, 0.18);
          border: 1px solid rgba(190, 60, 60, 0.35);
          border-radius: 12px;
          padding: 10px 12px;
          margin-bottom: 12px;
          font-size: 0.9rem;
        }
        .ma-alert.soft {
          background: rgba(196, 163, 90, 0.12);
          border-color: rgba(196, 163, 90, 0.35);
        }
        .ma-modal-backdrop {
          position: fixed;
          inset: 0;
          z-index: 80;
          display: grid;
          place-items: center;
          padding: 20px;
          background: rgba(2, 8, 14, 0.72);
          backdrop-filter: blur(6px);
        }
        .ma-modal {
          width: min(100%, 360px);
          border-radius: 20px;
          padding: 22px 20px;
          background: linear-gradient(180deg, #122436, #0a1624);
          border: 1px solid rgba(196, 163, 90, 0.4);
          box-shadow: 0 20px 48px rgba(0, 0, 0, 0.45);
          display: grid;
          gap: 12px;
          text-align: center;
        }
        .ma-modal h3 {
          margin: 0;
          font-family: var(--font-display);
          font-size: 1.45rem;
          color: #c4a35a;
        }
        .ma-modal p {
          margin: 0;
          color: rgba(232, 238, 247, 0.78);
          line-height: 1.4;
        }
        .ma-devices {
          list-style: none;
          margin: 0;
          padding: 0;
          display: grid;
          gap: 8px;
        }
        .ma-devices li {
          display: flex;
          justify-content: space-between;
          gap: 8px;
          align-items: center;
        }
        .ma-devices button {
          border: 0;
          border-radius: 10px;
          padding: 8px 10px;
          background: rgba(190, 60, 60, 0.2);
          color: #ffb4b4;
          font-weight: 600;
        }
        .ma-ol {
          margin: 0 0 12px;
          padding-left: 18px;
          display: grid;
          gap: 6px;
        }
      `}</style>
    </div>
  );
}
