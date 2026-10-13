"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ArrowRight, Eye, EyeSlash } from "@phosphor-icons/react";
import { ApiError, setToken, siteApi } from "@/lib/siteApi";

export default function AuthForm({ mode }: { mode: "register" | "login" }) {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const months = params.get("months");
  const devices = params.get("devices");
  const next = months ? `/cabinet?months=${months}&devices=${devices ?? ""}&buy=1` : "/cabinet";
  const verifyNext = (mail: string) =>
    `/verify?email=${encodeURIComponent(mail)}${months ? `&months=${months}&devices=${devices ?? ""}` : ""}`;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "register" && password.length < 8) {
      setError("Пароль должен быть не короче 8 символов.");
      return;
    }
    setBusy(true);
    const mail = email.trim();
    try {
      if (mode === "register") {
        await siteApi.register(mail, password);
        router.replace(verifyNext(mail));
      } else {
        const session = await siteApi.login(mail, password);
        setToken(session.access_token);
        router.replace(next);
      }
    } catch (err) {
      if (mode === "login" && err instanceof ApiError && err.status === 403) {
        router.replace(verifyNext(mail));
        return;
      }
      setError(err instanceof Error ? err.message : "Что-то пошло не так. Попробуйте ещё раз.");
    } finally {
      setBusy(false);
    }
  }

  const isRegister = mode === "register";
  return (
    <form onSubmit={onSubmit} className="auth-form">
      {isRegister && <div className="auth-step" aria-label="Шаг 1 из 2: регистрация"><span className="is-current" /><span /></div>}
      <h1>{isRegister ? "Создать аккаунт" : "Войти в кабинет"}</h1>
      <p className="auth-description">
        {isRegister ? "После подтверждения почты кодом вы получите 3 дня доступа бесплатно." : "Введите почту и пароль от личного кабинета."}
      </p>
      <label className="site-label">
        Электронная почта
        <input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className="site-input" placeholder="you@example.com" />
      </label>
      <label className="site-label" htmlFor="password">Пароль</label>
      <div className="password-field">
        <input id="password" type={showPassword ? "text" : "password"} required minLength={isRegister ? 8 : 1} autoComplete={isRegister ? "new-password" : "current-password"} value={password} onChange={(e) => setPassword(e.target.value)} className="site-input" placeholder={isRegister ? "Не менее 8 символов" : "Ваш пароль"} />
        <button type="button" onClick={() => setShowPassword((v) => !v)} className="icon-button password-toggle" aria-label={showPassword ? "Скрыть пароль" : "Показать пароль"} aria-pressed={showPassword}>{showPassword ? <EyeSlash size={20} aria-hidden /> : <Eye size={20} aria-hidden />}</button>
      </div>
      {error && <p className="site-alert" role="alert">{error}</p>}
      <button type="submit" disabled={busy} className="site-btn site-btn--dark site-btn--full form-submit">
        {busy ? "Секунду…" : isRegister ? "Зарегистрироваться" : "Войти"}
        <ArrowRight size={18} aria-hidden />
      </button>
      <p className="auth-switch">
        {isRegister ? (
          <>Уже есть аккаунт? <Link href={`/login${months ? `?months=${months}&devices=${devices ?? ""}` : ""}`} className="site-link">Войти</Link></>
        ) : (
          <>Нет аккаунта? <Link href="/register" className="site-link">Зарегистрироваться</Link></>
        )}
      </p>
      {isRegister && (
        <p className="auth-legal">
          Нажимая кнопку, вы принимаете <Link href="/legal" className="site-link">условия оферты</Link>.
        </p>
      )}
    </form>
  );
}
