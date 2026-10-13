import Link from "next/link";

const BRAND = process.env.NEXT_PUBLIC_BRAND_NAME || "Enigma_PN";

export default function Brand() {
  return (
    <Link href="/" className="site-brand" aria-label={`${BRAND} — главная`}>
      <svg viewBox="0 0 32 32" width="32" height="32" aria-hidden="true">
        <path fill="currentColor" d="M2 3h28v6H8v4h18v6H8v4h22v6H2z" />
        <path fill="var(--site-orange)" d="M26 13h4v6h-4z" />
      </svg>
      <span>{BRAND.replace("_", " / ")}</span>
    </Link>
  );
}
