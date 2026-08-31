"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { configureApi } from "@/lib/api/client";
import { useAuthStore } from "@/lib/store/auth-store";
import { usePlannerStore } from "@/lib/store/planner-store";
import * as authApi from "@/lib/api/auth";

const protectedRoutePrefixes = ["/dashboard", "/planner", "/profile", "/reviews"];

function isProtectedRoute(pathname: string) {
  return protectedRoutePrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const logout = useAuthStore((state) => state.logout);
  const setSession = useAuthStore((state) => state.setSession);
  const setHydrated = useAuthStore((state) => state.setHydrated);
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } }));
  const apiConfig = useMemo(
    () => ({
      onUnauthorized: () => {
        logout();
        usePlannerStore.getState().reset();
        queryClient.clear();
        if (isProtectedRoute(pathname)) router.replace("/login");
      },
    }),
    [logout, pathname, queryClient, router],
  );

  useEffect(() => {
    configureApi(apiConfig.onUnauthorized);
    let active = true;
    authApi.me()
      .then((user) => { if (active) setSession(user); })
      .catch(() => { if (active) setHydrated(true); });
    return () => { active = false; };
  }, [apiConfig, setHydrated, setSession]);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
