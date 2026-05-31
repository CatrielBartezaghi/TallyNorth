"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/lib/AuthContext";

function isAuthPath(pathname: string) {
  return pathname.startsWith("/login") || pathname.startsWith("/register");
}

export function AuthRedirector() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;

    if (user && isAuthPath(pathname)) {
      router.replace("/");
    }
  }, [isLoading, pathname, router, user]);

  return null;
}
