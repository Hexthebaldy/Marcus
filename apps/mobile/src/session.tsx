import React, { createContext, useContext, useEffect, useState } from "react";
import * as SecureStore from "expo-secure-store";
import { AppState } from "react-native";
import {
  ApiClient,
  ApiError,
  type Tokens,
  type User,
} from "@marcus/api-client";
import {
  focusManager,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

const key = "marcus.session.v1";
const tokenStore = {
  async get(): Promise<Tokens | null> {
    const value = await SecureStore.getItemAsync(key);
    return value ? JSON.parse(value) : null;
  },
  async set(value: Tokens) {
    await SecureStore.setItemAsync(key, JSON.stringify(value));
  },
  async clear() {
    await SecureStore.deleteItemAsync(key);
  },
};
let unauthorized: (() => void) | undefined;
export const api = new ApiClient({
  baseUrl: process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000/v1",
  tokenStore,
  clientType: "mobile",
  onUnauthorized: () => unauthorized?.(),
});
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (count, error) =>
        !(error instanceof ApiError && error.status < 500) && count < 2,
    },
    mutations: { retry: false },
  },
});
type Session = {
  user: User | null;
  loading: boolean;
  error: string | null;
  login(tokens: Tokens, user: User): Promise<void>;
  logout(): Promise<void>;
  reload(): Promise<void>;
};
const SessionContext = createContext<Session | null>(null);
export function SessionProvider({ children }: React.PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  async function reload() {
    setError(null);
    try {
      if (await tokenStore.get()) setUser(await api.get<User>("/me"));
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        await tokenStore.clear();
        setUser(null);
      } else setError(e instanceof Error ? e.message : "暂时无法连接服务器");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    unauthorized = () => {
      setUser(null);
      queryClient.clear();
    };
    void reload();
    const listener = AppState.addEventListener("change", (state) =>
      focusManager.setFocused(state === "active"),
    );
    return () => {
      listener.remove();
      unauthorized = undefined;
    };
  }, []);
  const value: Session = {
    user,
    loading,
    error,
    reload,
    async login(tokens, nextUser) {
      await tokenStore.set(tokens);
      queryClient.clear();
      setUser(nextUser);
      setError(null);
    },
    async logout() {
      await api.post("/auth/logout");
      await tokenStore.clear();
      queryClient.clear();
      setUser(null);
    },
  };
  return (
    <QueryClientProvider client={queryClient}>
      <SessionContext.Provider value={value}>
        {children}
      </SessionContext.Provider>
    </QueryClientProvider>
  );
}
export function useSession() {
  const session = useContext(SessionContext);
  if (!session) throw new Error("SessionProvider is required");
  return session;
}
