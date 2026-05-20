import type { Metadata } from "next";
import { Geist } from "next/font/google";
import { cookies } from "next/headers";
import "./globals.css";
import { Navbar } from "@/components/navbar";
import { AuthProvider } from "@/lib/AuthContext";
import { LanguageProvider } from "@/lib/LanguageContext";
import { DEFAULT_LANGUAGE, isLanguage } from "@/lib/translations";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "TallyNorth",
  description: "Personal finance platform - cashflow projection and credit card installment tracking",
  icons: {
    icon: "/tallynorth-logo.svg",
    apple: "/tallynorth-logo.svg",
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const cookieStore = await cookies();
  const cookieLang = cookieStore.get("NEXT_LOCALE")?.value;
  const currentLang = isLanguage(cookieLang) ? cookieLang : DEFAULT_LANGUAGE;

  return (
    <html lang={currentLang} className="dark">
      <body className={`${geist.className} min-h-screen bg-background text-foreground antialiased`}>
        <AuthProvider>
          <LanguageProvider defaultLang={currentLang}>
            <Navbar />
            <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
              {children}
            </main>
          </LanguageProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
