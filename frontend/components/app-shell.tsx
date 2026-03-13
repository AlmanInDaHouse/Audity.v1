'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Building2, FileText, FolderKanban, Home, LibraryBig, LogOut, Menu, PlayCircle, PlugZap } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { ConfirmDialog } from '@/components/confirm-dialog';
import { useSession } from '@/components/session-context';
import { prettyRole } from '@/lib/format';
import type { UserRole } from '@/lib/types';

type NavItem = {
  href: string;
  label: string;
  icon: React.ReactNode;
  allowRoles?: UserRole[];
};

const NAV_ITEMS: NavItem[] = [
  { href: '/overview', label: 'Overview', icon: <Home size={16} /> },
  { href: '/projects', label: 'Projects', icon: <FolderKanban size={16} /> },
  { href: '/integrations', label: 'Integrations', icon: <PlugZap size={16} /> },
  { href: '/evidence', label: 'Evidence Library', icon: <LibraryBig size={16} /> },
  { href: '/audit-runs', label: 'Audit Runs', icon: <PlayCircle size={16} /> },
  { href: '/reports', label: 'Reports', icon: <FileText size={16} /> },
  { href: '/enterprise', label: 'Enterprise', icon: <Building2 size={16} />, allowRoles: ['org_admin'] },
];

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { session, ready, logout } = useSession();
  const [mobileNav, setMobileNav] = useState(false);
  const [confirmLogout, setConfirmLogout] = useState(false);
  const isPublicRoute = pathname === '/' || pathname === '/login';

  useEffect(() => {
    if (!ready) {
      return;
    }
    if (!session.token && !isPublicRoute) {
      router.replace('/login');
    }
  }, [ready, session.token, isPublicRoute, router]);

  const visibleNav = useMemo(
    () => NAV_ITEMS.filter((item) => !item.allowRoles || (session.role && item.allowRoles.includes(session.role))),
    [session.role],
  );

  if (!ready) {
    return <div className="login-wrap"><div className="card">Loading session...</div></div>;
  }

  if (isPublicRoute) {
    return <>{children}</>;
  }

  if (!session.token) {
    return null;
  }

  const doLogout = () => {
    logout();
    setConfirmLogout(false);
    router.push('/login');
  };

  return (
    <>
      <div className="app-shell">
        <aside className="sidebar" aria-label="Main navigation">
          <div className="brand">
            <Image
              src="/audity-logo-mark.svg"
              alt="Audity logo"
              width={52}
              height={52}
              className="brand-logo"
              priority
            />
            <div className="brand-copy">
              <h1 className="brand-title">Audity</h1>
              <p className="brand-sub">Continuous Compliance</p>
            </div>
          </div>
          <nav className="nav-links">
            {visibleNav.map((item) => (
              <Link key={item.href} href={item.href} className={`nav-link ${isActive(pathname, item.href) ? 'active' : ''}`}>
                {item.icon}
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>
        <section className="main-frame">
          <header className="topbar">
            <div className="topbar-left">
              <button
                type="button"
                className="button button-ghost mobile-only"
                aria-label="Toggle navigation"
                onClick={() => setMobileNav((current) => !current)}
              >
                <Menu size={16} />
              </button>
              <strong>Organization {session.orgId.slice(0, 8)}</strong>
            </div>
            <div className="topbar-right">
              <span>{session.email}</span>
              <span className="role-pill">{prettyRole(session.role || 'unknown')}</span>
              <button type="button" className="button button-ghost" onClick={() => setConfirmLogout(true)}>
                <LogOut size={14} style={{ marginRight: 6 }} />
                Logout
              </button>
            </div>
          </header>
          {mobileNav && (
            <div className="card" style={{ margin: 12 }}>
              <nav className="nav-links">
                {visibleNav.map((item) => (
                  <Link
                    key={`${item.href}-mobile`}
                    href={item.href}
                    className={`nav-link ${isActive(pathname, item.href) ? 'active' : ''}`}
                    onClick={() => setMobileNav(false)}
                  >
                    {item.icon}
                    {item.label}
                  </Link>
                ))}
              </nav>
            </div>
          )}
          <main className="content">{children}</main>
        </section>
      </div>
      <ConfirmDialog
        open={confirmLogout}
        title="Logout"
        body="Close this session and return to login?"
        confirmLabel="Logout"
        onConfirm={doLogout}
        onCancel={() => setConfirmLogout(false)}
      />
    </>
  );
}
