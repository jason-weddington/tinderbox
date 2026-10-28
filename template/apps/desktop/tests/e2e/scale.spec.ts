import { expect, test } from './fixtures';
import { open } from './helpers';

// The root scale is 120% of the browser default: 1rem is 19.2px, and what the
// app drew at 14px body text before is the 100% size now (16.8px).

test('text and the band render on the 120% root scale', async ({ page }) => {
  await open(page);
  const size = (selector: string) =>
    page.evaluate((s) => parseFloat(getComputedStyle(document.querySelector(s) as Element).fontSize), selector);
  expect(await size('html')).toBeCloseTo(19.2, 2);
  expect(await size('body')).toBeCloseTo(16.8, 2);
  expect(await size('h1')).toBeCloseTo(18, 2);
  const band = await page.locator('.band').evaluate((el) => el.getBoundingClientRect().height);
  expect(band).toBeCloseTo(62.4, 1);
});
