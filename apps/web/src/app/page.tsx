import Link from "next/link";
import { ArrowRight, ArrowUpRight, Check, DeviceMobile, GlobeHemisphereWest, ShieldCheck, LockSimple, Info, AndroidLogo, AppleLogo, WindowsLogo, Television, EnvelopeSimple, DownloadSimple, PlugsConnected } from "@phosphor-icons/react/dist/ssr";
import SiteShell from "@/components/site/SiteShell";
import ConnectionArtwork from "@/components/site/ConnectionArtwork";
import PriceCalculator from "@/components/site/PriceCalculator";
import FAQ from "@/components/site/FAQ";

const SUPPORT = process.env.NEXT_PUBLIC_SUPPORT_TELEGRAM || "alexkr1t";

export default function HomePage() {
  return (
    <SiteShell>
      <main id="main">
        <section className="site-container hero">
          <div>
            <div className="site-eyebrow">VPN ДЛЯ ВАШЕГО ПОВСЕДНЕВНОГО ИНТЕРНЕТА</div>
            <h1>Интернет.<br />Без закрытых <span>дверей.</span></h1>
            <p className="hero-description">Ваши сайты, приложения и видео — даже в сетях с белыми списками. Один VPN для телефона, ноутбука и всех ваших устройств.</p>
            <div className="hero-actions">
              <Link href="/register" className="site-btn site-btn--dark">3 дня бесплатно <ArrowUpRight size={18} aria-hidden /></Link>
              <Link href="#price" className="site-link">Выбрать тариф</Link>
            </div>
            <div className="hero-note"><Check size={14} aria-hidden /> Без карты. Просто подтвердите почту.</div>
          </div>
          <ConnectionArtwork />
        </section>
        <div className="site-container facts">
          <div className="fact"><strong>05</strong><span>устройств<br />в одной подписке</span></div>
          <div className="fact"><strong>∞</strong><span>трафик<br />без ограничений</span></div>
          <div className="fact"><strong>200 ₽</strong><span>стоимость<br />за один месяц</span></div>
          <div className="fact"><strong>03</strong><span>дня бесплатно<br />для знакомства</span></div>
        </div>
        <section className="site-container site-section">
          <div className="section-top">
            <div><div className="site-eyebrow">НЕ ОДИН ПУТЬ, А ДВА</div><h2>В обычной сети.<br />И там, где сложнее.</h2></div>
            <p>В одной подписке — основное подключение и отдельный маршрут для белых списков. Переключайтесь между ними прямо в Happ.</p>
          </div>
          <div className="route-grid">
            <article className="route">
              <div className="route-title"><h3>Обычное подключение</h3><span className="route-label">Finland</span></div>
              <div className="route-path" aria-hidden="true"><div className="route-node"><DeviceMobile size={24} /></div><div className="route-line" /><div className="route-node route-node--accent"><ShieldCheck size={24} /></div><div className="route-line" /><div className="route-node"><GlobeHemisphereWest size={26} /></div></div>
              <p>Для Wi-Fi и мобильного интернета без белых списков. Выберите сервер Finland и подключитесь.</p>
            </article>
            <article className="route route--bypass">
              <div className="route-title"><h3>Обход ограничений</h3><span className="route-label">Обход</span></div>
              <div className="route-path" aria-hidden="true"><div className="route-node"><DeviceMobile size={24} /></div><div className="route-line" /><div className="route-node route-node--accent"><PlugsConnected size={24} /></div><div className="route-line" /><div className="route-node"><GlobeHemisphereWest size={26} /></div></div>
              <p>Когда обычное соединение не устанавливается, переключитесь на «Обход». Он рассчитан на сети с белыми списками.</p>
            </article>
          </div>
          <p className="route-caveat"><Info size={16} aria-hidden /> Ограничения у провайдеров отличаются. Проверьте свою сеть в бесплатном пробном периоде.</p>
        </section>
        <section id="price" className="site-section pricing-section">
          <div className="site-container pricing-grid">
            <div className="pricing-intro">
              <div className="site-eyebrow">ПОНЯТНАЯ ЦЕНА</div>
              <h2>Платите за время.<br />Не за гигабайты.</h2>
              <p>Один тариф, всё включено. Выберите срок и количество устройств — итоговая цена сразу перед вами.</p>
              <ul className="included-list">
                <li><Check size={18} aria-hidden /> Обход белых списков</li>
                <li><Check size={18} aria-hidden /> 5 устройств и безлимитный трафик</li>
                <li><Check size={18} aria-hidden /> Все доступные серверы</li>
                <li><Check size={18} aria-hidden /> Дополнительное устройство — 20 ₽ / месяц</li>
              </ul>
              <div className="trial-note"><LockSimple size={22} aria-hidden /><div><strong>Сначала попробуйте. Потом решайте.</strong><p>3 дня бесплатно после подтверждения почты. Без привязки карты.</p></div></div>
            </div>
            <PriceCalculator />
          </div>
        </section>
        <section className="site-container site-section">
          <div className="section-top">
            <div><div className="site-eyebrow">ОТ АККАУНТА ДО ПОДКЛЮЧЕНИЯ</div><h2>Меньше настройки.<br />Больше интернета.</h2></div>
            <p>Никаких конфигурационных файлов и сложных параметров. Нужны почта, бесплатное приложение Happ и пара нажатий.</p>
          </div>
          <div className="steps-grid">
            <article><div className="step-number"><span>01 / АККАУНТ</span><EnvelopeSimple size={24} aria-hidden /></div><h3>Подтвердите почту</h3><p>Зарегистрируйтесь и введите код из письма. Пробный период начнётся сразу.</p></article>
            <article><div className="step-number"><span>02 / ПРИЛОЖЕНИЕ</span><DownloadSimple size={24} aria-hidden /></div><h3>Установите Happ</h3><p>Бесплатное приложение для вашего устройства. Ссылки есть в <Link href="/setup" className="site-link">инструкции</Link>.</p></article>
            <article><div className="step-number"><span>03 / ПОДКЛЮЧЕНИЕ</span><GlobeHemisphereWest size={24} aria-hidden /></div><h3>Добавьте подписку</h3><p>Нажмите «Добавить в Happ» в кабинете, выберите сервер и подключитесь.</p></article>
          </div>
          <div className="platform-strip">
            <span>На устройствах, которыми вы пользуетесь</span>
            <div><AndroidLogo size={20} aria-hidden />Android</div><div><AppleLogo size={20} aria-hidden />iOS / macOS</div><div><WindowsLogo size={20} aria-hidden />Windows</div><div><Television size={20} aria-hidden />Android TV</div>
          </div>
        </section>
        <section id="questions" className="site-section faq-section">
          <div className="site-container faq-grid">
            <div className="faq-intro"><div className="site-eyebrow">БЕЗ МЕЛКОГО ШРИФТА</div><h2>Хорошие вопросы.<br />Прямые ответы.</h2><p>Не нашли свой ответ?<br /><a className="site-link" href={`https://t.me/${SUPPORT.replace(/^@/, "")}`} target="_blank" rel="noreferrer">Напишите нам в Telegram <ArrowUpRight size={14} style={{ display: "inline" }} aria-hidden /></a></p></div>
            <FAQ />
          </div>
        </section>
        <section className="site-container final-cta">
          <div><h2>Откройте свой интернет.</h2><p>3 дня, чтобы проверить всё на своих устройствах. Бесплатно.</p></div>
          <Link href="/register" className="site-btn site-btn--dark">Начать с 3 дней бесплатно <ArrowRight size={18} aria-hidden /></Link>
        </section>
      </main>
    </SiteShell>
  );
}
