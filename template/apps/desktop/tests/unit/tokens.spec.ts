import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

import { expect, test } from '@playwright/test';

// The sizing rules in app.css: the root scale is 120%, every length is rem so
// the whole UI scales together, and px survives only for hairlines. A px
// literal that creeps back in would not scale with the rest.

const ROOT = process.cwd();
const CSS = readFileSync(resolve(ROOT, 'src/app.css'), 'utf8');

function svelteFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return svelteFiles(path);
    return path.endsWith('.svelte') ? [path] : [];
  });
}

const HAIRLINES = new Set([
  'border',
  'border-top',
  'border-right',
  'border-bottom',
  'border-left',
  'border-width',
  'border-top-width',
  'border-right-width',
  'border-bottom-width',
  'border-left-width',
  'outline',
  'outline-width',
  'outline-offset',
  'box-shadow',
]);

function pxViolations(css: string): string[] {
  const bad: string[] = [];
  for (const m of css.replace(/\/\*[\s\S]*?\*\//g, '').matchAll(/([a-z-]+)\s*:\s*([^;{}]*)/g)) {
    const [decl = '', prop = '', value = ''] = m;
    if (/\d*\.?\d+px\b/.test(value) && !HAIRLINES.has(prop)) bad.push(decl.trim());
  }
  return bad;
}

test('no length is a px literal outside hairlines', () => {
  expect(pxViolations('border-radius: 3px')).toHaveLength(1);
  expect(pxViolations('font-size: 14px')).toHaveLength(1);
  expect(pxViolations('border: 1px solid var(--line)')).toEqual([]);
  expect(pxViolations('/* 19.2px in a comment */ margin: 1rem')).toEqual([]);
  expect(pxViolations(CSS), 'src/app.css').toEqual([]);
  for (const file of svelteFiles(resolve(ROOT, 'src'))) {
    const blocks = [...readFileSync(file, 'utf8').matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)].map((m) => m[1] ?? '');
    expect(pxViolations(blocks.join('\n')), file).toEqual([]);
  }
});

test('svg icons are sized in CSS, not attributes', () => {
  for (const file of svelteFiles(resolve(ROOT, 'src'))) {
    const code = readFileSync(file, 'utf8').replace(/<!--[\s\S]*?-->/g, '');
    expect(code, file).not.toMatch(/<svg\b[^>]*\s(width|height)=/);
  }
});

test('the root scale is 120%', () => {
  expect(CSS.replace(/\/\*[\s\S]*?\*\//g, '')).toMatch(/(^|\})\s*html\s*\{[^}]*font-size:\s*120%/);
});
