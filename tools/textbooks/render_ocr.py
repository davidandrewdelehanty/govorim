# usage: render_ocr.py <slug> <pdf> <ocr:0|1>
import sys, os, subprocess, pymupdf
slug, pdf, ocr = sys.argv[1], sys.argv[2], sys.argv[3] == "1"
if slug in ("peshkovsky-pervye-uroki", "mayakovsky-azbuka"): ocr = False
out = f"/tmp/claude-0/tb/pages/{slug}"; os.makedirs(out, exist_ok=True)
d = pymupdf.open(pdf)
for i, pg in enumerate(d, 1):
    jpg = f"{out}/p{i:04d}.jpg"
    if not os.path.exists(jpg):
        pg.get_pixmap(dpi=200).save(jpg, jpg_quality=92)
    if ocr and not os.path.exists(f"{out}/p{i:04d}.tsv"):
        png = f"{out}/_g{i:04d}.png"
        pg.get_pixmap(dpi=300, colorspace=pymupdf.csGRAY).save(png)
        subprocess.run(["tesseract", png, f"{out}/p{i:04d}", "-l", "rus", "--psm", "3", "tsv"],
                       env=dict(os.environ, OMP_THREAD_LIMIT="1", TESSDATA_PREFIX="/tmp/claude-0/tess"),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(png)
    print(slug, i, len(d), flush=True)
