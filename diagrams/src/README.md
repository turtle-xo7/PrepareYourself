# Diagram sources

Every PNG in `diagrams/` is rendered from a hand-crafted HTML/SVG page in this
folder, sharing one design system (`theme.css`) and a small layout engine
(`engine.js`) that draws the connector arrows and sequence lifelines.

## Regenerating

Open any `.html` file in a browser to preview it. To export PNGs, run this
snippet with Playwright (Node or Python — any runner that can screenshot an
element):

```js
// for each diagram page:
await page.goto('file:///…/diagrams/src/<name>.html', { waitUntil: 'networkidle' });
await page.waitForTimeout(900);                      // let fonts + arrows settle
await page.evaluate(() => { document.body.style.zoom = 2; document.body.style.margin = '0'; });
await page.waitForTimeout(600);
const box = await page.locator('#frame').boundingBox();
await page.screenshot({ path: 'diagrams/<name>.png', clip: box });
```

> Use a cache-busting query (`?v=Date.now()`) after editing a page — `file://`
> documents are cached aggressively. `zoom` (not `transform: scale`) is what
> guarantees the 2× raster, because it forces a re-layout.

## Files

| Source | Output |
|--------|--------|
| `dfd_level0.html` | Context diagram |
| `dfd_level1.html` | System overview DFD |
| `dfd_level2_question.html` / `_contest` / `_payment` | Level-2 DFDs |
| `seq_login` / `seq_mcq` / `seq_subscription` / `seq_contest` / `seq_cq_grade` | Sequence diagrams |
| `activity_exam.html` | Exam attempt activity flow |
| `tech_stack.html` | Layered tech stack |
| `gantt_chart.html` | Sprint Gantt |
