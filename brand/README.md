# brand/

Static shell assets that differ between the two deployments.

`public/` holds the Говорим versions, which vite copies straight into `dist/`.
For a public build, `scripts/brand.mjs` copies the matching file out of
`brand/samovar/` over the top of it — after vite has finished, against `dist/`
only, so the working tree is never touched and the private build never sees
these files at all.

The letter is the only difference: Г for Говорим, С for Самовар, same serif,
same #c8a276 on #1a1611.

- `favicon.svg`          — browser tab, and the Android "Add to Home screen"
                           icon (the web manifest points at it)
- `apple-touch-icon.png` — the iOS "Add to Home Screen" icon, 180×180
