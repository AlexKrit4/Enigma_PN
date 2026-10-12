import { Suspense } from "react";
import Footer from "@/components/site/Footer";
import Header from "@/components/site/Header";
import VerifyForm from "@/components/site/VerifyForm";

export const metadata = { title: "Подтверждение почты" };

export default function Page() {
  return (
    <>
      <Header />
      <main className="mx-auto flex min-h-[70vh] w-full max-w-6xl items-center justify-center px-5 py-16">
        <Suspense fallback={null}>
          <VerifyForm />
        </Suspense>
      </main>
      <Footer />
    </>
  );
}
