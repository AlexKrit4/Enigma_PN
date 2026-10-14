import { Suspense } from "react";
import AuthForm from "@/components/site/AuthForm";
import AuthLayout from "@/components/site/AuthLayout";

export const metadata = { title: "Вход" };

export default function Page() {
  return (
    <AuthLayout variant="login">
      <Suspense fallback={<div className="loading-state">Загружаем форму…</div>}>
        <AuthForm mode="login" />
      </Suspense>
    </AuthLayout>
  );
}
