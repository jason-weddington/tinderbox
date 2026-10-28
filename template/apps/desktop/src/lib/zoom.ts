// Pure zoom rules for the Mac app: the steps, the keys, and the stored value.
// bridge.ts applies them to the webview; nothing here touches Tauri.

export const ZOOM_STEPS: readonly number[] = [0.5, 0.67, 0.75, 0.8, 0.9, 1, 1.1, 1.25, 1.5, 1.75, 2];

export const ZOOM_KEY = 'emberly.zoom';

export type ZoomAction = 'in' | 'out' | 'reset';

/** The zoom a Cmd key chord asks for, or null when it is not one. Shift is ignored. */
export function zoomAction(e: Pick<KeyboardEvent, 'key' | 'metaKey' | 'ctrlKey' | 'altKey'>): ZoomAction | null {
  if (!e.metaKey || e.ctrlKey || e.altKey) return null;
  if (e.key === '=' || e.key === '+') return 'in';
  if (e.key === '-') return 'out';
  if (e.key === '0') return 'reset';
  return null;
}

export function nextZoom(current: number, action: ZoomAction): number {
  if (action === 'reset') return 1;
  if (action === 'in') return ZOOM_STEPS.find((s) => s > current) ?? 2;
  return [...ZOOM_STEPS].reverse().find((s) => s < current) ?? 0.5;
}

/** A stored level back to a number; anything that is not a step fails closed to 100%. */
export function parseZoom(stored: string | null): number {
  if (stored === null || stored === '') return 1;
  const n = Number(stored);
  return ZOOM_STEPS.includes(n) ? n : 1;
}
