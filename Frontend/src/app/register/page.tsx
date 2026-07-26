import Link from "next/link";
import { AuthForm } from "@/components/AuthForm";

export default function RegisterPage() {
  return (
    <>
      <AuthForm mode="register" />
      <p className="pb-8 text-center text-sm text-slate-500">Already registered? <Link className="font-bold text-emerald-700" href="/login">Log in</Link></p>
    </>
  );
}
