import { Suspense } from "react";
import Cabinet from "@/components/site/Cabinet";
import SiteShell from "@/components/site/SiteShell";

export const metadata = { title: "Личный кабинет" };

export default function CabinetPage() {
  return (
    <SiteShell>
      <main id="main">
        <Suspense fallback={<div className="loading-state">Загружаем кабинет…</div>}>
          <Cabinet />
        </Suspense>
      </main>
    </SiteShell>
  );
}
