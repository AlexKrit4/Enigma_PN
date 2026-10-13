export default function ConnectionArtwork({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`connection-art${compact ? " connection-art--compact" : ""}`} role="img" aria-label="Схема: ваше устройство подключается к интернету через VPN">
      <div className="art-caption"><span>СВОЙ МАРШРУТ В СЕТЬ</span><span>01 — VPN</span></div>
      <svg className="art-globe" viewBox="0 0 480 420" fill="none" aria-hidden="true">
        <defs>
          <clipPath id={compact ? "globe-compact" : "globe-hero"}><circle cx="240" cy="200" r="155" /></clipPath>
        </defs>
        <g stroke="currentColor" strokeWidth="1.2" clipPath={`url(#${compact ? "globe-compact" : "globe-hero"})`}>
          <circle cx="240" cy="200" r="155" fill="#f9ead1" />
          <ellipse cx="240" cy="200" rx="103" ry="155" />
          <ellipse cx="240" cy="200" rx="47" ry="155" />
          <ellipse cx="240" cy="200" rx="155" ry="105" />
          <ellipse cx="240" cy="200" rx="155" ry="46" />
          <path d="M85 200h310M240 45v310" />
          <path d="m160 87 24 27-6 23 17 15 27-14 12 29-23 20-6 43 28 17-5 36-29 17-20-27-8-33-26-22-17-42 15-23-16-33M285 71l-21 43 15 19 23-6 12 29 34 4 18 29-24 23-11 41-28 16-4-24-30-13-11-36 13-24-20-19-1-22-29-12 10-28" fill="#e6dfcb" stroke="none" />
          <path d="M104 275c83-140 194-154 288-92" stroke="#f35734" strokeWidth="9" strokeLinecap="round" />
          <path d="M104 275c83-140 194-154 288-92" stroke="#252622" strokeWidth="1.5" strokeDasharray="3 10" />
        </g>
        <circle cx="240" cy="200" r="155" stroke="currentColor" strokeWidth="1.8" />
        <circle cx="120" cy="250" r="11" fill="#252622" stroke="#f9ead1" strokeWidth="4" />
        <circle cx="344" cy="164" r="11" fill="#252622" stroke="#f9ead1" strokeWidth="4" />
        <path d="M120 264v87H49M344 150V54h73" stroke="currentColor" strokeWidth="1.5" />
        <rect x="20" y="327" width="137" height="48" rx="3" fill="#252622" />
        <text x="88" y="357" textAnchor="middle" fill="#f9f5ec" fontSize="12" fontFamily="IBM Plex Mono, monospace">ВАШЕ УСТРОЙСТВО</text>
        <rect x="324" y="30" width="137" height="48" rx="3" fill="#252622" />
        <text x="392" y="60" textAnchor="middle" fill="#f9f5ec" fontSize="12" fontFamily="IBM Plex Mono, monospace">ИНТЕРНЕТ</text>
        <path d="m406 329 12-12 12 12-12 12z" fill="#252622" />
        <path d="M35 60h22M46 49v22" stroke="currentColor" strokeWidth="1.5" />
      </svg>
      <div className="art-bottom"><span className="art-stamp">E / PN</span><p>Меньше ограничений.<br />Больше возможностей.</p><span className="art-arrow" aria-hidden="true">↗</span></div>
    </div>
  );
}
