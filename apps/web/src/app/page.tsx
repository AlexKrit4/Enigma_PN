import Link from "next/link";
import Footer from "@/components/site/Footer";
import Header from "@/components/site/Header";
import PriceCalculator from "@/components/site/PriceCalculator";

const BRAND = process.env.NEXT_PUBLIC_BRAND_NAME || "Enigma_PN";

const steps = [
  { n: "01", title: "Зарегистрируйтесь", text: "Почта и пароль, затем подтверждение кодом из письма. Сразу получите 3 дня доступа бесплатно — проверьте, что всё работает именно у вас." },
  { n: "02", title: "Установите Happ", text: "Бесплатное приложение для Android, iPhone, Windows, macOS и телевизоров. Ссылки — в личном кабинете." },
  { n: "03", title: "Нажмите «Добавить в Happ»", text: "Подписка добавится сама. Выбираете сервер, включаете — готово. Никаких ручных настроек." },
];

const faq = [
  { q: "Что такое «белые списки» и почему другие VPN не работают?", a: "На некоторых сетях провайдер пропускает трафик только к разрешённым российским сайтам. Обычные VPN-серверы за рубежом туда не входят, поэтому соединение просто не устанавливается. Наш вход расположен в России и выглядит для провайдера как обычный российский сайт, поэтому проходит." },
  { q: "Будет ли работать на мобильном интернете и домашнем Wi-Fi?", a: "Да. В подписке два подключения: обычное через Финляндию и «Обход» для сетей с ограничениями. Если одно не подходит для вашей сети — переключитесь на второе прямо в Happ." },
  { q: "Как считаются устройства?", a: "Устройство — это телефон, компьютер или телевизор, на котором добавлена подписка. В тариф входит 5 устройств, каждое следующее — 20 ₽ в месяц. Список устройств и кнопка «отключить» есть в кабинете." },
  { q: "Есть ограничение трафика или скорости?", a: "Нет. Трафик безлимитный, скорость ограничена только вашим интернетом." },
  { q: "Как оплатить?", a: "Через ЮMoney: банковской картой или кошельком. Подписка активируется автоматически в течение минуты после оплаты." },
];

export default function HomePage() {
  return (
    <>
      <Header />
      <main>
        <section className="relative overflow-hidden">
          <div className="pointer-events-none absolute inset-0 -z-10 bg-hero" />
          <div className="mx-auto grid w-full max-w-6xl gap-12 px-5 pb-20 pt-16 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:pt-24">
            <div className="animate-rise">
              <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-xs text-mist/80">
                <span className="h-1.5 w-1.5 rounded-full bg-accent" /> Работает там, где остальные молчат
              </div>
              <h1 className="font-display mt-6 text-4xl font-semibold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
                VPN, который проходит через белые списки
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-mist/75">
                {BRAND} подключается даже в сетях, где провайдер разрешает только российские сайты. Один тариф, безлимитный трафик, пять устройств. Настройка — одно нажатие в приложении Happ.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link href="/register" className="btn-primary">Попробовать 3 дня бесплатно</Link>
                <Link href="#price" className="btn-ghost">Смотреть цену</Link>
              </div>
              <dl className="mt-12 grid max-w-lg grid-cols-3 gap-6 border-t border-white/10 pt-8">
                <div><dt className="text-xs text-mist/55">Трафик</dt><dd className="font-display mt-1 text-2xl">∞</dd></div>
                <div><dt className="text-xs text-mist/55">Устройств</dt><dd className="font-display mt-1 text-2xl">5+</dd></div>
                <div><dt className="text-xs text-mist/55">Цена</dt><dd className="font-display mt-1 text-2xl">от 167 ₽</dd></div>
              </dl>
            </div>
            <div id="price" className="animate-rise scroll-mt-24 [animation-delay:150ms]">
              <PriceCalculator />
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-6xl px-5 py-20">
          <div className="max-w-2xl">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Как это работает</div>
            <h2 className="font-display mt-3 text-3xl font-semibold sm:text-4xl">Три шага до подключения</h2>
          </div>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {steps.map((s) => (
              <div key={s.n} className="card p-6">
                <div className="font-display text-sm text-copper">{s.n}</div>
                <h3 className="mt-3 text-lg font-semibold">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-mist/70">{s.text}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="border-y border-white/10 bg-white/[0.02]">
          <div className="mx-auto grid w-full max-w-6xl gap-10 px-5 py-20 lg:grid-cols-2">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Почему проходит</div>
              <h2 className="font-display mt-3 text-3xl font-semibold sm:text-4xl">Для сети это обычный российский сайт</h2>
              <p className="mt-5 leading-relaxed text-mist/75">
                Вход в сеть расположен в российском дата-центре и защищён так же, как любой сайт с сертификатом. Провайдер видит привычное соединение и пропускает его. Дальше трафик идёт на наши серверы за рубежом — вы получаете открытый интернет.
              </p>
              <ul className="mt-6 space-y-3 text-sm text-mist/80">
                {["Два подключения в одной подписке: обычное и «Обход»", "Протокол без заметных признаков VPN", "Подписка обновляется автоматически — новые серверы появятся сами"].map((t) => (
                  <li key={t} className="flex gap-3"><span className="mt-1 h-4 w-4 shrink-0 rounded-full bg-accent/20 text-center text-[10px] leading-4 text-accent">✓</span>{t}</li>
                ))}
              </ul>
            </div>
            <div className="card p-6 sm:p-8">
              <div className="text-sm font-semibold">Поддерживаемые устройства</div>
              <div className="mt-5 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
                {["Android", "iPhone / iPad", "Windows", "macOS", "Android TV", "Apple TV"].map((d) => (
                  <div key={d} className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-mist/85">{d}</div>
                ))}
              </div>
              <p className="mt-5 text-sm text-mist/60">Подключение через бесплатное приложение Happ. Подробная инструкция — <Link href="/setup" className="text-accent">здесь</Link>.</p>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-3xl px-5 py-20">
          <h2 className="font-display text-3xl font-semibold sm:text-4xl">Вопросы и ответы</h2>
          <div className="mt-8 divide-y divide-white/10">
            {faq.map((f) => (
              <details key={f.q} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-base font-medium">
                  {f.q}
                  <span className="text-mist/50 transition group-open:rotate-45">+</span>
                </summary>
                <p className="mt-3 text-sm leading-relaxed text-mist/70">{f.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="mx-auto w-full max-w-6xl px-5 pb-24">
          <div className="card flex flex-col items-start justify-between gap-6 p-8 sm:flex-row sm:items-center sm:p-10">
            <div>
              <h2 className="font-display text-2xl font-semibold sm:text-3xl">Попробуйте бесплатно — 3 дня</h2>
              <p className="mt-2 text-mist/70">Три дня доступа после регистрации, карта не нужна.</p>
            </div>
            <Link href="/register" className="btn-primary shrink-0">Начать</Link>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
