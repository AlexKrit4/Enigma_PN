import Link from "next/link";
import Footer from "@/components/site/Footer";
import Header from "@/components/site/Header";

export const metadata = { title: "Как подключить" };

const platforms = [
  { name: "Android", store: "Google Play", url: "https://play.google.com/store/apps/details?id=com.happproxy", steps: ["Установите Happ из Google Play.", "В личном кабинете нажмите «Добавить в Happ» — приложение откроется и подписка появится в списке.", "Выберите сервер и нажмите кнопку подключения. При первом запуске разрешите создание VPN-соединения."] },
  { name: "iPhone и iPad", store: "App Store", url: "https://apps.apple.com/app/happ-proxy-utility/id6504287215", steps: ["Установите Happ из App Store.", "Нажмите «Добавить в Happ» в личном кабинете, подтвердите открытие приложения.", "Выберите сервер, нажмите подключение и разрешите добавить VPN-конфигурацию."] },
  { name: "Windows", store: "сайт Happ", url: "https://www.happ.su/main/ru", steps: ["Скачайте Happ для Windows с официального сайта и установите.", "Скопируйте ссылку подписки из кабинета и вставьте её в Happ: «+» → «Добавить подписку».", "Выберите сервер и подключитесь."] },
  { name: "macOS", store: "App Store", url: "https://apps.apple.com/app/happ-proxy-utility/id6504287215", steps: ["Установите Happ из App Store.", "Нажмите «Добавить в Happ» в кабинете или вставьте ссылку подписки вручную.", "Выберите сервер и подключитесь."] },
  { name: "Android TV", store: "Google Play", url: "https://play.google.com/store/apps/details?id=com.happproxy", steps: ["Установите Happ из Google Play на телевизоре.", "В Happ выберите добавление подписки по ссылке и введите ссылку из кабинета (или откройте кабинет на телефоне и перепишите).", "Выберите сервер и подключитесь."] },
];

export default function SetupPage() {
  return (
    <>
      <Header />
      <main className="mx-auto w-full max-w-4xl px-5 py-14">
        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Инструкция</div>
        <h1 className="font-display mt-3 text-4xl font-semibold">Как подключить</h1>
        <p className="mt-4 max-w-2xl text-mist/70">
          Подключение идёт через бесплатное приложение Happ. Подписка добавляется одним нажатием из <Link href="/cabinet" className="text-accent">личного кабинета</Link>. Если кнопка не сработала, всегда можно вставить ссылку подписки вручную.
        </p>

        <div className="card mt-10 p-6 sm:p-8">
          <h2 className="font-display text-xl font-semibold">Какой сервер выбрать</h2>
          <ul className="mt-4 space-y-3 text-sm text-mist/80">
            <li><span className="font-semibold text-mist">Finland</span> — основное подключение. Подходит для большинства сетей.</li>
            <li><span className="font-semibold text-mist">🇷🇺 Обход</span> — для сетей с ограничениями («белые списки»), где обычное подключение не устанавливается. Если Finland не подключается — выберите «Обход».</li>
          </ul>
        </div>

        <div className="mt-8 space-y-5">
          {platforms.map((p) => (
            <details key={p.name} className="card group p-6" open={p.name === "Android"}>
              <summary className="flex cursor-pointer list-none items-center justify-between text-lg font-semibold">
                {p.name}
                <span className="text-mist/50 transition group-open:rotate-45">+</span>
              </summary>
              <ol className="mt-4 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-mist/75">
                {p.steps.map((s) => <li key={s}>{s}</li>)}
              </ol>
              <a href={p.url} target="_blank" rel="noreferrer" className="btn-ghost mt-5 !px-4 !py-2 !text-sm">Скачать Happ — {p.store}</a>
            </details>
          ))}
        </div>

        <div className="card mt-8 p-6 sm:p-8">
          <h2 className="font-display text-xl font-semibold">Не подключается?</h2>
          <ul className="mt-4 space-y-2 text-sm text-mist/75">
            <li>Обновите подписку в Happ (потяните список вниз или нажмите «Обновить»).</li>
            <li>Переключитесь между Finland и «Обход».</li>
            <li>Проверьте, не исчерпан ли лимит устройств в кабинете — лишние можно отключить.</li>
            <li>Напишите в поддержку — ссылка внизу страницы. Поможем.</li>
          </ul>
        </div>
      </main>
      <Footer />
    </>
  );
}
