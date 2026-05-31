import { NextRequest, NextResponse } from "next/server";

const TOKEN_COOKIE = "token";
const TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

export function backendUrl(request: NextRequest, path: string) {
  const configuredBase = process.env.SERVER_API_URL || process.env.NEXT_PUBLIC_API_URL;
  const fallbackBase =
    process.env.NODE_ENV === "development" ? "http://localhost:8000" : request.nextUrl.origin;
  return new URL(path, configuredBase || fallbackBase);
}

export function safeRedirectUrl(request: NextRequest, rawNext: FormDataEntryValue | string | null) {
  const next = typeof rawNext === "string" ? rawNext : "/";
  if (!next.startsWith("/") || next.startsWith("//")) {
    return new URL("/", request.url);
  }
  return new URL(next, request.url);
}

export function redirectWithSession(request: NextRequest, accessToken: string, destination: URL) {
  const response = NextResponse.redirect(destination, { status: 303 });
  response.cookies.set({
    name: TOKEN_COOKIE,
    value: accessToken,
    httpOnly: true,
    secure: request.nextUrl.protocol === "https:" || process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: TOKEN_MAX_AGE_SECONDS,
  });
  return response;
}

export function redirectWithClearedSession(request: NextRequest, destination = "/login") {
  const response = NextResponse.redirect(new URL(destination, request.url), { status: 303 });
  response.cookies.set({
    name: TOKEN_COOKIE,
    value: "",
    path: "/",
    maxAge: 0,
  });
  return response;
}
