'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Building2, ShieldCheck, Sparkles, Workflow } from 'lucide-react';

import { useSession } from '@/components/session-context';

export default function HomePage() {
  const router = useRouter();
  const { ready, session } = useSession();

  useEffect(() => {
    if (!ready) {
      return;
    }
    if (session.token) {
      router.replace('/overview');
    }
  }, [ready, session.token, router]);

  if (!ready) {
    return <div className="login-wrap"><div className="card">Loading...</div></div>;
  }

  if (session.token) {
    return <div className="login-wrap"><div className="card">Redirecting...</div></div>;
  }

  return (
    <main className="marketing-shell">
      <section className="marketing-hero">
        <div className="marketing-copy">
          <span className="eyebrow">Continuous Compliance Workspace</span>
          <h1>Auditoria continua con evidencia, trazabilidad y paquetes listos para cliente.</h1>
          <p>
            Audity combina ejecucion automatica, biblioteca de evidencias, controles enterprise y reporting exportable
            en una sola plataforma multi-tenant.
          </p>
          <div className="actions">
            <Link href="/login" className="button button-primary">
              Entrar al producto
            </Link>
            <Link href="/login" className="button button-ghost">
              Acceso controlado
            </Link>
          </div>
          <div className="marketing-strip">
            <div className="marketing-stat">
              <strong>ISO 27001 / ENS / RGPD</strong>
              <span>Catalogos listos para correr.</span>
            </div>
            <div className="marketing-stat">
              <strong>Evidencia firmada</strong>
              <span>Integridad verificable y exportable.</span>
            </div>
            <div className="marketing-stat">
              <strong>Enterprise-ready</strong>
              <span>SCIM, MFA, RLS, observabilidad y pricing gates.</span>
            </div>
          </div>
        </div>
        <div className="marketing-panel">
          <div className="signal-card">
            <p className="signal-label">Por que compra un cliente</p>
            <ul className="signal-list">
              <li><Workflow size={16} /> Reduce el tiempo entre evidencia y hallazgo.</li>
              <li><ShieldCheck size={16} /> Mantiene cadena de custodia y cuarentena AV.</li>
              <li><Building2 size={16} /> Soporta operacion multiempresa con gobierno real.</li>
              <li><Sparkles size={16} /> Entrega reporting y paquete de auditor con un clic.</li>
            </ul>
          </div>
        </div>
      </section>
    </main>
  );
}
