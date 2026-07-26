import Link from "next/link";
import { AuthForm } from "@/components/AuthForm";

export default function LoginPage() {
  return (
    <>
      <AuthForm mode="login" />
      <p className="pb-8 text-center text-sm text-slate-500">New here? <Link className="font-bold text-emerald-700" href="/register">Create an account</Link></p>
    </>
  );
}
