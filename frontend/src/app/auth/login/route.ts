import { NextRequest, NextResponse } from "next/server";

import { backendUrl, redirectWithSession, safeRedirectUrl } from "../_session";

export async function POST(request: NextRequest) {
  const formData = await request.formData();
  const destination = safeRedirectUrl(request, formData.get("next"));

  const response = await fetch(backendUrl(request, "/api/auth/login"), {
    method: "POST",
    body: formData,
    cache: "no-store",
  });

  if (!response.ok) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("error", "invalid");
    loginUrl.searchParams.set("next", destination.pathname + destination.search);
    return NextResponse.redirect(loginUrl, { status: 303 });
  }

  const data = await response.json();
  return redirectWithSession(request, data.access_token, destination);
}
