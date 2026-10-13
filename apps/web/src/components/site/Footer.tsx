import Link from "next/link";
import { ArrowUpRight } from "@phosphor-icons/react/dist/ssr";
import Brand from "./Brand";

const BRAND = process.env.NEXT_PUBLIC_BRAND_NAME || "Enigma_PN";
const SUPPORT = process.env.NEXT_PUBLIC_SUPPORT_TELEGRAM || "alexkr1t";

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-container">
        <div className="footer-main">
          <div><Brand /><p>Свободнее в сети. Проще в жизни.</p></div>
          <nav className="footer-links" aria-label="Ссылки внизу страницы">
            <Link href="/setup">Как подключить</Link>
            <Link href="/legal">Оферта и конфиденциальность</Link>
            <a href={`https://t.me/${SUPPORT.replace(/^@/, "")}`} target="_blank" rel="noreferrer">
              Поддержка в Telegram <ArrowUpRight size={14} aria-hidden />
            </a>
          </nav>
        </div>
        <div className="footer-bottom">
          <span>{`© ${new Date().getFullYear()} ${BRAND}`}</span><span>ВАШ МАРШРУТ. ВАШ ИНТЕРНЕТ.</span>
        </div>
      </div>
    </footer>
  );
}
