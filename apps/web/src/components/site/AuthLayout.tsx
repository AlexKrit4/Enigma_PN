import SiteShell from "./SiteShell";
import ConnectionArtwork from "./ConnectionArtwork";

export default function AuthLayout({ children, variant }: { children: React.ReactNode; variant: "register" | "login" | "verify" }) {
  return (
    <SiteShell>
      <main id="main" className="auth-layout">
        <aside className="auth-aside">
          <div>
            <div className="site-eyebrow">{variant === "login" ? "С ВОЗВРАЩЕНИЕМ" : "НАЧНИТЕ БЕЗ ОПЛАТЫ"}</div>
            <h2>{variant === "login" ? <>Ваш интернет.<br />Ваши правила.</> : <>Один день.<br />Все возможности.</>}</h2>
            <ConnectionArtwork compact />
          </div>
        </aside>
        <div className="auth-content">{children}</div>
      </main>
    </SiteShell>
  );
}
