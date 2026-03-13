import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';

const PUBLIC_PATHS = ['/', '/login'];
const PROTECTED_PREFIXES = [
  '/overview',
  '/projects',
  '/audit-runs',
  '/evidence',
  '/reports',
  '/enterprise',
  '/integrations',
];

function isProtectedPath(pathname: string): boolean {
  return PROTECTED_PREFIXES.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get('audity_session_token')?.value;

  if (PUBLIC_PATHS.includes(pathname) && token && pathname === '/login') {
    return NextResponse.redirect(new URL('/overview', request.url));
  }

  if (isProtectedPath(pathname) && !token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|audity-logo-mark.svg).*)'],
};
