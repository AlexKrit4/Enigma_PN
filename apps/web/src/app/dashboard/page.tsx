const BRAND = process.env.NEXT_PUBLIC_BRAND_NAME || "Enigma_PN";
const BOT = process.env.NEXT_PUBLIC_BOT_USERNAME || "enigmapnbot";

export default function DashboardPage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col justify-center px-6 py-16 text-mist">
      <h1 className="font-display text-4xl">{BRAND}</h1>
      <p className="mt-4 text-mist/70">
        Личный кабинет на сайте в MVP упрощён: управление подпиской — в Telegram-боте.
      </p>
      <a
        href={`https://t.me/${BOT}`}
        className="mt-8 inline-flex w-fit rounded-full bg-accent px-5 py-3 font-semibold text-ink"
      >
        Открыть @{BOT}
      </a>
      <a href="/" className="mt-6 text-sm text-mist/60 hover:text-mist">
        ← На главную
      </a>
    </main>
  );
}
