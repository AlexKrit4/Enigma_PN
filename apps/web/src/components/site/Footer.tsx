import Link from "next/link";

const BRAND = process.env.NEXT_PUBLIC_BRAND_NAME || "Enigma_PN";
const SUPPORT = process.env.NEXT_PUBLIC_SUPPORT_TELEGRAM || "alexkr1t";

export default function Footer() {
  return (
    <footer className="border-t border-white/10">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-5 py-10 text-sm text-mist/60 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="font-display text-base text-mist">{BRAND}</div>
          <div className="mt-1">© {new Date().getFullYear()}. Все права защищены.</div>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-2">
          <Link href="/setup" className="hover:text-mist">Как подключить</Link>
          <Link href="/legal" className="hover:text-mist">Оферта и конфиденциальность</Link>
          <a href={`https://t.me/${SUPPORT.replace(/^@/, "")}`} target="_blank" rel="noreferrer" className="hover:text-mist">
            Поддержка в Telegram
          </a>
        </div>
      </div>
    </footer>
  );
}
