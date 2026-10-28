import { expect, type Locator, type Page } from '@playwright/test';

/** Loads the app against the mock with these URL parameters (see src/lib/mock.ts). */
export async function open(page: Page, params: Record<string, string> = {}): Promise<void> {
  await page.goto(`/?${new URLSearchParams(params).toString()}`);
  await expect(page.locator('html')).toHaveAttribute('data-bridge', 'mock');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
}

export function chooseButton(page: Page): Locator {
  return page.getByRole('button', { name: /^Choose (another )?folder…$/ });
}

/** Makes the mock's next calls of `command` wait until `release`. */
export async function hold(page: Page, command: string): Promise<void> {
  await page.evaluate((c) => {
    window.__mockBridge?.hold(c);
  }, command);
}

export async function release(page: Page, command: string): Promise<void> {
  await page.evaluate((c) => {
    window.__mockBridge?.release(c);
  }, command);
}

/** Every path the UI asked the mock to scan. */
export async function scans(page: Page): Promise<string[]> {
  return page.evaluate(() => [...(window.__mockBridge?.scans ?? [])]);
}

/**
 * Every item of a list that overflows its container can be scrolled into view,
 * and none is squeezed below its content height (docs/tauri-design-notes.md,
 * "Layout that survives real data"). Use it on every list.
 */
export async function expectEveryItemReachable(items: Locator): Promise<void> {
  const n = await items.count();
  expect(n, 'the fixture must overflow the container').toBeGreaterThan(10);
  for (const i of [0, n - 1]) {
    const item = items.nth(i);
    await item.scrollIntoViewIfNeeded();
    // 0.9, not 1: sub-pixel heights leave a fully scrolled item a fraction short.
    await expect(item).toBeInViewport({ ratio: 0.9 });
  }
  const squeezed = await items.evaluateAll((els) => els.filter((e) => e.scrollHeight > e.clientHeight + 1).length);
  expect(squeezed, 'items squeezed below their content height').toBe(0);
}

// ---- the Tauri build, stubbed -------------------------------------------------------

// Tauri injects a drag script that decides from the mousedown target's ancestry.
// These rules are a vendored copy of it (tauri 2.12.4, src/window/scripts/drag.js),
// so the tests assert what that script would do. window-drag.spec.ts has the
// version tripwire that flags a Tauri upgrade.
const DRAG_RULES = `
const CLICKABLE_TAGS = new Set(['A','BUTTON','INPUT','SELECT','TEXTAREA','LABEL','SUMMARY']);
const INTERACTIVE_ROLES = new Set(['button','link','menuitem','tab','checkbox','radio','switch','option']);
function isClickableElement(el){return CLICKABLE_TAGS.has(el.tagName)||(el.hasAttribute('contenteditable')&&el.getAttribute('contenteditable')!=='false')||(el.hasAttribute('tabindex')&&el.getAttribute('tabindex')!=='-1')||INTERACTIVE_ROLES.has(el.getAttribute('role'))}
function isDragRegion(path){for(const el of path){if(!(el instanceof HTMLElement))continue;const attr=el.getAttribute('data-tauri-drag-region');if(isClickableElement(el)&&attr===null)return false;if(attr===null)continue;if(attr==='false')return false;if(attr==='deep')return true;if(attr===''||attr==='true')return el===path[0]}return false}
`;

/** Whether Tauri's drag script would start a window drag from a press at (x, y). */
export async function dragsAt(page: Page, x: number, y: number): Promise<boolean> {
  const script = `(() => {
    ${DRAG_RULES}
    let el = document.elementFromPoint(${String(x)}, ${String(y)});
    const path = [];
    while (el !== null) { path.push(el); el = el.parentElement; }
    return isDragRegion(path);
  })()`;
  return page.evaluate<boolean>(script);
}

export async function hitClass(page: Page, x: number, y: number): Promise<string> {
  return page.evaluate(([px, py]) => document.elementFromPoint(px, py)?.className.toString() ?? '', [x, y] as const);
}

export async function hitTag(page: Page, x: number, y: number): Promise<string> {
  return page.evaluate(([px, py]) => document.elementFromPoint(px, py)?.tagName.toLowerCase() ?? '', [x, y] as const);
}

export async function centre(target: Locator): Promise<[number, number]> {
  const box = await target.boundingBox();
  if (box === null) throw new Error('no bounding box');
  return [box.x + box.width / 2, box.y + box.height / 2];
}

export async function userSelect(target: Locator): Promise<string> {
  return target.evaluate((el) => getComputedStyle(el).userSelect);
}

/** Loads the app as the Tauri webview would see it: a stubbed __TAURI_INTERNALS__, no mock. */
export async function bootTauri(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const w = window as unknown as { __TAURI_INTERNALS__: unknown };
    w.__TAURI_INTERNALS__ = {
      metadata: { currentWindow: { label: 'main' }, currentWebview: { windowLabel: 'main', label: 'main' } },
      transformCallback: () => 1,
      unregisterCallback: () => undefined,
      invoke: (cmd: string) => Promise.resolve(cmd === 'app_info' ? { version: '0.1.0' } : null),
    };
  });
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-bridge', 'tauri');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
}
