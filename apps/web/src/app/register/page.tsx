import { Suspense } from "react";
import AuthForm from "@/components/site/AuthForm";
import AuthLayout from "@/components/site/AuthLayout";

export const metadata = { title: "Регистрация" };

export default function Page() {
  return (
    <AuthLayout variant="register">
      <Suspense fallback={<div className="loading-state">Загружаем форму…</div>}>
        <AuthForm mode="register" />
      </Suspense>
    </AuthLayout>
  );
}
