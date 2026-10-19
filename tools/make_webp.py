"""Make a smaller .webp copy of every .jpg in static/img (needs Pillow).

The site uses the .webp automatically when one exists next to the .jpg;
photos without one (for example new uploads from Pages CMS) still work as .jpg.
Run: python3 tools/make_webp.py
"""
import glob, os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for jpg in sorted(glob.glob(os.path.join(ROOT, "static", "img", "*.jp*g"))):
    webp = os.path.splitext(jpg)[0] + ".webp"
    if os.path.exists(webp) and os.path.getmtime(webp) >= os.path.getmtime(jpg):
        continue
    Image.open(jpg).convert("RGB").save(webp, "WEBP", quality=80, method=6)
    print(f"{os.path.basename(webp)}: {os.path.getsize(jpg)//1024} KB -> {os.path.getsize(webp)//1024} KB")
