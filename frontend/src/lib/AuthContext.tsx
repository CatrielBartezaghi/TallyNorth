"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
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
  document.cookie = "token=; Max-Age=0; path=/";
}

export function AuthProvider({
  children,
  initialTokenPresent = false,
}: {
  children: React.ReactNode;
  initialTokenPresent?: boolean;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [hasServerToken, setHasServerToken] = useState(initialTokenPresent);
  const [isLoading, setIsLoading] = useState(initialTokenPresent);

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
        void authApi.logout();
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
    authApi.logout().finally(() => {
      window.location.href = "/login";
    });
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
