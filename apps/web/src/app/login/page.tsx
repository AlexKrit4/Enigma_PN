import { Suspense } from "react";
import AuthForm from "@/components/site/AuthForm";
import Footer from "@/components/site/Footer";
import Header from "@/components/site/Header";

export const metadata = { title: "Вход" };

export default function Page() {
  return (
    <>
      <Header />
      <main className="mx-auto flex min-h-[70vh] w-full max-w-6xl items-center justify-center px-5 py-16">
        <Suspense fallback={null}>
          <AuthForm mode="login" />
        </Suspense>
      </main>
      <Footer />
    </>
  );
}
