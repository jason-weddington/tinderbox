import { expect, test } from '@playwright/test';

import { ZOOM_STEPS, nextZoom, parseZoom, zoomAction } from '../../src/lib/zoom';

test('nextZoom steps through the table and clamps', () => {
  const cases: [number, 'in' | 'out' | 'reset', number][] = [
    [1, 'in', 1.1],
    [1.1, 'in', 1.25],
    [2, 'in', 2],
    [3, 'in', 2],
    [1.2, 'in', 1.25],
    [1, 'out', 0.9],
    [0.5, 'out', 0.5],
    [0.3, 'out', 0.5],
    [1.2, 'out', 1.1],
    [1.75, 'reset', 1],
  ];
  for (const [cur, action, want] of cases) expect(nextZoom(cur, action), `${cur} ${action}`).toBe(want);
});

test('zoomAction needs Cmd alone', () => {
  const k = (key: string, metaKey: boolean, ctrlKey: boolean, altKey: boolean) => ({ key, metaKey, ctrlKey, altKey });
  expect(zoomAction(k('=', true, false, false))).toBe('in');
  expect(zoomAction(k('+', true, false, false))).toBe('in');
  expect(zoomAction(k('-', true, false, false))).toBe('out');
  expect(zoomAction(k('0', true, false, false))).toBe('reset');
  expect(zoomAction(k('=', false, false, false))).toBeNull();
  expect(zoomAction(k('=', true, true, false))).toBeNull();
  expect(zoomAction(k('=', true, false, true))).toBeNull();
  expect(zoomAction(k('a', true, false, false))).toBeNull();
});

test('parseZoom fails closed', () => {
  expect(parseZoom('1.25')).toBe(1.25);
  expect(parseZoom('0.67')).toBe(0.67);
  for (const bad of [null, '', 'abc', '3', '1.2', '0.4']) expect(parseZoom(bad), String(bad)).toBe(1);
  for (const s of ZOOM_STEPS) expect(parseZoom(String(s))).toBe(s);
});
