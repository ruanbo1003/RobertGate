#!/usr/bin/env python3
"""
扫描照片目录，生成 photos.json 清单文件。
每次有新照片上传后运行一次即可。

用法：python3 gen-photos.py [照片目录]
默认目录：/home/ubuntu/photos
"""

import json
import sys
from pathlib import Path

from PIL import Image

PHOTO_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/ubuntu/photos")
SUPPORTED = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def main():
    if not PHOTO_DIR.is_dir():
        print(f"Error: {PHOTO_DIR} is not a directory")
        sys.exit(1)

    files = sorted(
        [f for f in PHOTO_DIR.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    photos = []
    for f in files:
        try:
            with Image.open(f) as img:
                w, h = img.size
        except Exception:
            w, h = 0, 0

        photos.append({
            "filename": f.name,
            "url": f"/photos/{f.name}",
            "width": w,
            "height": h,
        })

    output = PHOTO_DIR / "photos.json"
    output.write_text(json.dumps({"photos": photos, "total": len(photos)}, ensure_ascii=False))
    print(f"Generated {output} with {len(photos)} photos")


if __name__ == "__main__":
    main()
