import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { expect, test } from '@playwright/test';

test('the capability grants exactly the permissions the bridge uses, and Tauri zoom hotkeys stay off', () => {
  const cap = JSON.parse(readFileSync(resolve(process.cwd(), 'src-tauri/capabilities/default.json'), 'utf8')) as {
    permissions: string[];
  };
  const conf = JSON.parse(readFileSync(resolve(process.cwd(), 'src-tauri/tauri.conf.json'), 'utf8')) as {
    app: { windows: { zoomHotkeysEnabled?: boolean }[] };
  };
  expect(cap.permissions).toEqual([
    'core:default',
    'dialog:allow-open',
    'core:window:allow-start-dragging',
    'core:webview:allow-set-webview-zoom',
  ]);
  expect(conf.app.windows[0]?.zoomHotkeysEnabled).not.toBe(true);
});
