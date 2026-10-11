import { Suspense } from "react";
import Cabinet from "@/components/site/Cabinet";
import Footer from "@/components/site/Footer";
import Header from "@/components/site/Header";

export const metadata = { title: "Личный кабинет" };

export default function CabinetPage() {
  return (
    <>
      <Header />
      <main className="min-h-[70vh]">
        <Suspense fallback={null}>
          <Cabinet />
        </Suspense>
      </main>
      <Footer />
    </>
  );
}
