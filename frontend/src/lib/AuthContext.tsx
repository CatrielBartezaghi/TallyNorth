"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import Cookies from "js-cookie";
import { authApi } from "./api";

interface User {
  id: string;
  email: string;
  is_active: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function isAuthRoute() {
  if (typeof window === "undefined") return false;
  return window.location.pathname.startsWith("/login") || window.location.pathname.startsWith("/register");
}

function clearTokenCookie() {
  Cookies.remove("token", { path: "/" });
}

export function AuthProvider({
  children,
  initialTokenPresent = false,
}: {
  children: React.ReactNode;
  initialTokenPresent?: boolean;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => Cookies.get("token") ?? null);
  const [hasServerToken, setHasServerToken] = useState(initialTokenPresent);
  const [isLoading, setIsLoading] = useState(() => Boolean(Cookies.get("token")) || initialTokenPresent);

  useEffect(() => {
    const hasToken = Boolean(token) || hasServerToken;

    if (!hasToken) {
      if (!isAuthRoute() && typeof window !== "undefined") {
        window.location.href = "/login";
      }
      return;
    }

    let cancelled = false;

    authApi.me(token)
      .then((data) => {
        if (!cancelled) setUser(data);
      })
      .catch(() => {
        clearTokenCookie();
        setToken(null);
        setHasServerToken(false);
        if (!cancelled) {
          setUser(null);
          if (!isAuthRoute()) {
            window.location.href = "/login";
          }
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token, hasServerToken]);

  const login = (newToken: string, newUser: User) => {
    Cookies.set("token", newToken, { expires: 7, path: "/", sameSite: "lax", secure: window.location.protocol === "https:" });
    setToken(newToken);
    setHasServerToken(true);
    setUser(newUser);
    setIsLoading(false);
  };

  const logout = () => {
    clearTokenCookie();
    setToken(null);
    setHasServerToken(false);
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
