import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Enigma_PN Admin",
  robots: { index: false, follow: false },
};

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#0f1419] text-[#e8eef5] antialiased">
      {children}
    </div>
  );
}
