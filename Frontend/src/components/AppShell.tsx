"use client";

import { LayoutDashboard, LogIn, LogOut, Map, Menu, MessageSquareText, Plus, UserRound, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { LogoBrand } from "@/components/LogoBrand";
import { ProfileAvatar } from "@/components/ProfileAvatar";
import { useAuthStore } from "@/lib/store/auth-store";
import { usePlannerStore } from "@/lib/store/planner-store";
import * as authApi from "@/lib/api/auth";
import { cn } from "@/lib/utils/format";

const navigation = [
  { href: "/dashboard", label: "My trips", icon: LayoutDashboard },
  { href: "/planner/new", label: "Plan a trip", icon: Map },
  { href: "/reviews", label: "Travel notes", icon: MessageSquareText },
  { href: "/profile", label: "Profile", icon: UserRound },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const resetPlanner = usePlannerStore((state) => state.reset);
  const [menuOpen, setMenuOpen] = useState(false);

  async function signOut() {
    await authApi.logout().catch(() => undefined);
    logout();
    resetPlanner();
    queryClient.clear();
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-[#f8f7f2]">
      <header className="sticky top-0 z-40 border-b border-[#17453a]/10 bg-[#f8f7f2]/92 backdrop-blur-xl">
        <div className="mx-auto flex h-[72px] max-w-[1440px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <LogoBrand />
          <nav className="hidden items-center gap-1 rounded-full border border-[#17453a]/10 bg-white/70 p-1 md:flex" aria-label="Main navigation">
            {navigation.map((item) => {
              const active = pathname === item.href || (item.href === "/planner/new" && pathname.startsWith("/planner/"));
              return (
                <Link
                  key={item.href}
                  className={cn(
                    "rounded-full px-4 py-2 text-sm font-semibold transition-colors",
                    active ? "bg-[#17453a] text-white shadow-sm" : "text-[#4c625b] hover:bg-white hover:text-[#173e34]",
                  )}
                  href={item.href}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-2">
            {user ? (
              <>
                <Link href="/profile" className="hidden rounded-full sm:inline-flex" aria-label={`Open ${user.name}'s profile`} title={user.name}>
                  <ProfileAvatar user={user} className="h-9 w-9" />
                </Link>
                <Button className="hidden md:inline-flex" variant="ghost" aria-label="Log out" onClick={signOut}>
                  <LogOut className="h-4 w-4" />
                </Button>
              </>
            ) : (
              <Button className="hidden sm:inline-flex" variant="secondary" onClick={() => router.push("/login")}>
                <LogIn className="h-4 w-4" /> Sign in
              </Button>
            )}
            <button
              type="button"
              className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-[#17453a]/10 bg-white text-[#17453a] md:hidden"
              aria-label={menuOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
            >
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>
        {menuOpen ? (
          <nav className="border-t border-[#17453a]/10 bg-[#f8f7f2] px-4 py-4 md:hidden" aria-label="Mobile navigation">
            <div className="mx-auto grid max-w-[1440px] gap-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href || (item.href === "/planner/new" && pathname.startsWith("/planner/"));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMenuOpen(false)}
                    className={cn(
                      "flex min-h-12 items-center gap-3 rounded-xl px-3 text-sm font-semibold",
                      active ? "bg-[#e4eee8] text-[#17453a]" : "text-[#4c625b]",
                    )}
                  >
                    <Icon className="h-4 w-4" /> {item.label}
                  </Link>
                );
              })}
              {user ? (
                <button type="button" onClick={signOut} className="flex min-h-12 items-center gap-3 rounded-xl px-3 text-left text-sm font-semibold text-[#7c4133]">
                  <LogOut className="h-4 w-4" /> Sign out
                </button>
              ) : (
                <Link href="/login" className="mt-2 inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-[#17453a] px-4 text-sm font-semibold text-white">
                  <LogIn className="h-4 w-4" /> Sign in
                </Link>
              )}
            </div>
          </nav>
        ) : null}
      </header>
      <main className="mx-auto w-full max-w-[1440px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">{children}</main>
      {user && pathname !== "/planner/new" && !pathname.startsWith("/planner/") ? (
        <Link
          href="/planner/new"
          className="fixed bottom-5 right-5 z-30 inline-flex h-14 items-center gap-2 rounded-full bg-[#e36f3d] px-5 text-sm font-bold text-white shadow-[0_12px_28px_rgba(113,53,27,.22)] transition hover:-translate-y-0.5 hover:bg-[#cb5f31] md:hidden"
        >
          <Plus className="h-5 w-5" /> New trip
        </Link>
      ) : null}
    </div>
  );
}
