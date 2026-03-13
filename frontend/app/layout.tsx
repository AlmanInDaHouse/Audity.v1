import type { Metadata } from 'next';
import { AppShell } from '@/components/app-shell';
import { SessionProvider } from '@/components/session-context';
import { ToastProvider } from '@/components/toast-provider';
import './globals.css';

export const metadata: Metadata = {
  title: 'Audity',
  description: 'Continuous compliance auditing workspace',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>
        <SessionProvider>
          <ToastProvider>
            <AppShell>{children}</AppShell>
          </ToastProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
