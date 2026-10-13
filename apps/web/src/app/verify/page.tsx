import { Suspense } from "react";
import AuthLayout from "@/components/site/AuthLayout";
import VerifyForm from "@/components/site/VerifyForm";

export const metadata = { title: "Подтверждение почты" };

export default function Page() {
  return (
    <AuthLayout variant="verify">
      <Suspense fallback={<div className="loading-state">Загружаем форму…</div>}>
        <VerifyForm />
      </Suspense>
    </AuthLayout>
  );
}
