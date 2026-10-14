import { Suspense } from "react";
import AdminPanel from "@/components/site/AdminPanel";
import SiteShell from "@/components/site/SiteShell";

export const metadata = { title: "Панель", robots: { index: false, follow: false } };

export default function PanelPage() {
  return (
    <SiteShell>
      <main id="main">
        <Suspense fallback={<div className="loading-state">Загружаем панель…</div>}>
          <AdminPanel />
        </Suspense>
      </main>
    </SiteShell>
  );
}
