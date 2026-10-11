"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getToken } from "@/lib/siteApi";

const BRAND = process.env.NEXT_PUBLIC_BRAND_NAME || "Enigma_PN";

export default function Header() {
  const [authed, setAuthed] = useState(false);
  useEffect(() => {
    const sync = () => setAuthed(Boolean(getToken()));
    sync();
    window.addEventListener("enigma-auth", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("enigma-auth", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-ink/70 backdrop-blur">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-5">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/15 text-accent">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5l-8-3Z" /><path d="m9 12 2 2 4-4" /></svg>
          </span>
          <span className="font-display text-lg font-semibold tracking-tight">{BRAND}</span>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          <Link href="/#price" className="nav-link hidden sm:inline-flex">Цена</Link>
          <Link href="/setup" className="nav-link hidden sm:inline-flex">Как подключить</Link>
          {authed ? (
            <Link href="/cabinet" className="btn-primary ml-2 !px-4 !py-2 !text-sm">Личный кабинет</Link>
          ) : (
            <>
              <Link href="/login" className="nav-link">Войти</Link>
              <Link href="/register" className="btn-primary ml-2 !px-4 !py-2 !text-sm">Попробовать</Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
