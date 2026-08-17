"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BarChart3,
  CreditCard,
  Landmark,
  LineChart,
  List,
  LogOut,
  Menu,
  Receipt,
  Search,
  Settings,
  Target,
  User as UserIcon,
  X,
} from "lucide-react";
import { useAuth } from "@/lib/AuthContext";
import { useLanguage } from "@/lib/LanguageContext";

const links = [
  { href: "/", labelKey: "dashboard", icon: BarChart3 },
  { href: "/transactions", labelKey: "transactions", icon: List },
  { href: "/budgets", labelKey: "budgets", icon: Receipt },
  { href: "/investments", labelKey: "investments", icon: LineChart },
  { href: "/accounts", labelKey: "accounts", icon: Landmark },
  { href: "/credit-cards", labelKey: "creditCards", icon: CreditCard },
  { href: "/saving-goals", labelKey: "savingGoals", icon: Target },
  { href: "/categories", labelKey: "categories", icon: Settings },
  { href: "/exchange-rates", labelKey: "exchangeRates", icon: Search },
] as const;

export function Navbar() {
  const pathname = usePathname();
  const { user, logout, isLoading } = useAuth();
  const { lang, t, toggleLanguage } = useLanguage();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-[1800px] items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex shrink-0 items-center gap-2 text-lg font-semibold tracking-tight">
          <Image
            src="/tallynorth-logo.svg"
            alt=""
            width={32}
            height={32}
            aria-hidden="true"
            className="size-8 rounded-lg"
            priority
          />
          <span className="bg-gradient-to-r from-cyan-300 to-emerald-300 bg-clip-text text-transparent">
            TallyNorth
          </span>
        </Link>

        {user && !isLoading ? (
          <>
            <nav className="hidden flex-1 items-center gap-1 overflow-x-auto lg:flex">
              {links.map((link) => {
                const active = pathname === link.href;
                const Icon = link.icon;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                      active
                        ? "bg-emerald-500/10 text-emerald-300"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    }`}
                  >
                    <Icon size={15} />
                    {t.nav[link.labelKey]}
                  </Link>
                );
              })}
            </nav>

            <div className="hidden min-w-56 items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground 2xl:flex">
              <Search size={15} />
              <span>{t.nav.search}</span>
            </div>

            <div className="ml-2 hidden items-center gap-2 border-l border-border pl-4 lg:flex">
              <button
                type="button"
                onClick={toggleLanguage}
                className="rounded-md border border-border px-2.5 py-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                title={t.nav.switchToEnglish}
              >
                {lang === "es" ? "EN" : "ES"}
              </button>
              <div className="hidden items-center gap-2 text-sm text-muted-foreground xl:flex">
                <UserIcon size={15} />
                <span>{user.email}</span>
              </div>
              <button
                type="button"
                onClick={logout}
                className="flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-red-950/30"
                title={t.nav.logout}
              >
                <LogOut size={15} />
              </button>
            </div>

            <button
              type="button"
              onClick={() => setMobileOpen((open) => !open)}
              className="ml-auto inline-flex size-10 items-center justify-center rounded-md border border-border text-muted-foreground transition-colors hover:bg-accent hover:text-foreground lg:hidden"
              aria-expanded={mobileOpen}
              aria-controls="mobile-navigation"
              aria-label={mobileOpen ? "Cerrar menú" : "Abrir menú"}
            >
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </>
        ) : (
          <div className="flex-1" />
        )}
      </div>

      {user && !isLoading && mobileOpen ? (
        <div id="mobile-navigation" className="border-t border-border bg-background lg:hidden">
          <div className="mx-auto max-w-[1800px] px-4 py-3 sm:px-6">
            <nav className="grid gap-1">
              {links.map((link) => {
                const active = pathname === link.href;
                const Icon = link.icon;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setMobileOpen(false)}
                    className={`flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium transition-colors ${
                      active
                        ? "bg-emerald-500/10 text-emerald-300"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    }`}
                  >
                    <Icon size={17} />
                    {t.nav[link.labelKey]}
                  </Link>
                );
              })}
            </nav>

            <div className="mt-3 flex items-center justify-between gap-3 border-t border-border pt-3">
              <div className="min-w-0 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <UserIcon size={15} className="shrink-0" />
                  <span className="truncate">{user.email}</span>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  onClick={toggleLanguage}
                  className="rounded-md border border-border px-2.5 py-1.5 text-xs font-semibold text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                  title={t.nav.switchToEnglish}
                >
                  {lang === "es" ? "EN" : "ES"}
                </button>
                <button
                  type="button"
                  onClick={logout}
                  className="flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium text-red-400 transition-colors hover:bg-red-950/30"
                  title={t.nav.logout}
                >
                  <LogOut size={15} />
                  <span>{t.nav.logout}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </header>
  );
}
