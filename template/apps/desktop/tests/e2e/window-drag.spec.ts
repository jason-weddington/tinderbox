import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import AxeBuilder from '@axe-core/playwright';

import { expect, test } from './fixtures';
import { bootTauri, centre, chooseButton, dragsAt, hitClass, hitTag, open, userSelect } from './helpers';

// The Mac app's window drags by its top band. Tauri starts a drag only when the
// pressed element itself, or an ancestor marked "deep", carries
// data-tauri-drag-region; children do not inherit a bare attribute.

test('the Tauri pin matches the vendored drag rules', () => {
  const lock = readFileSync(resolve(process.cwd(), 'Cargo.lock'), 'utf8');
  const lockVersion = /name = "tauri"\nversion = "([^"]+)"/.exec(lock)?.[1];
  const pkg = JSON.parse(readFileSync(resolve(process.cwd(), 'package.json'), 'utf8')) as {
    dependencies: Record<string, string>;
  };
  const message =
    'Tauri upgraded: re-sync isClickableElement/isDragRegion in helpers.ts with tauri <new>/src/window/scripts/drag.js, then bump this pin';
  expect(lockVersion, message).toBe('2.12.4');
  expect(pkg.dependencies['@tauri-apps/api'], message).toBe('2.12.4');
});

test('tauri mode: the top strip, band and heading drag; the button does not', async ({ page }) => {
  await bootTauri(page);
  const stripBottom = await page.locator('.titlebar').evaluate((el) => el.getBoundingClientRect().bottom);

  expect(await dragsAt(page, 480, 4)).toBe(true);
  expect(await hitClass(page, 480, 4)).toContain('titlebar');

  // The strip must not cover the band's controls.
  const button = chooseButton(page);
  const buttonTop = await button.evaluate((el) => el.getBoundingClientRect().top);
  expect(buttonTop).toBeGreaterThanOrEqual(stripBottom);

  const [hx, hy] = await centre(page.getByRole('heading', { level: 1 }));
  expect(await dragsAt(page, hx, hy)).toBe(true);
  const band = await page.locator('.band').boundingBox();
  if (band === null) throw new Error('no band');
  const edgeX = band.x + band.width - 2;
  const edgeY = band.y + band.height / 2;
  expect(await dragsAt(page, edgeX, edgeY)).toBe(true);
  expect(await hitTag(page, edgeX, edgeY)).toBe('header');

  const [bx, by] = await centre(button);
  expect(await dragsAt(page, bx, by)).toBe(false);
  const [mx, my] = await centre(page.locator('main .status'));
  expect(await dragsAt(page, mx, my)).toBe(false);

  // Chrome text does not select; the status text still does.
  expect(await userSelect(button)).toBe('none');
  expect(await userSelect(page.getByRole('heading', { level: 1 }))).toBe('none');
  expect(await userSelect(page.locator('main .status'))).not.toBe('none');
});

test('the mock build renders no drag attributes and keeps text selectable', async ({ page }) => {
  await open(page);
  await expect(page.locator('[data-tauri-drag-region]')).toHaveCount(0);
  await expect(page.locator('.titlebar')).toHaveCount(0);
  expect(await userSelect(page.getByRole('heading', { level: 1 }))).not.toBe('none');
});

test('the Tauri-mode window has no axe violations', async ({ page }) => {
  await bootTauri(page);
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations.map((v) => `${v.id}: ${v.help}`)).toEqual([]);
});
