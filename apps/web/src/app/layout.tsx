import type { Metadata } from "next";
import "./globals.css";

const brand = process.env.NEXT_PUBLIC_BRAND_NAME || "Enigma_PN";

export const metadata: Metadata = {
  title: `${brand} — VPN для Happ`,
  description: "Подписки VPN с быстрым подключением в Happ. Telegram-бот и личный кабинет.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
