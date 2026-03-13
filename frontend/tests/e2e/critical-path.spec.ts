import fs from 'node:fs/promises';
import path from 'node:path';

import { expect, test, type Page } from '@playwright/test';

const projectName = process.env.E2E_PROJECT_NAME || 'Demo Project';
const evidenceDir = path.resolve(__dirname, '../../../.tmp/release_evidence/e2e');

async function saveScreenshot(page: Page, name: string) {
  await fs.mkdir(evidenceDir, { recursive: true });
  await page.screenshot({ path: path.join(evidenceDir, name), fullPage: true });
}

test.describe('Release critical path', () => {
  test('login, audit run, reports PDF, AI removal and DPA gate', async ({ page }) => {
    await fs.mkdir(evidenceDir, { recursive: true });

    await page.goto('/login');
    await page.getByTestId('login-demo-user').selectOption('admin@demo.local');
    await page.getByTestId('login-submit').click();

    await expect(page).toHaveURL(/\/overview$/);
    await expect(page.getByRole('heading', { name: /demo org|organization overview/i })).toBeVisible();
    await expect(page.getByText('Readiness score')).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/DPA pendiente/i)).toBeVisible({ timeout: 15_000 });
    await saveScreenshot(page, '01-overview.png');

    await page.goto('/projects');
    await expect(page.getByRole('link', { name: projectName })).toBeVisible({ timeout: 15_000 });
    await page.getByRole('link', { name: projectName }).click();

    await expect(page.getByRole('heading', { name: projectName })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText(/Latest run status/i)).toBeVisible({ timeout: 15_000 });
    await saveScreenshot(page, '02-project.png');

    await page.getByTestId('project-run-one-click').click();
    await expect(page).toHaveURL(/\/projects\/.*\/runs\/.*/);
    await expect(page.getByRole('heading', { name: 'Audit Run' })).toBeVisible();
    const projectId = page.url().match(/projects\/([^/]+)\/runs\//)?.[1];
    expect(projectId).toBeTruthy();

    await expect
      .poll(
        async () => {
          const text = await page.locator('body').innerText();
          if (text.includes('failed')) {
            return 'failed';
          }
          if (text.includes('completed')) {
            return 'completed';
          }
          return 'running';
        },
        { timeout: 120_000, intervals: [1_000, 2_000, 3_000] },
      )
      .toBe('completed');

    await expect(page.getByRole('button', { name: 'Download PDF' })).toBeEnabled();
    await saveScreenshot(page, '03-run-completed.png');

    const pdfDownload = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download PDF' }).click();
    const pdf = await pdfDownload;
    const pdfPath = path.join(evidenceDir, 'audit-report-e2e.pdf');
    await pdf.saveAs(pdfPath);
    const pdfBytes = await fs.readFile(pdfPath);
    expect(pdfBytes.byteLength).toBeGreaterThan(1024);
    expect(pdfBytes.subarray(0, 5).toString('utf8')).toBe('%PDF-');

    await page.goto('/reports');
    await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Download PDF' }).first()).toBeVisible();
    await expect(page.getByRole('cell', { name: projectName }).first()).toBeVisible();
    await saveScreenshot(page, '04-reports.png');

    await expect(page.getByText(/AI Orchestrator/i)).toHaveCount(0);
    const token = await page.evaluate(() => window.localStorage.getItem('audity_token') || '');
    expect(token).toBeTruthy();
    const orchestratorStatus = await page.evaluate(
      async ({ bearer, selectedProjectId }) => {
        const response = await fetch('/api/ai-orchestrator/runs', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${bearer}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            project_id: selectedProjectId,
            task_type: 'audit_fix',
          }),
        });
        return response.status;
      },
      { bearer: token, selectedProjectId: projectId },
    );
    expect(orchestratorStatus).toBe(404);

    await page.goto('/enterprise');
    await expect(page.getByRole('heading', { name: 'Enterprise Settings' })).toBeVisible();
    await expect(page.getByText(/Estado actual:\s*pending/i)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Complete onboarding' })).toBeDisabled();
    await page.getByLabel('DPA reference').fill('DPA-E2E-2026-001');
    await page.getByRole('button', { name: 'Register signed DPA' }).click();
    await expect(page.getByText(/Estado actual:\s*signed/i)).toBeVisible();
    await expect(page.getByRole('button', { name: 'Complete onboarding' })).toBeEnabled();
    await page.getByRole('button', { name: 'Complete onboarding' }).click();
    await expect(page.getByText(/Onboarding:\s*completed/i)).toBeVisible();
    await saveScreenshot(page, '05-enterprise.png');

    await page.goto('/overview');
    await expect(page.getByText(/DPA firmado/i)).toBeVisible();
    await saveScreenshot(page, '06-overview-post-dpa.png');
  });
});
