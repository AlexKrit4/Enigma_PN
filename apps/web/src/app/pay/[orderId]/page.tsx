import { Suspense } from "react";
import Footer from "@/components/site/Footer";
import Header from "@/components/site/Header";
import PaymentStatus from "@/components/site/PaymentStatus";

export const metadata = { title: "Оплата" };

export default async function PayPage({ params }: { params: Promise<{ orderId: string }> }) {
  const { orderId } = await params;
  return (
    <>
      <Header />
      <main className="mx-auto flex min-h-[70vh] w-full max-w-6xl items-center justify-center px-5 py-16">
        <Suspense fallback={null}>
          <PaymentStatus orderId={orderId} />
        </Suspense>
      </main>
      <Footer />
    </>
  );
}
