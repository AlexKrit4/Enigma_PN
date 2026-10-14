import Link from "next/link";
import SiteShell from "@/components/site/SiteShell";
import SetupGuide from "@/components/site/SetupGuide";

export const metadata = { title: "Как подключить" };

export default function SetupPage() {
  return (
    <SiteShell>
      <main id="main" className="site-container">
        <div className="page-heading">
          <div className="site-eyebrow">ИНСТРУКЦИЯ ПО ПОДКЛЮЧЕНИЮ</div>
          <h1>Пара шагов — и вы в сети.</h1>
          <p>Подключение работает через бесплатное приложение Happ. Выберите своё устройство и следуйте инструкции. Подписка — в <Link href="/cabinet" className="site-link">личном кабинете</Link>.</p>
        </div>
        <div className="guide-grid">
          <SetupGuide />
          <aside className="guide-sidebar">
            <section className="site-panel subscription-panel">
              <h2>Какой сервер выбрать?</h2>
              <div className="server-choice"><strong>01 / Finland</strong><p>Основное подключение. Подходит для большинства сетей.</p></div>
              <div className="server-choice"><strong>02 / Обход</strong><p>Для сетей с белыми списками. Если Finland не подключается — выберите «Обход».</p></div>
            </section>
            <section className="site-panel">
              <h2>Не подключается?</h2>
              <ul className="troubleshoot-list">
                <li>Обновите подписку в Happ: потяните список вниз или нажмите «Обновить».</li>
                <li>Переключитесь между Finland и «Обход».</li>
                <li>Проверьте лимит устройств в кабинете — лишние можно отключить.</li>
                <li>Напишите в поддержку — ссылка внизу страницы. Поможем.</li>
              </ul>
            </section>
          </aside>
        </div>
      </main>
    </SiteShell>
  );
}
