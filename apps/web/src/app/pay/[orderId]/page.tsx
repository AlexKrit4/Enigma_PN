import { Suspense } from "react";
import SiteShell from "@/components/site/SiteShell";
import PaymentStatus from "@/components/site/PaymentStatus";

export const metadata = { title: "Оплата" };

export default async function PayPage({ params }: { params: Promise<{ orderId: string }> }) {
  const { orderId } = await params;
  return (
    <SiteShell>
      <main id="main" className="payment-layout">
        <Suspense fallback={<div className="loading-state">Загружаем заказ…</div>}>
          <PaymentStatus orderId={orderId} />
        </Suspense>
      </main>
    </SiteShell>
  );
}
