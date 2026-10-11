import type { Metadata } from "next";
import "./globals.css";

const brand = process.env.NEXT_PUBLIC_BRAND_NAME || "Enigma_PN";

export const metadata: Metadata = {
  title: { default: `${brand} — VPN, который проходит через белые списки`, template: `%s — ${brand}` },
  description:
    "VPN для сетей с белыми списками: подключается там, где другие не работают. Безлимитный трафик, 5 устройств, настройка в одно нажатие через Happ.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
