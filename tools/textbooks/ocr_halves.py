# usage: ocr_halves.py <slug> <pdf> [first last]   — spreads: split, upscale, denoise, OCR each half
import sys, os, subprocess, pymupdf, cv2, numpy as np
slug, pdf = sys.argv[1], sys.argv[2]
out = f"/tmp/claude-0/tb/pages/{slug}"; os.makedirs(out, exist_ok=True)
d = pymupdf.open(pdf)
env = dict(os.environ, TESSDATA_PREFIX="/tmp/claude-0/tess", OMP_THREAD_LIMIT="1")
k = 0
jobs = []
for i, pg in enumerate(d, 1):
    imgs = pg.get_images()
    x = d.extract_image(imgs[0][0])
    im = cv2.imdecode(np.frombuffer(x["image"], np.uint8), cv2.IMREAD_COLOR)
    h, w = im.shape[:2]
    for half in (im[:, :w // 2], im[:, w // 2:]):
        k += 1
        up = cv2.resize(half, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        g = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
        g = cv2.fastNlMeansDenoising(g, None, 15, 7, 21)
        cv2.imwrite(f"{out}/p{k:04d}.jpg", up, [cv2.IMWRITE_JPEG_QUALITY, 90])
        cv2.imwrite(f"{out}/_g{k:04d}.png", g)
        jobs.append(k)
procs = []
for k in jobs:
    if os.path.exists(f"{out}/p{k:04d}.tsv"): continue
    p = subprocess.Popen(["tesseract", f"{out}/_g{k:04d}.png", f"{out}/p{k:04d}", "-l", "rus", "--psm", "6", "tsv"], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    procs.append(p)
    if len(procs) >= 2:
        procs.pop(0).wait()
    print(k, flush=True)
for p in procs: p.wait()
for k in jobs:
    try: os.remove(f"{out}/_g{k:04d}.png")
    except OSError: pass
print("done", k)
