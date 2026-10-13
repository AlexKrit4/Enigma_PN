"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight } from "@phosphor-icons/react";
import { setToken, siteApi } from "@/lib/siteApi";

const RESEND_SECONDS = 60;

export default function VerifyForm() {
  const router = useRouter();
  const params = useSearchParams();
  const email = params.get("email") || "";
  const months = params.get("months");
  const devices = params.get("devices");
  const next = months ? `/cabinet?months=${months}&devices=${devices ?? ""}&buy=1` : "/cabinet?welcome=1";

  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(RESEND_SECONDS);

  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((v) => v - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  useEffect(() => {
    if (!email) router.replace("/register");
  }, [email, router]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (code.trim().length < 4) {
      setError("Введите код из письма.");
      return;
    }
    setBusy(true);
    try {
      const session = await siteApi.verify(email, code.trim());
      setToken(session.access_token);
      router.replace(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Что-то пошло не так. Попробуйте ещё раз.");
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setError(null);
    setNotice(null);
    try {
      await siteApi.resend(email);
      setCooldown(RESEND_SECONDS);
      setNotice("Отправили код ещё раз. Проверьте почту и папку «Спам».");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить код. Попробуйте позже.");
    }
  }

  return (
    <form onSubmit={onSubmit} className="auth-form">
      <div className="auth-step" aria-label="Шаг 2 из 2: подтверждение почты"><span className="is-current" /><span className="is-current" /></div>
      <h1>Проверьте почту</h1>
      <p className="auth-description">
        Мы отправили код на <strong>{email}</strong>. Введите его — и пробный период на 1 день активируется.
      </p>
      <label className="site-label">
        Код из письма
        <input
          inputMode="numeric"
          autoComplete="one-time-code"
          required
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/[^\d]/g, "").slice(0, 8))}
          className="site-input code-input"
          placeholder="000000"
        />
      </label>
      {error && <p className="site-alert" role="alert">{error}</p>}
      {notice && <p className="site-alert site-alert--success" role="status">{notice}</p>}
      <button type="submit" disabled={busy} className="site-btn site-btn--dark site-btn--full form-submit">
        {busy ? "Секунду…" : "Подтвердить"}
        <ArrowRight size={18} aria-hidden />
      </button>
      <p className="auth-switch">
        {cooldown > 0 ? (
          <>Не пришёл код? Отправить снова можно через {cooldown} с.</>
        ) : (
          <>
            Не пришёл код?{" "}
            <button type="button" onClick={resend} className="site-link">
              Отправить снова
            </button>
          </>
        )}
      </p>
      <p className="auth-legal">
        Указали другую почту? <Link href="/register" className="site-link">Зарегистрироваться заново</Link>
      </p>
    </form>
  );
}
