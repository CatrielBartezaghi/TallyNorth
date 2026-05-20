"use client";

import React, { createContext, useContext, useState } from "react";
import Cookies from "js-cookie";
import { DEFAULT_LANGUAGE, isLanguage, translations, type Language, type Translations } from "./translations";

interface LanguageContextType {
  lang: Language;
  t: Translations;
  toggleLanguage: () => void;
}

const LANGUAGE_COOKIE = "NEXT_LOCALE";
const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({
  children,
  defaultLang = DEFAULT_LANGUAGE,
}: {
  children: React.ReactNode;
  defaultLang?: Language;
}) {
  const [lang, setLang] = useState<Language>(isLanguage(defaultLang) ? defaultLang : DEFAULT_LANGUAGE);

  const toggleLanguage = () => {
    const newLang: Language = lang === "es" ? "en" : "es";
    setLang(newLang);
    Cookies.set(LANGUAGE_COOKIE, newLang, { expires: 365 });
    document.documentElement.lang = newLang;
  };

  return (
    <LanguageContext.Provider value={{ lang, t: translations[lang], toggleLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
