"use client";

import { useState } from "react";
import Link from "next/link";

import { useLanguage } from "@/lib/LanguageContext";

type LoginFormProps = {
  hasError: boolean;
  next: string;
};

export function LoginForm({ hasError, next }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { t } = useLanguage();
  const registerHref = next === "/" ? "/register" : `/register?next=${encodeURIComponent(next)}`;

  return (
    <div className="flex min-h-[80vh] flex-col items-center justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-foreground">
          {t.auth.welcome}
        </h2>
        <p className="mt-2 text-center text-sm text-muted-foreground">
          {t.auth.loginSubtitle}
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="border border-border bg-card px-4 py-8 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" action="/auth/login" method="post" onSubmit={() => setLoading(true)}>
            <input type="hidden" name="next" value={next} />
            {hasError && (
              <div className="rounded-md border border-red-500/20 bg-red-500/10 p-4">
                <p className="text-sm text-red-400">{t.auth.loginError}</p>
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-foreground">
                {t.auth.email}
              </label>
              <div className="mt-1">
                <input
                  id="email"
                  name="username"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="block w-full appearance-none rounded-md border border-input bg-background px-3 py-2 text-foreground shadow-sm placeholder:text-muted-foreground focus:border-emerald-500 focus:outline-none focus:ring-emerald-500 sm:text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-foreground">
                {t.auth.password}
              </label>
              <div className="mt-1">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full appearance-none rounded-md border border-input bg-background px-3 py-2 text-foreground shadow-sm placeholder:text-muted-foreground focus:border-emerald-500 focus:outline-none focus:ring-emerald-500 sm:text-sm"
                />
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="text-sm">
                <Link href={registerHref} className="font-medium text-emerald-400 hover:text-emerald-300">
                  {t.auth.noAccount}
                </Link>
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="flex w-full justify-center rounded-md border border-transparent bg-emerald-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 disabled:opacity-50"
              >
                {loading ? t.auth.loggingIn : t.auth.login}
              </button>
            </div>
          </form>

          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="bg-card px-2 text-muted-foreground">{t.auth.demoDivider}</span>
              </div>
            </div>

            <div className="mt-6">
              <form action="/auth/login" method="post" onSubmit={() => setLoading(true)}>
                <input type="hidden" name="username" value="demo@finance.com" />
                <input type="hidden" name="password" value="demo123" />
                <input type="hidden" name="next" value={next} />
                <button
                  type="submit"
                  className="flex w-full items-center justify-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-accent focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
                >
                  {t.auth.demoButton}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
