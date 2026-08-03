const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const BRAND = process.env.NEXT_PUBLIC_BRAND_NAME || "Enigma_PN";
const BOT = process.env.NEXT_PUBLIC_BOT_USERNAME || "enigmapnbot";
const DOMAIN = process.env.NEXT_PUBLIC_DOMAIN || "bigwinzone.ru";

type Plan = {
  id: string;
  slug: string;
  name: string;
  group_name: string;
  duration_days: number;
  traffic_gb: number | null;
  device_limit: number;
  price_rub: string;
};

async function getPlans(): Promise<Plan[]> {
  try {
    const res = await fetch(`${API_URL}/api/v1/plans`, { next: { revalidate: 60 } });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const plans = await getPlans();
  const groups = Array.from(new Set(plans.map((p) => p.group_name)));

  return (
    <main className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 grid-noise opacity-40" />
      <div className="pointer-events-none absolute -right-24 top-24 h-80 w-80 animate-glow rounded-full bg-accent/20 blur-3xl" />
      <div className="pointer-events-none absolute left-10 top-64 h-56 w-56 animate-drift rounded-full bg-copper/10 blur-3xl" />

      <header className="relative z-10 mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6">
        <div className="font-display text-2xl tracking-tight text-mist">{BRAND}</div>
        <nav className="flex items-center gap-4 text-sm text-mist/80">
          <a href="#pricing" className="hover:text-mist">
            Тарифы
          </a>
          <a href="/legal" className="hover:text-mist">
            Оферта
          </a>
          <a
            href={`https://t.me/${BOT}`}
            className="rounded-full bg-accent px-4 py-2 font-semibold text-ink transition hover:bg-accent2"
          >
            Открыть бота
          </a>
        </nav>
      </header>

      <section className="relative z-10 mx-auto flex min-h-[78vh] w-full max-w-6xl flex-col justify-center px-6 pb-20 pt-8">
        <p className="animate-rise mb-4 text-sm uppercase tracking-[0.22em] text-accent">VPN · Happ · {DOMAIN}</p>
        <h1 className="animate-rise font-display max-w-3xl text-5xl leading-[1.05] text-mist md:text-7xl" style={{ animationDelay: "0.08s" }}>
          {BRAND}
        </h1>
        <p className="animate-rise mt-6 max-w-xl text-lg text-mist/75 md:text-xl" style={{ animationDelay: "0.16s" }}>
          Стабильный доступ через Happ. Купите подписку в Telegram — получите ссылку и подключитесь за минуту.
        </p>
        <div className="animate-rise mt-10 flex flex-wrap gap-4" style={{ animationDelay: "0.24s" }}>
          <a
            href={`https://t.me/${BOT}`}
            className="rounded-full bg-mist px-6 py-3 font-semibold text-ink transition hover:bg-white"
          >
            Начать в Telegram
          </a>
          <a
            href="#pricing"
            className="rounded-full border border-mist/25 px-6 py-3 font-semibold text-mist transition hover:border-mist/60"
          >
            Смотреть тарифы
          </a>
        </div>
      </section>

      <section id="pricing" className="relative z-10 mx-auto w-full max-w-6xl px-6 pb-24">
        <h2 className="font-display text-3xl text-mist md:text-4xl">Тарифы</h2>
        <p className="mt-3 max-w-2xl text-mist/70">
          Ограниченный трафик, вечный трафик или свой тариф. Оплата в Telegram-боте через ЮMoney.
        </p>

        {groups.length === 0 ? (
          <p className="mt-10 text-mist/60">Тарифы появятся после запуска API.</p>
        ) : (
          groups.map((group) => (
            <div key={group} className="mt-12">
              <h3 className="mb-6 text-sm uppercase tracking-[0.18em] text-copper">{group}</h3>
              <div className="grid gap-6 md:grid-cols-3">
                {plans
                  .filter((p) => p.group_name === group)
                  .map((plan) => (
                    <article
                      key={plan.id}
                      className="rounded-2xl border border-mist/10 bg-white/[0.03] p-6 backdrop-blur transition hover:border-accent/40 hover:bg-white/[0.05]"
                    >
                      <div className="font-display text-2xl text-mist">{plan.name}</div>
                      <div className="mt-4 font-display text-4xl text-accent">{plan.price_rub} ₽</div>
                      <ul className="mt-6 space-y-2 text-sm text-mist/75">
                        <li>{plan.duration_days} дней</li>
                        <li>{plan.traffic_gb == null ? "вечный трафик" : `${plan.traffic_gb} ГБ трафика`}</li>
                        <li>до {plan.device_limit} устройств</li>
                        <li>клиент Happ</li>
                      </ul>
                      <a
                        href={`https://t.me/${BOT}`}
                        className="mt-8 inline-flex rounded-full bg-accent/90 px-4 py-2 text-sm font-semibold text-ink hover:bg-accent"
                      >
                        Купить в боте
                      </a>
                    </article>
                  ))}
              </div>
            </div>
          ))
        )}

        <div className="mt-12 rounded-2xl border border-mist/10 bg-white/[0.03] p-6">
          <div className="font-display text-2xl text-mist">Свой тариф</div>
          <p className="mt-3 text-mist/70">
            Соберите сами в боте: 2 ₽ за ГБ, 1 ₽ за день, 25 ₽ за устройство. Вечный трафик в своём тарифе недоступен.
          </p>
          <a
            href={`https://t.me/${BOT}`}
            className="mt-6 inline-flex rounded-full bg-mist px-4 py-2 text-sm font-semibold text-ink hover:bg-white"
          >
            Собрать в боте
          </a>
        </div>
      </section>

      <section className="relative z-10 mx-auto w-full max-w-6xl px-6 pb-24">
        <h2 className="font-display text-3xl text-mist">Как это работает</h2>
        <ol className="mt-8 grid gap-6 md:grid-cols-3">
          {[
            ["1", "Откройте бота", `Напишите @${BOT} и получите пробный день`],
            ["2", "Оплатите тариф", "ЮMoney (СБП / карта), метка платежа в заказе"],
            ["3", "Добавьте в Happ", "Одна ссылка подписки — список серверов"],
          ].map(([n, title, desc]) => (
            <li key={n} className="border-t border-mist/15 pt-5">
              <div className="text-accent">{n}</div>
              <div className="mt-2 font-display text-xl text-mist">{title}</div>
              <p className="mt-2 text-sm text-mist/70">{desc}</p>
            </li>
          ))}
        </ol>
      </section>

      <footer className="relative z-10 border-t border-mist/10 px-6 py-10 text-sm text-mist/55">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-4">
          <span>{BRAND} · {DOMAIN}</span>
          <div className="flex gap-4">
            <a href="/legal">Оферта</a>
            <a href={`https://t.me/${BOT}`}>Telegram</a>
            <a href="https://www.happ.su/main" target="_blank" rel="noreferrer">
              Happ
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}
