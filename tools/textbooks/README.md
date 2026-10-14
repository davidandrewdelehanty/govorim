# Soviet textbooks pipeline

How the "Soviet Textbooks" shelf was made from the Telegram scans
(tools/telegram_textbooks.py downloads them).

1. `render_ocr.py <slug> <pdf> 1` — render each page at 200 dpi and OCR it with
   Tesseract (`rus`, tessdata_best) to TSV. Born-digital PDFs and scans with a
   good text layer skip OCR (`layer=True` in books.py).
   `ocr_halves.py` is for two-page spreads at low resolution (Поварнин,
   «Введение в логику»): split, upscale ×2.5, denoise, OCR each half.
2. `extract.py <slug>` — lines → paragraphs (indent / short line / gap),
   headings (size, centring, regex), running heads and page numbers dropped,
   line-break hyphens joined, letter-spaced words rejoined, OCR words below the
   confidence bar corrected against a word list built from the library's own
   FB2s, and illustrations found as ink not covered by text, cropped to WebP
   with their captions.
3. `build_fb2.py <slug>` — FB2 with `<image l:href="textbooks/<slug>/fNNN.webp">`
   beside the text, parts/chapters, `<subtitle>`s, synopses as emphasis, short
   line runs as `<poem data-tight>`; plus `cover.webp`.
4. `pkg.py` — copies into public/books/novel and public/books/textbooks.

Paths inside are those of the working container (/tmp/claude-0/tb); adjust
before re-running.
