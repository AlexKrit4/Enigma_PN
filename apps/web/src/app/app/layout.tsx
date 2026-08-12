import type { Metadata } from "next";
import Script from "next/script";

export const metadata: Metadata = {
  title: "Enigma_PN — кабинет",
  description: "Telegram Mini App: подписка, тарифы и казино дней",
};

export default function MiniAppLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Script src="https://telegram.org/js/telegram-web-app.js" strategy="beforeInteractive" />
      <div className="miniapp-root min-h-screen">{children}</div>
    </>
  );
}
