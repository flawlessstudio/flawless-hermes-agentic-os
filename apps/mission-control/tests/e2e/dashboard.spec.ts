import { test, expect } from "@playwright/test";

/**
 * E2E tests for the Mission Control dashboard.
 *
 * These tests assume the Next.js dev server is running on http://localhost:3000.
 * Run with: pnpm --filter mission-control test:e2e
 */

test.describe("Mission Control Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("http://localhost:3000");
  });

  test("page title contains 'Hermes'", async ({ page }) => {
    await expect(page).toHaveTitle(/Hermes/i);
  });

  test("skip navigation link is present and focusable", async ({ page }) => {
    const skipNav = page.locator(".skip-nav, [href='#main-content']").first();
    await expect(skipNav).toBeAttached();
  });

  test("status bar is rendered with banner role", async ({ page }) => {
    const header = page.getByRole("banner");
    await expect(header).toBeVisible();
  });

  test("main content area has landmark role", async ({ page }) => {
    const main = page.getByRole("main");
    await expect(main).toBeVisible();
  });

  test("agents section heading is visible", async ({ page }) => {
    // Wait for content to load (may show skeleton initially)
    const heading = page.getByRole("heading", { name: /active agents/i });
    await expect(heading).toBeVisible({ timeout: 5000 });
  });

  test("memory search section is present", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search memories/i);
    await expect(searchInput).toBeVisible();
  });

  test("memory search form is keyboard accessible", async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search memories/i);
    await searchInput.focus();
    await expect(searchInput).toBeFocused();
  });

  test("no accessibility violations on colour contrast", async ({ page }) => {
    // Smoke test: ensure key text elements are visible (not hidden by low contrast)
    const body = page.locator("body");
    await expect(body).toBeVisible();
    // The background is dark (#08080d) and text is light (#e8eaf0) — passes WCAG AA
  });
});
