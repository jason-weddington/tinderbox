import { expect, test } from './fixtures';

import { open } from './helpers';

// bridge.ts's zoom against a stubbed Tauri: the webview set-zoom command is
// the only call, and the stored level is what comes back at the next launch.

interface Run {
  log: { command: string; args: Record<string, unknown> | undefined }[];
  warns: unknown[][];
  steps: { stored: string | null; prevented: boolean }[];
  extra: number[];
}

type Scenario = 'happy' | 'uninstall' | 'reject' | 'badstored' | 'gate';

async function run(page: import('@playwright/test').Page, scenario: Scenario): Promise<Run> {
  return page.evaluate(async (sc) => {
    const w = window as unknown as { __TAURI_INTERNALS__?: unknown };
    const log: Run['log'] = [];
    const warns: unknown[][] = [];
    const steps: Run['steps'] = [];
    const extra: number[] = [];
    const reject = sc === 'reject';
    w.__TAURI_INTERNALS__ = {
      invoke: (command: string, args?: Record<string, unknown>) => {
        log.push({ command, args });
        return reject ? Promise.reject(new Error('denied')) : Promise.resolve(null);
      },
      metadata: { currentWindow: { label: 'main' }, currentWebview: { label: 'main' } },
    };
    const realWarn = console.warn;
    console.warn = (...a: unknown[]) => {
      warns.push(a);
    };
    const stored: Partial<Record<Scenario, string>> = { happy: '1.25', uninstall: '1', badstored: '1.2' };
    localStorage.removeItem('emberly.zoom');
    const s = stored[sc];
    if (s !== undefined) localStorage.setItem('emberly.zoom', s);
    const uninstalls: (() => void)[] = [];
    try {
      const url = '/src/lib/bridge.ts';
      const bridge = (await import(/* @vite-ignore */ url)) as {
        installTauriZoom: () => () => void;
        installZoom: (tauri: boolean) => () => void;
      };
      const press = async (init: KeyboardEventInit): Promise<void> => {
        const ev = new KeyboardEvent('keydown', { ...init, cancelable: true });
        window.dispatchEvent(ev);
        await new Promise((r) => setTimeout(r, 0));
        steps.push({ stored: localStorage.getItem('emberly.zoom'), prevented: ev.defaultPrevented });
      };
      if (sc === 'gate') {
        uninstalls.push(bridge.installZoom(true));
        extra.push(log.length);
        uninstalls.push(bridge.installZoom(false));
        uninstalls.push(bridge.installZoom(false));
        extra.push(log.length);
        extra.push(localStorage.getItem('emberly.zoom') === null ? 1 : 0);
      } else {
        const un = bridge.installTauriZoom();
        uninstalls.push(un);
        if (sc === 'uninstall') un();
        if (sc === 'happy') {
          await press({ key: '=', metaKey: true });
          await press({ key: '-', metaKey: true });
          await press({ key: '0', metaKey: true });
          await press({ key: '=', metaKey: false });
        } else {
          await press({ key: '=', metaKey: true });
        }
      }
    } finally {
      for (const u of uninstalls) u();
      console.warn = realWarn;
      delete w.__TAURI_INTERNALS__;
      localStorage.removeItem('emberly.zoom');
    }
    return { log, warns, steps, extra };
  }, scenario);
}

const SET = 'plugin:webview|set_webview_zoom';

test.describe('zoom through the bridge', () => {
  test('keys step the webview zoom and persist it', async ({ page }) => {
    await open(page);
    const r = await run(page, 'happy');
    expect(r.log.every((c) => c.command === SET)).toBe(true);
    expect(r.log.map((c) => c.args)).toEqual([
      { label: 'main', value: 1.25 },
      { label: 'main', value: 1.5 },
      { label: 'main', value: 1.25 },
      { label: 'main', value: 1 },
    ]);
    expect(r.steps.map((s) => s.stored)).toEqual(['1.5', '1.25', '1', '1']);
    expect(r.steps.map((s) => s.prevented)).toEqual([true, true, true, false]);
  });

  test('uninstall removes the listener', async ({ page }) => {
    await open(page);
    const r = await run(page, 'uninstall');
    expect(r.log).toHaveLength(1);
    expect(r.steps[0]?.stored).toBe('1');
  });

  test('a rejected set-zoom is logged, not thrown', async ({ page }) => {
    const errors: Error[] = [];
    page.on('pageerror', (e) => errors.push(e));
    await open(page);
    const r = await run(page, 'reject');
    expect(r.warns).toEqual([
      ['[emberly/zoom]', { kind: 'set_zoom_failed', phase: 'install', level: 1, error: 'Error: denied' }],
      ['[emberly/zoom]', { kind: 'set_zoom_failed', phase: 'key', level: 1.1, error: 'Error: denied' }],
    ]);
    expect(errors).toEqual([]);
  });

  test('an unknown stored level is rejected with a warning', async ({ page }) => {
    await open(page);
    const r = await run(page, 'badstored');
    expect(r.warns).toContainEqual(['[emberly/zoom]', { kind: 'stored_zoom_rejected', stored: '1.2' }]);
    expect(r.log[0]?.args).toEqual({ label: 'main', value: 1 });
  });

  test('only tauri mode installs zoom', async ({ page }) => {
    await open(page);
    const r = await run(page, 'gate');
    expect(r.extra).toEqual([1, 1, 1]);
  });

  test('the stub is gone afterwards: the page is back on the mock', async ({ page }) => {
    await open(page);
    await expect(page.locator('html')).toHaveAttribute('data-bridge', 'mock');
    expect(await page.evaluate(() => '__TAURI_INTERNALS__' in window)).toBe(false);
  });

  test('the mock app does not zoom', async ({ page }) => {
    await open(page);
    await page.keyboard.press('Meta+Equal');
    await page.keyboard.press('Meta+Minus');
    expect(await page.evaluate(() => localStorage.getItem('emberly.zoom'))).toBeNull();
  });
});
