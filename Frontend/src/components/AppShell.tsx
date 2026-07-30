"use client";

import { LogOut, Menu, Star } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { LogoBrand } from "@/components/LogoBrand";
import { useAuthStore } from "@/lib/store/auth-store";
import { usePlannerStore } from "@/lib/store/planner-store";
import * as authApi from "@/lib/api/auth";

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const resetPlanner = usePlannerStore((state) => state.reset);
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          <LogoBrand />
          <nav className="hidden items-center gap-2 md:flex">
            <Link className="rounded-md px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100" href="/dashboard">Dashboard</Link>
            <Link className="rounded-md px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100" href="/planner/new">Planner</Link>
            <Link className="rounded-md px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100" href="/reviews">Reviews</Link>
          </nav>
          <div className="flex items-center gap-2">
            {user ? <span className="hidden text-sm font-medium text-slate-600 sm:block">{user.name}</span> : null}
            {user ? (
              <Button
                variant="ghost"
                aria-label="Log out"
                onClick={async () => {
                  await authApi.logout().catch(() => undefined);
                  logout();
                  resetPlanner();
                  queryClient.clear();
                  router.push("/login");
                }}
              >
                <LogOut className="h-4 w-4" />
              </Button>
            ) : (
              <Button onClick={() => router.push("/login")}><Star className="h-4 w-4" /> Sign in</Button>
            )}
            <Menu className="h-5 w-5 text-slate-400 md:hidden" />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}
