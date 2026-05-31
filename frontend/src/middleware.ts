import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const token = request.cookies.get("token")?.value;
  const pathname = request.nextUrl.pathname;
  const isAuthPage = pathname.startsWith("/login") || pathname.startsWith("/register");

  if (pathname.startsWith("/auth/")) {
    return NextResponse.next();
  }
  
  if (!token && !isAuthPage) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", `${pathname}${request.nextUrl.search}`);
    return NextResponse.redirect(loginUrl);
  }
  
  if (token && isAuthPage) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (backend routes)
     * - auth (form action routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, tallynorth-logo.svg (public files)
     */
    "/((?!api|auth|_next/static|_next/image|favicon.ico|.*\\.svg|.*\\.png).*)",
  ],
};
