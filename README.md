# fore-ladies.com

Static website for **Fore Ladies Golf** — women's golf clothes, golf dresses, tennis apparel, size charts and style guides.
The repository root is the web root. Hostinger deploys `main` to `public_html` with Git auto-deployment.

## How it works

- `_build/content/` — all content as JSON (products, categories, posts, pages, redirects, overrides) plus new articles in `_build/content/new/*.html` (each starts with a `<!--META {...} -->` JSON header).
- `_build/build.py` — generates every page as `<path>.html`, plus `sitemap.xml`, `feed.xml`, `robots.txt`, `.htaccess`, `404.html`, icons and the web manifest. Clean URLs (no `.html`) are served by `.htaccess`.
- `_build/check.py` — broken links and images, one `<h1>`, unique titles and descriptions, canonical tags, JSON-LD, sitemap URLs, and new-article word counts (1,000–1,600). Exit code 1 means something must be fixed.
- `_build/make_card.py` — title-card images for articles (`/img/blog/<slug>.jpg` 1200×630 and `-thumb.jpg` 600×400).
- `_build/profile.md` — brand voice. `_build/entity-map.md` — verified entities for schema.
- `_build/plan/` — content calendar and the autopilot runbook used by scheduled tasks.

```bash
pip install pillow --break-system-packages   # once
python3 _build/build.py
python3 _build/check.py
```

Edit content in `_build/content/`, never the generated `.html` files. Titles/descriptions/noindex can be overridden per URL in `_build/content/overrides.json`. Redirects live in `_build/content/redirects.json` (the build writes them into `.htaccess`, all one hop).

## Rules

- Never change an existing URL or image path. If a URL must go, add a 301 in `redirects.json`.
- Online checkout is not available on this site: no "buy", "in stock", discount codes or invented prices. Prices appear only as "last listed price".
- No invented statistics, reviews, quotes or personal stories. Link real sources.
- This repository is **public**: never commit Search Console numbers, CSV exports or private notes.

## Deploy on Hostinger

1. **Back up first.** hPanel → Websites → fore-ladies.com → File Manager → select everything in `public_html` (including `.htaccess`) → Compress → download the zip. Deploying replaces the files in `public_html`.
2. hPanel → Websites → fore-ladies.com → Advanced → **GIT** → Connect with GitHub → choose `mdminhaj6565/site-fore-ladies.com`, branch `main`, directory `public_html` (leave the path empty if hPanel asks for a sub-folder) → Deploy.
3. Turn **Auto Deployment** on. Every push to `main` then goes live within about a minute.
4. Force HTTPS in hPanel (Security → SSL → Force HTTPS). `.htaccess` handles www → non-www, `.html` → clean URL, trailing slashes and old store URLs.

### বাংলায় সংক্ষেপে

1. **আগে backup নিন:** hPanel → Websites → fore-ladies.com → File Manager → `public_html`-এর সব file (`.htaccess` সহ) select → Compress → zip download। Deploy করলে `public_html`-এর file বদলে যায়।
2. hPanel → Websites → fore-ladies.com → Advanced → **GIT** → Connect with GitHub → repo `mdminhaj6565/site-fore-ladies.com`, branch `main` → Deploy।
3. **Auto Deployment** On করুন — এরপর `main`-এ প্রতিটি push প্রায় ১ মিনিটে live হবে।
4. hPanel-এ Force HTTPS চালু রাখুন। www → non-www, `.html` → clean URL ও পুরোনো store-এর URL-এর redirect `.htaccess` নিজেই করে।
