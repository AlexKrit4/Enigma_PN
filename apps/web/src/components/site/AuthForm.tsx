"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { setToken, siteApi } from "@/lib/siteApi";

export default function AuthForm({ mode }: { mode: "register" | "login" }) {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const months = params.get("months");
  const devices = params.get("devices");
  const next = months ? `/cabinet?months=${months}&devices=${devices ?? ""}&buy=1` : "/cabinet";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "register" && password.length < 8) {
      setError("Пароль должен быть не короче 8 символов.");
      return;
    }
    setBusy(true);
    try {
      const session = mode === "register" ? await siteApi.register(email.trim(), password) : await siteApi.login(email.trim(), password);
      setToken(session.access_token);
      router.replace(mode === "register" && !months ? "/cabinet?welcome=1" : next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Что-то пошло не так. Попробуйте ещё раз.");
    } finally {
      setBusy(false);
    }
  }

  const isRegister = mode === "register";
  return (
    <form onSubmit={onSubmit} className="card w-full max-w-md p-7 sm:p-9">
      <h1 className="font-display text-3xl font-semibold">{isRegister ? "Создать аккаунт" : "Войти"}</h1>
      <p className="mt-2 text-sm text-mist/65">
        {isRegister ? "Сразу после регистрации вы получите один день доступа бесплатно." : "Введите почту и пароль от личного кабинета."}
      </p>
      <label className="mt-7 block text-sm font-medium">
        Электронная почта
        <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className="input mt-1.5" placeholder="you@example.com" />
      </label>
      <label className="mt-4 block text-sm font-medium">
        Пароль
        <input type="password" required minLength={isRegister ? 8 : 1} autoComplete={isRegister ? "new-password" : "current-password"} value={password} onChange={(e) => setPassword(e.target.value)} className="input mt-1.5" placeholder={isRegister ? "Не менее 8 символов" : "Ваш пароль"} />
      </label>
      {error && <p className="mt-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>}
      <button type="submit" disabled={busy} className="btn-primary mt-6 w-full">
        {busy ? "Секунду…" : isRegister ? "Зарегистрироваться" : "Войти"}
      </button>
      <p className="mt-5 text-center text-sm text-mist/65">
        {isRegister ? (
          <>Уже есть аккаунт? <Link href={`/login${months ? `?months=${months}&devices=${devices ?? ""}` : ""}`} className="text-accent">Войти</Link></>
        ) : (
          <>Нет аккаунта? <Link href="/register" className="text-accent">Зарегистрироваться</Link></>
        )}
      </p>
      {isRegister && (
        <p className="mt-4 text-center text-xs text-mist/50">
          Нажимая кнопку, вы принимаете <Link href="/legal" className="underline">условия оферты</Link>.
        </p>
      )}
    </form>
  );
}
