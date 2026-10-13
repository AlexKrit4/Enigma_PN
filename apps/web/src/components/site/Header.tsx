"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { ArrowUpRight, List, X } from "@phosphor-icons/react";
import Brand from "./Brand";
import { getToken } from "@/lib/siteApi";

export default function Header() {
  const [authed, setAuthed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
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
    <header className="site-header">
      <div className="site-container header-inner">
        <Brand />
        <nav className="header-nav" aria-label="Основная навигация">
          <Link href="/#price">Тариф</Link>
          <Link href="/setup">Как подключить</Link>
          <Link href="/#questions">Вопросы и ответы</Link>
        </nav>
        <div className="header-actions">
          {!authed && <Link href="/login" className="header-login">Войти</Link>}
          <Link href={authed ? "/cabinet" : "/register"} className="site-btn site-btn--dark site-btn--small">
            <span className="header-cta-label">{authed ? "Личный кабинет" : "Попробовать бесплатно"}</span>
            <span className="header-cta-short">{authed ? "Кабинет" : "Начать"}</span>
            <ArrowUpRight size={15} aria-hidden />
          </Link>
          <Dialog.Root open={menuOpen} onOpenChange={setMenuOpen}>
            <Dialog.Trigger className="mobile-trigger" aria-label="Открыть меню"><List size={24} /></Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="site-menu-overlay" />
              <Dialog.Content className="website site-menu" aria-describedby={undefined}>
                <div className="menu-title">
                  <Dialog.Title>Меню</Dialog.Title>
                  <Dialog.Close className="icon-button" aria-label="Закрыть меню"><X size={24} /></Dialog.Close>
                </div>
                <nav className="menu-links" aria-label="Мобильная навигация">
                  <Link href="/" onClick={() => setMenuOpen(false)}>Главная</Link>
                  <Link href="/#price" onClick={() => setMenuOpen(false)}>Тариф</Link>
                  <Link href="/setup" onClick={() => setMenuOpen(false)}>Как подключить</Link>
                  <Link href="/#questions" onClick={() => setMenuOpen(false)}>Вопросы и ответы</Link>
                  <Link href={authed ? "/cabinet" : "/login"} onClick={() => setMenuOpen(false)}>{authed ? "Личный кабинет" : "Войти"}</Link>
                </nav>
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>
        </div>
      </div>
    </header>
  );
}
