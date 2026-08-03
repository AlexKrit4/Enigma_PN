"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { adminLogin } from "@/lib/adminApi";

export default function AdminLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await adminLogin(username.trim(), password);
      router.replace("/admin");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка входа");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-6 py-12">
      <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-8 shadow-2xl">
        <h1 className="font-serif text-3xl tracking-tight">Enigma_PN</h1>
        <p className="mt-2 text-sm text-white/60">Админ-панель</p>
        <form onSubmit={onSubmit} className="mt-8 space-y-4">
          <label className="block text-sm">
            <span className="text-white/70">Логин</span>
            <input
              className="mt-1 w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 outline-none focus:border-sky-400"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </label>
          <label className="block text-sm">
            <span className="text-white/70">Пароль</span>
            <input
              type="password"
              className="mt-1 w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 outline-none focus:border-sky-400"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error ? <p className="text-sm text-rose-300">{error}</p> : null}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-sky-400 px-4 py-2.5 font-semibold text-black transition hover:bg-sky-300 disabled:opacity-60"
          >
            {loading ? "Вход…" : "Войти"}
          </button>
        </form>
      </div>
    </main>
  );
}
