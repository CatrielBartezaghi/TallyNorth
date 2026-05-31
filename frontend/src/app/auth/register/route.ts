import { NextRequest, NextResponse } from "next/server";

import { backendUrl, redirectWithSession, safeRedirectUrl } from "../_session";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const destination = safeRedirectUrl(request, formData.get("next"));
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");

  const registerResponse = await fetch(backendUrl(request, "/api/auth/register"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
    cache: "no-store",
  });

  if (!registerResponse.ok) {
    const registerUrl = new URL("/register", request.url);
    registerUrl.searchParams.set("error", "register");
    registerUrl.searchParams.set("next", destination.pathname + destination.search);
    return NextResponse.redirect(registerUrl, { status: 303 });
  }

  const loginData = new FormData();
  loginData.set("username", email);
  loginData.set("password", password);

  const loginResponse = await fetch(backendUrl(request, "/api/auth/login"), {
    method: "POST",
    body: loginData,
    cache: "no-store",
  });

  if (!loginResponse.ok) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("error", "invalid");
    loginUrl.searchParams.set("next", destination.pathname + destination.search);
    return NextResponse.redirect(loginUrl, { status: 303 });
  }

  const data = await loginResponse.json();
  return redirectWithSession(request, data.access_token, destination);
}
