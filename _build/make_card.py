#!/usr/bin/env python3
"""Make a title card for an article: /img/blog/<slug>.jpg (1200x630) and /img/blog/<slug>-thumb.jpg (600x400).
Usage: python3 _build/make_card.py <slug> "<title>" ["<kicker>"]
"""
import os, sys, textwrap, hashlib
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, '_build', 'assets-src')
PALETTES = [('#111111', '#e9446e', '#ffffff', '#f3c6d2'), ('#fdf0f3', '#e9446e', '#111111', '#7a3b4d'),
            ('#e9446e', '#111111', '#ffffff', '#ffe3ea'), ('#1f2a2e', '#e9446e', '#ffffff', '#cfe3e0')]

def card(slug, title, kicker='Fore Ladies Golf Blog'):
    out = os.path.join(ROOT, 'img', 'blog'); os.makedirs(out, exist_ok=True)
    bg, acc, fg, sub = PALETTES[int(hashlib.md5(slug.encode()).hexdigest(), 16) % len(PALETTES)]
    for (w, h, name, ts, ks) in ((1200, 630, f'{slug}.jpg', 64, 28), (600, 400, f'{slug}-thumb.jpg', 36, 17)):
        im = Image.new('RGB', (w, h), bg); d = ImageDraw.Draw(im)
        pad = int(w * 0.07)
        # golf-ball dimple pattern on the right
        r = int(h * 0.42); cx, cy = w - int(r * 0.55), int(h * 0.55)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=acc, width=max(2, w // 300))
        for i in range(-4, 5):
            for j in range(-4, 5):
                x, y = cx + i * r // 4.5, cy + j * r // 4.5
                if (x - cx) ** 2 + (y - cy) ** 2 < (r * 0.85) ** 2:
                    s = max(2, w // 220); d.ellipse([x - s, y - s, x + s, y + s], fill=acc)
        fk = ImageFont.truetype(os.path.join(FONTS, 'Poppins-SemiBold.ttf'), ks)
        ft = ImageFont.truetype(os.path.join(FONTS, 'Poppins-Bold.ttf'), ts)
        d.rectangle([pad, pad, pad + int(w * 0.06), pad + max(4, h // 90)], fill=acc)
        d.text((pad, pad + h // 30), kicker.upper(), font=fk, fill=sub)
        maxw = int(w * 0.62)
        words = title.split(); lines = []; cur = ''
        for wd in words:
            t = (cur + ' ' + wd).strip()
            if d.textlength(t, font=ft) <= maxw: cur = t
            else: lines.append(cur); cur = wd
        lines.append(cur)
        y = pad + h // 30 + int(ks * 2.2)
        for ln in lines[:5]:
            d.text((pad, y), ln, font=ft, fill=fg); y += int(ts * 1.18)
        im.save(os.path.join(out, name), quality=84, optimize=True, progressive=True)
    return f'/img/blog/{slug}.jpg', f'/img/blog/{slug}-thumb.jpg'

if __name__ == '__main__':
    print(card(sys.argv[1], sys.argv[2], *(sys.argv[3:4] or [])))
