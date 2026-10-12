"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
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
    <form onSubmit={onSubmit} className="card w-full max-w-md p-7 sm:p-9">
      <h1 className="font-display text-3xl font-semibold">Подтвердите почту</h1>
      <p className="mt-2 text-sm text-mist/65">
        Мы отправили код на <span className="font-medium text-mist">{email}</span>. Введите его — и пробный период на 3 дня активируется.
      </p>
      <label className="mt-7 block text-sm font-medium">
        Код из письма
        <input
          inputMode="numeric"
          autoComplete="one-time-code"
          required
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/[^\d]/g, "").slice(0, 8))}
          className="input mt-1.5 text-center font-display text-2xl tracking-[0.4em]"
          placeholder="000000"
        />
      </label>
      {error && <p className="mt-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>}
      {notice && <p className="mt-4 rounded-xl bg-accent/10 px-4 py-3 text-sm text-mist">{notice}</p>}
      <button type="submit" disabled={busy} className="btn-primary mt-6 w-full">
        {busy ? "Секунду…" : "Подтвердить"}
      </button>
      <p className="mt-5 text-center text-sm text-mist/65">
        {cooldown > 0 ? (
          <>Не пришёл код? Отправить снова можно через {cooldown} с.</>
        ) : (
          <>
            Не пришёл код?{" "}
            <button type="button" onClick={resend} className="text-accent">
              Отправить снова
            </button>
          </>
        )}
      </p>
      <p className="mt-4 text-center text-xs text-mist/50">
        Указали другую почту? <Link href="/register" className="underline">Зарегистрироваться заново</Link>
      </p>
    </form>
  );
}
