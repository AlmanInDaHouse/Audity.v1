import { expect, test } from '@playwright/test';

const projectName = process.env.E2E_PROJECT_NAME || 'Demo Project';

test('project detail defers risk loading until risk tab is opened', async ({ page }) => {
  let riskCalls = 0;

  await page.route('**/projects/*/risk', async (route) => {
    riskCalls += 1;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        dimensions: [],
        assets: [],
        asset_relations: [],
        threats: [],
        safeguards: [],
        assessments: [],
        scenarios: [],
        risk_register: [],
      }),
    });
  });

  await page.goto('/login');
  await page.getByTestId('login-demo-user').selectOption('admin@demo.local');
  await page.getByTestId('login-submit').click();

  await expect(page).toHaveURL(/\/overview$/);

  await page.goto('/projects');
  await expect(page.getByRole('link', { name: projectName })).toBeVisible({ timeout: 15_000 });
  await page.getByRole('link', { name: projectName }).click();

  await expect(page.getByRole('heading', { name: projectName })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText(/Latest run status/i)).toBeVisible({ timeout: 15_000 });
  expect(riskCalls).toBe(0);

  await page.getByRole('button', { name: 'Risk' }).click();
  await expect.poll(() => riskCalls).toBe(1);
  await expect(page.getByTestId('formal-risk-register')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Formal risk register' })).toBeVisible();
});
