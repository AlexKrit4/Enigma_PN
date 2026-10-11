import { redirect } from "next/navigation";

export default async function DashboardRedirect({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  redirect(params.paid ? "/cabinet?paid=1" : "/cabinet");
}
