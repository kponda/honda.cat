#!/usr/bin/env python3
"""
scripts/generate_favicons.py
Generate crisp, high-visibility, solid-color (ベタ塗り) favicons and web icons for honda.cat.

Design:
- Background: Honda Racing Red (#e63946) squircle (rx ~22%)
- Foreground: Solid white (#ffffff) cat head silhouette with distinct upright ears,
              gentle forehead dip, and cute rounded cheeks.
- Output formats:
  - public/favicon.svg (Scalable vector icon)
  - public/favicon.ico (Multi-size 16x16, 32x32, 48x48)
  - public/favicon-32x32.png
  - public/favicon-16x16.png
  - public/apple-touch-icon.png (180x180)
  - public/icon-192.png (192x192)
  - public/icon-512.png (512x512)
  - public/site.webmanifest
"""

import os
import json
import numpy as np
from PIL import Image, ImageDraw

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC_DIR = os.path.join(PROJECT_ROOT, "public")

# SVG representation
SVG_CONTENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <!-- Honda Racing Red squircle background for high contrast & visibility on both light and dark themes -->
  <rect width="512" height="512" rx="112" fill="#e63946"/>
  <!-- Crisp, solid-white cat head silhouette -->
  <path d="M 256 175
           C 220 175 185 142 142 90
           C 135 82 125 87 122 98
           C 115 140 110 180 106 215
           C 78 255 78 315 110 365
           C 140 415 195 426 256 426
           C 317 426 372 415 402 365
           C 434 315 434 255 406 215
           C 402 180 397 140 390 98
           C 387 87 377 82 370 90
           C 327 142 292 175 256 175 Z"
        fill="#ffffff"/>
</svg>
"""

def bezier_cubic(p0, p1, p2, p3, n_points=60):
    t = np.linspace(0, 1, n_points)[:, None]
    return ((1 - t)**3 * p0 + 3 * (1 - t)**2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3).tolist()

def get_cat_polygon_points():
    curves = [
        # Top forehead center to left ear inner
        ([256, 175], [220, 175], [185, 142], [142, 90]),
        # Left ear tip rounded turn
        ([142, 90], [135, 82], [125, 87], [122, 98]),
        # Left ear outer edge to upper cheek
        ([122, 98], [115, 140], [110, 180], [106, 215]),
        # Left cheek flare and roundness
        ([106, 215], [78, 255], [78, 315], [110, 365]),
        # Left cheek to bottom chin
        ([110, 365], [140, 415], [195, 426], [256, 426]),
        # Symmetrical right side:
        # Chin to right cheek
        ([256, 426], [317, 426], [372, 415], [402, 365]),
        # Right cheek
        ([402, 365], [434, 315], [434, 255], [406, 215]),
        # Right cheek to outer ear edge
        ([406, 215], [402, 180], [397, 140], [390, 98]),
        # Right ear tip rounded turn
        ([390, 98], [387, 87], [377, 82], [370, 90]),
        # Right ear inner edge to forehead center
        ([370, 90], [327, 142], [292, 175], [256, 175]),
    ]
    points = []
    for p0, p1, p2, p3 in curves:
        pts = bezier_cubic(np.array(p0), np.array(p1), np.array(p2), np.array(p3), 60)
        points.extend(pts[:-1])
    return points

def render_master_image(canvas_size=2048):
    scale = canvas_size / 512.0
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Squircle radius: ~22%
    radius = int(canvas_size * (112.0 / 512.0))
    bg_color = (230, 57, 70, 255) # #E63946
    draw.rounded_rectangle([0, 0, canvas_size, canvas_size], radius=radius, fill=bg_color)

    # Cat silhouette polygon
    points = get_cat_polygon_points()
    scaled_poly = [(p[0] * scale, p[1] * scale) for p in points]
    draw.polygon(scaled_poly, fill=(255, 255, 255, 255))

    return img

def main():
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    # 1. Write SVG
    svg_path = os.path.join(PUBLIC_DIR, "favicon.svg")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(SVG_CONTENT)
    print(f"✓ Created {svg_path}")

    # 2. Render high-res master image (2048x2048)
    master = render_master_image(2048)

    # 3. Generate PNGs
    sizes = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "apple-touch-icon.png": 180,
        "icon-192.png": 192,
        "icon-512.png": 512,
    }

    generated_images = {}
    for filename, size in sizes.items():
        out_img = master.resize((size, size), Image.Resampling.LANCZOS)
        out_path = os.path.join(PUBLIC_DIR, filename)
        out_img.save(out_path, format="PNG")
        generated_images[size] = out_img
        print(f"✓ Created {out_path} ({size}x{size})")

    # 4. Generate multi-resolution ICO (16x16, 32x32, 48x48)
    ico_img_48 = master.resize((48, 48), Image.Resampling.LANCZOS)
    ico_path = os.path.join(PUBLIC_DIR, "favicon.ico")
    master.save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)]
    )
    print(f"✓ Created {ico_path} (contains 16x16, 32x32, 48x48)")

    # 5. Write site.webmanifest
    manifest_data = {
        "name": "HONDA.CAT",
        "short_name": "HONDA.CAT",
        "description": "二足歩行の猫編集部が届ける3言語二輪レース＆草耐久情報サイト",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0d0f14",
        "theme_color": "#e63946",
        "icons": [
            {
                "src": "/favicon-32x32.png",
                "sizes": "32x32",
                "type": "image/png"
            },
            {
                "src": "/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
    manifest_path = os.path.join(PUBLIC_DIR, "site.webmanifest")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)
    print(f"✓ Created {manifest_path}")

    print("\nAll favicon assets generated successfully!")

if __name__ == "__main__":
    main()
