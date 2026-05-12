"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  CreditCard,
  Landmark,
  LineChart,
  List,
  Receipt,
  Search,
  Settings,
  Target,
  WalletCards,
} from "lucide-react";

const links = [
  { href: "/", label: "Resumen", icon: BarChart3 },
  { href: "/transactions", label: "Movimientos", icon: List },
  { href: "/budgets", label: "Presupuestos", icon: Receipt },
  { href: "/investments", label: "Inversiones", icon: LineChart },
  { href: "/accounts", label: "Cuentas", icon: Landmark },
  { href: "/credit-cards", label: "Tarjetas", icon: CreditCard },
  { href: "/saving-goals", label: "Metas", icon: Target },
  { href: "/categories", label: "Categorías", icon: Settings },
  { href: "/exchange-rates", label: "Cotizaciones", icon: Search },
];

export function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-background/90 backdrop-blur-sm">
      <div className="mx-auto flex max-w-[1800px] items-center gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2 font-semibold text-lg tracking-tight shrink-0">
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

        <nav className="flex flex-1 items-center gap-1 overflow-x-auto">
          {links.map((link) => {
            const active = pathname === link.href;
            const Icon = link.icon;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors ${
                  active
                    ? "bg-emerald-500/10 text-emerald-300"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`}
              >
                <Icon size={15} />
                {link.label}
              </Link>
            );
          })}
        </nav>
        <div className="hidden min-w-56 items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground xl:flex">
          <Search size={15} />
          <span>Buscar...</span>
        </div>
      </div>
    </header>
  );
}
