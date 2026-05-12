import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/navbar";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "TallyNorth",
  description: "Personal finance platform - cashflow projection and credit card installment tracking",
  icons: {
    icon: "/tallynorth-logo.svg",
    apple: "/tallynorth-logo.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${geist.className} min-h-screen bg-background text-foreground antialiased`}>
        <Navbar />
        <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </main>
      </body>
    </html>
  );
}
