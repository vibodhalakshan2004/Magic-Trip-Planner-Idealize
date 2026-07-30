"use client";

import { create } from "zustand";
import type { User } from "@/lib/api/types";

type AuthState = {
  authenticated: boolean;
  user: User | null;
  hydrated: boolean;
  setSession: (user: User) => void;
  setUser: (user: User | null) => void;
  setHydrated: (hydrated: boolean) => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>()((set) => ({
  authenticated: false,
  user: null,
  hydrated: false,
  setSession: (user) => set({ authenticated: true, user, hydrated: true }),
  setUser: (user) => set({ user }),
  setHydrated: (hydrated) => set({ hydrated }),
  logout: () => set({ authenticated: false, user: null, hydrated: true }),
}));
