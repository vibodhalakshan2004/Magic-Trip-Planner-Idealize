"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { configureApi } from "@/lib/api/client";
import { useAuthStore } from "@/lib/store/auth-store";
import { usePlannerStore } from "@/lib/store/planner-store";

export function Providers({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const logout = useAuthStore((state) => state.logout);
  const [queryClient] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } }));
  const apiConfig = useMemo(
    () => ({
      getToken: () => useAuthStore.getState().token,
      onUnauthorized: () => {
        logout();
        usePlannerStore.getState().reset();
        queryClient.clear();
        router.replace("/login");
      },
    }),
    [logout, queryClient, router],
  );

  useEffect(() => {
    configureApi(apiConfig.getToken, apiConfig.onUnauthorized);
  }, [apiConfig]);

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
