#!/usr/bin/env python3
"""Static site generator for fore-ladies.com.

Content lives in _build/content/. Run from anywhere:  python3 _build/build.py
Output is written to the repository root (the web root). Every page is written as
<path>.html and served at the clean URL <path> by .htaccess.
"""
import json, os, re, html, glob, datetime as dt, shutil, hashlib, collections
from xml.sax.saxutils import escape as xesc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, '_build')
C = os.path.join(B, 'content')
TODAY = dt.date.today()
TODAY_S = TODAY.isoformat()

def load(name, default=None):
    p = os.path.join(C, name)
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else default

SITE = load('site.json')
PRODUCTS = load('products.json')
CATS = load('categories.json')
POSTS = load('posts.json')
PAGES = load('pages.json')
REDIR = load('redirects.json')
TESTI = load('testimonials.json', [])
OVR = load('overrides.json', {})
URL = SITE['url']
E = lambda s: html.escape(s or '', quote=True)

# ------------------------------------------------------------------ new articles
def read_new_articles():
    arts = {}
    for f in sorted(glob.glob(os.path.join(C, 'new', '*.html'))):
        raw = open(f, encoding='utf-8').read()
        m = re.match(r'\s*<!--META\s*(\{.*?\})\s*-->\s*(.*)$', raw, re.S)
        if not m: raise SystemExit(f'missing META header: {f}')
        meta = json.loads(m.group(1)); body = m.group(2).strip()
        path = '/blog/' + meta['slug']
        meta.update({'path': path, 'body_html': body, 'new': True, 'file': os.path.basename(f)})
        meta.setdefault('author', 'Fore Ladies Golf team')
        arts[path] = meta
    return arts
NEW = read_new_articles()
ALLPOSTS = dict(POSTS); ALLPOSTS.update(NEW)

def text_of(h):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h or ''))).strip()
def wcount(h): return len(text_of(h).split())

def trim(s, n):
    s = re.sub(r'\s+', ' ', s or '').strip()
    if len(s) <= n: return s
    cut = s[:n - 1]
    cut = cut[:cut.rfind(' ')] if ' ' in cut else cut
    return cut.rstrip(' ,;:-—') + '…'

def first_sentences(h, n=155):
    t = text_of(h)
    out = ''
    for s in re.split(r'(?<=[.!?])\s+', t):
        if len(out) + len(s) + 1 > n: break
        out = (out + ' ' + s).strip()
    return out or trim(t, n)

# ------------------------------------------------------------------ indexing rules
def product_indexable(p):
    o = OVR.get(p['path'], {})
    if 'index' in o: return o['index']
    if p['path'] in PDUP: return False
    return bool(p.get('img')) or wcount(p.get('desc_html')) >= 30
def cat_indexable(c):
    o = OVR.get(c['path'], {})
    if 'index' in o: return o['index']
    n = len(live_products(c)); w = wcount(c.get('desc_html'))
    if n == 0: return w >= 150
    if n <= 2: return w >= 60
    return True
def live_products(c):
    return [PRODUCTS[x] for x in c.get('products', []) if x in PRODUCTS]

# ------------------------------------------------------------------ titles/descriptions
def title_for(path, default):
    t = OVR.get(path, {}).get('title') or default
    return trim(t, 60)
def desc_for(path, default):
    return trim(OVR.get(path, {}).get('description') or default, 160)

PT, PD, PDUP = {}, {}, set()
def norm_name(n):
    n = re.sub(r'\s*-?\s*final sale\s*', ' ', n, flags=re.I)
    n = re.sub(r'\s*-?\s*(size\s*)?\b(xxs|xs|s|m|l|xl|xxl|\d{1,2}(\.5)?)\s*$', '', n, flags=re.I)
    return re.sub(r'\W+', ' ', n).strip().lower()
def prepare_products():
    """Unique titles/descriptions; exact duplicate listings (same item, same text) get noindex on all but one."""
    groups = collections.defaultdict(list)
    for p in PRODUCTS.values():
        groups[(norm_name(p['name']), text_of(p.get('desc_html'))[:300])].append(p)
    for g in groups.values():
        if len(g) > 1:
            g.sort(key=lambda p: (0 if p.get('img') else 1, 1 if p.get('final_sale') else 0, len(p['path'])))
            for p in g[1:]: PDUP.add(p['path'])
    for p in PRODUCTS.values():
        PT[p['path']] = product_title_raw(p); PD[p['path']] = product_desc_raw(p)
    for store in (PT, PD):
        seen = collections.defaultdict(list)
        for k, v in store.items(): seen[v].append(k)
        for v, ks in seen.items():
            if len(ks) < 2: continue
            for k in ks:
                pr = PRODUCTS[k]
                extra = ' (final sale)' if pr.get('final_sale') else ''
                m = re.search(r'(size-[\d-]+|-(xxs|xs|s|m|l|xl|xxl))$', k)
                if m: extra += ' – size ' + m.group(0).replace('size-', '').strip('-').replace('-', '.').upper()
                if not extra: extra = ' – ' + k.rsplit('/', 1)[-1].split('-')[-1]
                if store is PT:
                    base = re.sub(r'\s*\|\s*Fore Ladies$', '', v)
                    store[k] = trim(base, 60 - len(extra)) + extra
                else:
                    store[k] = trim(v, 160 - len(extra)) + extra

def product_title(p): return PT.get(p['path']) or product_title_raw(p)
def product_desc(p): return PD.get(p['path']) or product_desc_raw(p)

def product_title_raw(p):
    base = re.sub(r'\s*-\s*Final Sale\s*$', '', p['name'], flags=re.I)
    t = f"{base} | Fore Ladies"
    return title_for(p['path'], t if len(t) <= 60 else base)
def product_desc_raw(p):
    lead = first_sentences(p.get('desc_html'), 110)
    extra = f" Sizes: {', '.join(p['sizes'][:6])}." if p.get('sizes') else ''
    d = (f"{p['name']}: {lead}{extra}").strip() if lead else f"{p['name']} from {p.get('brand') or 'Fore Ladies'} — women's golf apparel details, sizing and similar styles."
    return desc_for(p['path'], d)
def cat_title(c):
    old = c.get('old_title') or ''
    if old and '|' in old and 'Fore Ladies' not in old and len(old) >= 30: t = old
    elif c['kind'] == 'brand': t = f"{c['name']} Women's Golf Apparel | Fore Ladies"
    else: t = f"{c['name']} | Women's Golf | Fore Ladies"
    if len(t) > 60: t = f"{c['name']} | Fore Ladies Golf"
    return title_for(c['path'], t)
def cat_desc(c):
    old = c.get('old_desc') or ''
    if old and 'woman-owned boutique' not in old and len(old) > 60: d = old
    elif wcount(c.get('desc_html')) > 25: d = first_sentences(c['desc_html'], 155)
    else:
        n = len(live_products(c))
        d = f"{c['name']} at Fore Ladies Golf: {n} women's golf styles with sizing details, photos where available, and links to fit guides."
    return desc_for(c['path'], d)

# ------------------------------------------------------------------ html helpers
CSS_V = ''; JS_V = ''
def asset_versions():
    global CSS_V, JS_V
    CSS_V = hashlib.md5(open(os.path.join(ROOT, 'assets', 'site.css'), 'rb').read()).hexdigest()[:8]
    JS_V = hashlib.md5(open(os.path.join(ROOT, 'assets', 'site.js'), 'rb').read()).hexdigest()[:8]

def ld(obj): return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '</script>'

ORG = {"@type": "Organization", "@id": URL + "/#org", "name": SITE['name'], "url": URL + "/",
       "logo": {"@type": "ImageObject", "url": URL + SITE['logo'], "width": SITE['logo_w'], "height": SITE['logo_h']},
       "foundingDate": SITE['founded']}

def breadcrumb_ld(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": URL + (h if h != '/' else '/')} for i, (n, h) in enumerate(items)]}

def crumbs_html(items):
    parts = []
    for i, (n, h) in enumerate(items):
        if i == len(items) - 1: parts.append(f'<li aria-current="page">{E(n)}</li>')
        else: parts.append(f'<li><a href="{h}">{E(n)}</a></li>')
    return '<nav class="crumbs" aria-label="Breadcrumb"><ol>' + ''.join(parts) + '</ol></nav>'

def nav_html():
    out = []
    for item in SITE['nav']:
        if item.get('children'):
            sub = ''.join(f'<li><a href="{c["href"]}">{E(c["label"])}</a></li>' for c in item['children'])
            out.append(f'<li class="has-sub"><a href="{item["href"]}">{E(item["label"])}</a><ul class="sub">{sub}</ul></li>')
        else:
            out.append(f'<li><a href="{item["href"]}">{E(item["label"])}</a></li>')
    return '<ul class="nav-list">' + ''.join(out) + '</ul>'
NAV = None

def footer_html():
    y = TODAY.year
    return f'''<footer class="site-footer"><div class="wrap foot-grid">
<div><p class="foot-brand">Fore Ladies Golf</p><p>{E(SITE["announcement"])}. Women's golf clothes, golf dresses and tennis apparel chosen by women who play.</p></div>
<div><p class="foot-h">Shop the catalog</p><ul><li><a href="/womens-golf-clothes">Golf Apparel</a></li><li><a href="/golf-dresses">Golf Dresses</a></li><li><a href="/bottoms/skorts">Skorts</a></li><li><a href="/tennis-clothes-women">Tennis Apparel</a></li><li><a href="/golf-gifts-for-women">Golf Gifts for Women</a></li></ul></div>
<div><p class="foot-h">Help</p><ul><li><a href="/womens-golf-clothes-size-charts">Size Charts &amp; Fit Guide</a></li><li><a href="/shipping-returns">Shipping &amp; Returns</a></li><li><a href="/contact-us">Contact Us</a></li><li><a href="/brands">All Brands</a></li></ul></div>
<div><p class="foot-h">About</p><ul><li><a href="/about-fore-ladies-golf">Our Story</a></li><li><a href="/playforpink">Play for P.I.N.K.</a></li><li><a href="/blog">Blog</a></li></ul></div>
</div><div class="wrap foot-base"><p>&copy; {y} Fore Ladies Golf. All rights reserved.</p></div></footer>'''

def page(path, title, desc, body, *, robots='index, follow', og_image=None, og_type='website', schema=None, extra_head='', canonical=True):
    canon = URL + ('/' if path == '/' else path)
    img = URL + (og_image or '/img/og-default.jpg')
    ga = SITE.get('ga4')
    ga_tag = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={ga}"></script>'
              f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{ga}');</script>") if ga else ''
    verify = ''
    if path == '/':
        if SITE.get('bing_verify'): verify += f'<meta name="msvalidate.01" content="{SITE["bing_verify"]}">'
        if SITE.get('google_verify'): verify += f'<meta name="google-site-verification" content="{SITE["google_verify"]}">'
    sch = ''
    if schema:
        sch = ld({"@context": "https://schema.org", "@graph": schema if isinstance(schema, list) else [schema]})
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<meta name="robots" content="{robots}">
{f'<link rel="canonical" href="{canon}">' if canonical else ''}
<meta property="og:site_name" content="Fore Ladies Golf">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{img}">
<meta name="theme-color" content="#111111">
{verify}
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="alternate" type="application/rss+xml" title="Fore Ladies Golf Blog" href="/feed.xml">
<link rel="preload" href="/assets/fonts/poppins-latin-600-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/site.css?v={CSS_V}">
{extra_head}
{ga_tag}
{sch}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="announce">{E(SITE["announcement"])}</div>
<header class="site-header"><div class="wrap head-row">
<a class="logo" href="/" aria-label="Fore Ladies Golf home"><img src="{SITE["logo"]}" alt="Fore Ladies Golf" width="{SITE["logo_w"]}" height="{SITE["logo_h"]}"></a>
<button class="menu-btn" aria-expanded="false" aria-controls="site-nav">Menu</button>
<nav id="site-nav" class="site-nav" aria-label="Main">{NAV}</nav>
</div></header>
<main id="main">
{body}
</main>
{footer_html()}
<script src="/assets/site.js?v={JS_V}" defer></script>
</body>
</html>
'''

def write(path, content):
    if path == '/': fn = os.path.join(ROOT, 'index.html')
    else: fn = os.path.join(ROOT, path.lstrip('/') + '.html')
    os.makedirs(os.path.dirname(fn), exist_ok=True)
    open(fn, 'w', encoding='utf-8').write(content)
    WRITTEN.add(path)
WRITTEN = set()

def img_tag(src, alt, w=None, h=None, cls='', lazy=True, sizes=None):
    from PIL import Image
    if w is None:
        try:
            im = Image.open(os.path.join(ROOT, src.lstrip('/'))); w, h = im.size
        except Exception: w, h = 600, 600
    attrs = f' class="{cls}"' if cls else ''
    load = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    return f'<img src="{E(src)}" alt="{E(alt)}" width="{w}" height="{h}"{attrs}{load}>'

def initials(s):
    w = [x for x in re.split(r'\W+', s or '') if x]
    return (''.join(x[0] for x in w[:2]) or 'FL').upper()

def product_card(p):
    if p.get('img'):
        fig = img_tag(p['img']['thumb'], p['img']['alt'] or p['name'], cls='card-img')
    else:
        fig = f'<span class="card-ph" aria-hidden="true"><span>{E(initials(p.get("brand") or p["name"]))}</span></span>'
    price = f'<span class="card-price">Last listed {E(p["last_price"])}</span>' if p.get('last_price') else ''
    brand = f'<span class="card-brand">{E(p["brand"])}</span>' if p.get('brand') else ''
    fs = '<span class="badge">Final sale</span>' if p.get('final_sale') else ''
    return f'<li class="card"><a href="{p["path"]}">{fig}{fs}{brand}<span class="card-name">{E(p["name"])}</span>{price}</a></li>'

def sort_products(lst):
    return sorted(lst, key=lambda p: (0 if p.get('img') else 1, p.get('final_sale', False), p['name'].lower()))

_DIM = {}
def fix_imgs(h):
    """Add width/height to content images that lack them."""
    from PIL import Image
    def rep(m):
        tag = m.group(0)
        if ' width=' in tag: return tag
        src = re.search(r'src="([^"]+)"', tag)
        if not src or src.group(1).startswith('http'): return tag
        p = src.group(1)
        if p not in _DIM:
            try: _DIM[p] = Image.open(os.path.join(ROOT, p.lstrip('/'))).size
            except Exception: _DIM[p] = None
        if not _DIM[p]: return tag
        w, hh = _DIM[p]
        return tag[:-1] + f' width="{w}" height="{hh}" decoding="async">'
    return re.sub(r'<img [^>]*>', rep, h)

def yt_lite(h):
    h = fix_imgs(h)
    return re.sub(r'<p class="yt-embed" data-yt="([\w-]+)"></p>',
                  lambda m: f'<div class="yt" data-yt="{m.group(1)}"><button type="button" class="yt-btn" aria-label="Play video"><img src="https://i.ytimg.com/vi/{m.group(1)}/hqdefault.jpg" alt="Video thumbnail" loading="lazy" width="480" height="360"><span class="yt-play" aria-hidden="true"></span></button></div>', h)

def cat_chain(path):
    chain = []
    seen = set()
    while path and path in CATS and path not in seen:
        seen.add(path); chain.insert(0, (CATS[path]['name'], path)); path = CATS[path].get('parent')
    return chain

# ------------------------------------------------------------------ product pages
def type_tip(p):
    n = (p['name'] + ' ' + ' '.join(x for x, _ in p.get('bc', []))).lower()
    has = lambda *ks: any(re.search(k, n) for k in ks)
    if has(r'\bdress'):
        return 'Golf dresses fit best when the torso length matches yours. See the <a href="/womens-golf-clothes-size-charts">fit guide</a> for how to measure torso length and compare brands.'
    if has(r'\bsk(o|i)rts?\b', r'\bshorts\b', r'\bshortie'):
        return 'Skort and short lengths are measured from the waistband. Our <a href="/womens-golf-clothes-size-charts">size chart and fit guide</a> explains how to pick a length that works for your height and your club\'s dress code.'
    if has(r'\bpants?\b', r'legging', r'capri', r'ankle'):
        return 'Golf pants are usually cut long enough to sit over a shoe. If you are under about 5\'4", the <a href="/petite-womens-golf-clothes">petite guide</a> covers inseams and hems.'
    if has(r'\bshoes?\b'):
        return 'Golf shoe sizing varies between brands. Measure your foot late in the day, and compare with a pair you already wear on the course.'
    if has(r'polo', r'\btops?\b', r'shirt', r'\btank', r'\btee\b', r'sleeve', r'jacket', r'\bvest', r'pullover', r'sweater', r'hoodie', r'shrug', r'layer'):
        return 'Tops from performance brands are often cut closer than traditional golf shirts. Compare your bust and shoulder measurements with the <a href="/womens-golf-clothes-size-charts">size charts</a> before choosing between two sizes.'
    return 'Questions about this item? The <a href="/contact-us">contact page</a> explains how to reach the Fore Ladies team.'

def guide_for(p):
    n = (p['name'] + ' ' + ' '.join(x for x, _ in p.get('bc', []))).lower()
    pick = [(r'\bdress', 'how-to-choose-a-golf-dress', 'How to choose a golf dress'),
            (r'tennis', 'can-you-wear-tennis-clothes-golfing', 'Can you wear tennis clothes golfing?'),
            (r'\bsk(o|i)rt', 'golf-skort-length-guide', 'How long should a golf skort be?'),
            (r'\bshorts\b', 'golf-skort-vs-skirt-vs-shorts', 'Golf skort vs skirt vs shorts'),
            (r'\bshoes?\b', 'how-to-choose-womens-golf-shoes', "How to choose women's golf shoes"),
            (r'jacket|vest|pullover|sweater|layer|hoodie|long ?sleeve', 'cold-weather-golf-outfits-women', 'What to wear golfing in cold weather'),
            (r'uv|upf|sleeveless|visor|hat\b|cap\b', 'hot-weather-golf-outfits-upf', 'Hot weather golf outfits and UPF'),
            (r'bag|tee\b|tees|towel|cover|grip|cart', 'golf-trip-packing-list-women', 'Golf trip packing list for women'),
            (r'', 'what-to-wear-golfing-women', 'What to wear golfing: outfit guide')]
    for rx, slug, label in pick:
        if re.search(rx, n) and '/blog/' + slug in NEW:
            return f'<p class="tip">Style guide: <a href="/blog/{slug}">{E(label)}</a></p>'
    return ''

def build_products():
    for p in PRODUCTS.values():
        chain = []
        if p.get('bc'):
            last = p['bc'][-1][1]
            chain = cat_chain(last)
        elif p.get('brand_path') in CATS:
            chain = [(CATS[p['brand_path']]['name'], p['brand_path'])]
        crumbs = [('Home', '/')] + chain + [(p['name'], p['path'])]
        primary = chain[-1][1] if chain else (p.get('brand_path') or '/womens-golf-clothes')
        # related
        pool = []
        for src in ([primary] if primary in CATS else []) + ([p['brand_path']] if p.get('brand_path') in CATS else []):
            for x in live_products(CATS[src]):
                if x['path'] != p['path'] and x not in pool: pool.append(x)
        related = sort_products(pool)[:8]
        if p.get('img'):
            media = img_tag(p['img']['src'], p['img']['alt'] or p['name'], cls='pd-img', lazy=False)
        else:
            media = f'<div class="pd-ph" aria-hidden="true"><span>{E(initials(p.get("brand") or p["name"]))}</span><small>Photo not available</small></div>'
        brand = ''
        if p.get('brand'):
            bname = E(p['brand'])
            brand = f'<p class="pd-brand"><a href="{p["brand_path"]}">{bname}</a></p>' if p.get('brand_path') else f'<p class="pd-brand">{bname}</p>'
        facts = []
        if p.get('sizes'): facts.append(f'<div><dt>Sizes offered</dt><dd>{E(", ".join(p["sizes"]))}</dd></div>')
        if p.get('colors'): facts.append(f'<div><dt>Color</dt><dd>{E(", ".join(p["colors"]))}</dd></div>')
        if p.get('last_price'): facts.append(f'<div><dt>Last listed price</dt><dd>{E(p["last_price"])}</dd></div>')
        if p.get('sku'): facts.append(f'<div><dt>SKU</dt><dd>{E(p["sku"])}</dd></div>')
        fs = '<p class="badge badge-lg">Final sale item</p>' if p.get('final_sale') else ''
        desc = yt_lite(p.get('desc_html') or '')
        if not text_of(desc):
            desc = f'<p>{E(p["name"])}{" by " + E(p["brand"]) if p.get("brand") else ""}. Browse <a href="{primary}">{E(chain[-1][0]) if chain else "more styles"}</a> for similar pieces.</p>'
        rel_html = ''
        if related:
            rel_html = f'<section class="related"><h2>More {E(chain[-1][0]) if chain else "styles"} to explore</h2><ul class="grid">{"".join(product_card(x) for x in related)}</ul></section>'
        body = f'''<div class="wrap">{crumbs_html(crumbs)}
<article class="pd">
<div class="pd-media">{media}</div>
<div class="pd-info">{brand}<h1>{E(p["name"])}</h1>{fs}
<dl class="facts">{"".join(facts)}</dl>
<p class="notice">{E(SITE["checkout_note"])} Questions about this style? See our <a href="/contact-us">contact page</a>.</p>
<p class="tip">{type_tip(p)}</p>
{guide_for(p)}
</div>
</article>
<section class="pd-desc prose"><h2>Product details</h2>{desc}</section>
{rel_html}
</div>'''
        schema = [ORG, breadcrumb_ld(crumbs), {"@type": "ItemPage", "@id": URL + p['path'] + "#page", "url": URL + p['path'], "name": p['name'],
                  "isPartOf": {"@id": URL + "/#website"}, "breadcrumb": {"@id": URL + p['path'] + "#bc"},
                  **({"primaryImageOfPage": {"@type": "ImageObject", "url": URL + p['img']['src']}} if p.get('img') else {})}]
        schema[1]["@id"] = URL + p['path'] + "#bc"
        robots = 'index, follow, max-image-preview:large' if product_indexable(p) else 'noindex, follow'
        write(p['path'], page(p['path'], product_title(p), product_desc(p), body, robots=robots,
                               og_image=p['img']['src'] if p.get('img') else None, schema=schema))

# ------------------------------------------------------------------ category pages
def split_desc(h):
    """Lead (first paragraph-ish) above the grid, the rest below."""
    if wcount(h) < 160: return h, ''
    parts = re.split(r'(?=<h[234]>)', h, maxsplit=1)
    if len(parts) == 2 and wcount(parts[0]) >= 30: return parts[0], parts[1]
    m = re.search(r'</p>\n?', h)
    if m: return h[:m.end()], h[m.end():]
    return h, ''

def build_categories():
    for c in CATS.values():
        prods = sort_products(live_products(c))
        chain = cat_chain(c['path'])
        crumbs = [('Home', '/')] + (chain if chain else [(c['name'], c['path'])])
        lead, rest = split_desc(c.get('desc_html') or '')
        kids = [CATS[k] for k in c.get('children', []) if k in CATS and live_products(CATS[k])]
        chips = ''
        if kids:
            chips = '<ul class="chips">' + ''.join(f'<li><a href="{k["path"]}">{E(k["name"])}</a></li>' for k in kids) + '</ul>'
        if not lead:
            noun = c['name']
            if c['kind'] == 'brand':
                lead = f'<p>Women\'s golf and tennis pieces from {E(noun)} in the Fore Ladies catalog. Each product page lists the sizes offered, the last listed price and fit notes.</p>'
            else:
                lead = f'<p>{E(noun)} from the Fore Ladies catalog of women\'s golf and tennis apparel. Use the product pages for sizes and fit notes, and check our <a href="/womens-golf-clothes-size-charts">size charts</a> before you choose.</p>'
        grid = f'<ul class="grid">{"".join(product_card(p) for p in prods)}</ul>' if prods else '<p class="empty">There are no products in this section right now. Try <a href="/womens-golf-clothes">all golf apparel</a> or our <a href="/blog">style guides</a>.</p>'
        count = f'<p class="count">{len(prods)} style{"s" if len(prods) != 1 else ""}</p>' if prods else ''
        more = f'<section class="cat-more prose"><h2>More about {E(c["name"])}</h2>{rest}</section>' if rest else ''
        guides = [a for a in sorted(NEW.values(), key=lambda a: a['file']) if c['path'] in a.get('related_categories', []) or (c.get('parent') and c['parent'] in a.get('related_categories', []))][:4]
        guides_html = ''
        if guides:
            guides_html = '<section class="guides"><h2>Style &amp; fit guides</h2><ul class="post-grid">' + ''.join(post_card(a) for a in guides) + '</ul></section>'
        body = f'''<div class="wrap">{crumbs_html(crumbs)}
<header class="cat-head"><h1>{E(c["name"])}</h1><div class="prose lead">{lead}</div>{chips}</header>
<p class="notice">{E(SITE["checkout_note"])} These pages are kept as a style and sizing reference.</p>
{count}{grid}{guides_html}{more}</div>'''
        schema = [ORG, breadcrumb_ld(crumbs), {"@type": "CollectionPage", "url": URL + c['path'], "name": c['name'],
                  "mainEntity": {"@type": "ItemList", "numberOfItems": len(prods), "itemListElement": [
                      {"@type": "ListItem", "position": i + 1, "url": URL + p['path'], "name": p['name']} for i, p in enumerate(prods[:60])]}}]
        robots = 'index, follow' if cat_indexable(c) else 'noindex, follow'
        og = next((p['img']['src'] for p in prods if p.get('img')), None)
        write(c['path'], page(c['path'], cat_title(c), cat_desc(c), body, robots=robots, schema=schema, og_image=og))

# ------------------------------------------------------------------ blog
def post_date(p): return p.get('date') or '2018-01-01'
def fmt_date(s):
    d = dt.date.fromisoformat(s); return d.strftime('%B %-d, %Y')

def post_card(p):
    img = p.get('thumb') or p.get('img')
    fig = img_tag(img, p.get('image_alt') or p['title'], cls='post-img') if img else '<span class="post-ph" aria-hidden="true"></span>'
    ex = trim(p.get('description') or first_sentences(p.get('body_html'), 150), 150)
    return f'<li class="post-card"><a href="{p["path"]}">{fig}<span class="post-date">{fmt_date(post_date(p))}</span><span class="post-title">{E(p["title"])}</span><span class="post-ex">{E(ex)}</span></a></li>'

def build_blog():
    lst = sorted(ALLPOSTS.values(), key=lambda p: post_date(p), reverse=True)
    body = f'''<div class="wrap">{crumbs_html([("Home", "/"), ("Blog", "/blog")])}
<header class="cat-head"><h1>Fore Ladies Golf Blog</h1><div class="prose lead"><p>Style guides, sizing help, dress-code explainers and golf stories for women who play — written by the Fore Ladies Golf team.</p></div></header>
<ul class="post-grid">{"".join(post_card(p) for p in lst)}</ul></div>'''
    schema = [ORG, breadcrumb_ld([("Home", "/"), ("Blog", "/blog")]), {"@type": "Blog", "url": URL + "/blog", "name": "Fore Ladies Golf Blog",
              "blogPost": [{"@type": "BlogPosting", "headline": p['title'], "url": URL + p['path'], "datePublished": post_date(p)} for p in lst[:30]]}]
    write('/blog', page('/blog', title_for('/blog', "Women's Golf Style & Fit Blog | Fore Ladies"),
                        desc_for('/blog', "Golf outfit ideas, size and fit guides, dress-code explainers and golf stories for women, from the Fore Ladies Golf team."), body, schema=schema))
    for p in lst:
        body_html = yt_lite(p['body_html'])
        rel = [x for x in lst if x['path'] != p['path']]
        rel.sort(key=lambda x: (len(set(x.get('labels', [])) & set(p.get('labels', []))), post_date(x)), reverse=True)
        related = rel[:3]
        upd = p.get('updated') or p.get('date')
        meta = f'<p class="post-meta">By {E(p.get("author") or "Fore Ladies Golf")} · <time datetime="{post_date(p)}">{fmt_date(post_date(p))}</time>'
        if p.get('updated') and p.get('updated') != p.get('date'): meta += f' · Updated <time datetime="{p["updated"]}">{fmt_date(p["updated"])}</time>'
        meta += '</p>'
        hero = img_tag(p['img'], p.get('image_alt') or p['title'], cls='post-hero', lazy=False) if p.get('img') and p.get('new') else ''
        cats = ''.join(f'<li><a href="{x}">{E(CATS[x]["name"])}</a></li>' for x in p.get('related_categories', []) if x in CATS)
        cats_html = f'<aside class="shop-links"><p class="foot-h">Related sections</p><ul class="chips">{cats}</ul></aside>' if cats else ''
        body = f'''<div class="wrap narrow">{crumbs_html([("Home", "/"), ("Blog", "/blog"), (p["title"], p["path"])])}
<article class="post"><header><h1>{E(p["title"])}</h1>{meta}</header>{hero}
<div class="prose">{body_html}</div>
{cats_html}
<aside class="author-box"><p><strong>Written by the Fore Ladies Golf team.</strong> Fore Ladies is a woman-owned women's golf apparel business founded in {SITE["founded"]} by a golfer who couldn't find golf clothes she liked. <a href="/about-fore-ladies-golf">Read our story</a>.</p></aside>
</article>
<section class="related"><h2>Keep reading</h2><ul class="post-grid">{"".join(post_card(x) for x in related)}</ul></section></div>'''
        posting = {"@type": "BlogPosting", "@id": URL + p['path'] + "#post", "headline": p['title'], "url": URL + p['path'],
                   "datePublished": post_date(p), "dateModified": upd or post_date(p), "mainEntityOfPage": URL + p['path'],
                   "author": {"@type": "Organization", "name": "Fore Ladies Golf", "url": URL + "/about-fore-ladies-golf"},
                   "publisher": {"@id": URL + "/#org"}, "inLanguage": "en-US", "wordCount": wcount(p['body_html'])}
        if p.get('img'): posting['image'] = URL + p['img']
        if p.get('about'): posting['about'] = [{"@type": "Thing", "name": n, "sameAs": u} for n, u in p['about']]
        if p.get('mentions'): posting['mentions'] = [{"@type": "Thing", "name": n, "sameAs": u} for n, u in p['mentions']]
        schema = [ORG, breadcrumb_ld([("Home", "/"), ("Blog", "/blog"), (p["title"], p["path"])]), posting]
        faq = re.findall(r'<h3>([^<]+\?)</h3>\s*<p>(.*?)</p>', p['body_html'], re.S) if p.get('new') else []
        title = p.get('seo_title') or f"{p['title']} | Fore Ladies"
        if len(title) > 60: title = p['title']
        desc = p.get('description') or first_sentences(p['body_html'], 155)
        write(p['path'], page(p['path'], title_for(p['path'], title), desc_for(p['path'], desc), body, og_type='article',
                               og_image=p.get('img'), schema=schema,
                               extra_head=f'<meta property="article:published_time" content="{post_date(p)}"><meta property="article:modified_time" content="{upd or post_date(p)}">'))

# ------------------------------------------------------------------ static pages
PAGE_NOTES = {
    '/playforpink': '<p class="notice">This page describes a past Fore Ladies Golf partnership and is kept for reference. Online checkout and the discount code mentioned below are not active on this website.</p>',
}
PAGE_TITLES = {
    '/about-fore-ladies-golf': ("Our Story | Woman-Owned Women's Golf Apparel", "How a golfer who couldn't find golf clothes she liked started Fore Ladies Golf, a woman-owned women's golf apparel business, in 2017."),
    '/shipping-returns': ('Shipping & Returns | Fore Ladies Golf', 'Fore Ladies Golf shipping and returns policy: return windows, refunds, store credit, Tee Box subscription rules and international shipping.'),
    '/contact-us': ('Contact Us | Fore Ladies Golf', 'How to reach the Fore Ladies Golf team with questions about a style, sizing or a past order.'),
}
def build_pages():
    for p in PAGES.values():
        name = p['name']
        crumbs = [('Home', '/'), (name, p['path'])]
        body_html = p.get('body_html') or ''
        if p['path'] == '/contact-us':
            email = SITE.get('contact_email')
            if email:
                body_html = f'<p>Questions about a style, sizing or a past order? Email us at <a href="mailto:{E(email)}">{E(email)}</a> and we will get back to you.</p>'
            else:
                body_html = ('<p>We are updating our contact options. While we do, the fastest help for sizing questions is our '
                             '<a href="/womens-golf-clothes-size-charts">size charts and fit guide</a>, and our <a href="/shipping-returns">shipping and returns policy</a> covers returns and exchanges for past orders.</p>')
        if p['path'] == '/plus-size-womens-golf-clothes':
            body_html += ('<h2>Shop by category</h2><ul class="chips"><li><a href="/womens-golf-shirts">Tops</a></li><li><a href="/bottoms">Bottoms</a></li>'
                          '<li><a href="/golf-dresses">Golf Dresses</a></li><li><a href="/outerwear">Outerwear</a></li></ul>')
        body_html = PAGE_NOTES.get(p['path'], '') + body_html
        t, d = PAGE_TITLES.get(p['path'], (None, None))
        title = title_for(p['path'], t or (p.get('old_title') if p.get('old_title') and len(p.get('old_title')) > 20 else f"{name} | Fore Ladies Golf"))
        desc = desc_for(p['path'], d or (p.get('old_desc') if p.get('old_desc') and 'woman-owned boutique' not in p.get('old_desc') else first_sentences(body_html, 155)))
        body = f'<div class="wrap narrow">{crumbs_html(crumbs)}<article class="prose page-body"><h1>{E(name)}</h1>{yt_lite(body_html)}</article></div>'
        write(p['path'], page(p['path'], title, desc, body, schema=[ORG, breadcrumb_ld(crumbs), {"@type": "WebPage", "url": URL + p['path'], "name": name}]))

def build_html_sitemap():
    crumbs = [('Home', '/'), ('Sitemap', '/sitemap')]
    def ul(items): return '<ul>' + ''.join(f'<li><a href="{h}">{E(n)}</a></li>' for n, h in items) + '</ul>'
    cats = sorted([(c['name'], c['path']) for c in CATS.values() if c['kind'] != 'brand' and cat_indexable(c)], key=lambda x: x[1])
    brands = sorted([(c['name'], c['path']) for c in CATS.values() if c['kind'] == 'brand' and cat_indexable(c)], key=lambda x: x[0].lower())
    posts = [(p['title'], p['path']) for p in sorted(ALLPOSTS.values(), key=lambda p: post_date(p), reverse=True)]
    pages = [(p['name'], p['path']) for p in PAGES.values()] + [('Brands', '/brands'), ('Blog', '/blog')]
    body = f'''<div class="wrap narrow">{crumbs_html(crumbs)}<article class="prose page-body"><h1>Sitemap</h1>
<h2>Shop sections</h2>{ul(cats)}<h2>Brands</h2>{ul(brands)}<h2>Guides and articles</h2>{ul(posts)}<h2>About and help</h2>{ul(pages)}</article></div>'''
    write('/sitemap', page('/sitemap', 'Sitemap | Fore Ladies Golf', 'All sections, brands, guides and help pages on the Fore Ladies Golf website.', body,
                           schema=[ORG, breadcrumb_ld(crumbs)]))

def build_brands():
    brands = sorted([c for c in CATS.values() if c['kind'] == 'brand' and live_products(c)], key=lambda c: c['name'].lower())
    items = ''.join(f'<li><a href="{c["path"]}"><span class="brand-name">{E(c["name"])}</span><span class="brand-n">{len(live_products(c))} styles</span></a></li>' for c in brands)
    crumbs = [('Home', '/'), ('Brands', '/brands')]
    body = f'''<div class="wrap">{crumbs_html(crumbs)}<header class="cat-head"><h1>Women's Golf &amp; Tennis Brands</h1>
<div class="prose lead"><p>Every brand in the Fore Ladies catalog, from performance golf labels to tennis and accessory makers. Pick a brand to see its styles, sizes offered and fit notes.</p></div></header>
<ul class="brand-list">{items}</ul></div>'''
    write('/brands', page('/brands', title_for('/brands', "Women's Golf & Tennis Apparel Brands | Fore Ladies"),
                          desc_for('/brands', "All women's golf and tennis apparel brands in the Fore Ladies catalog, including Daily Sports, Kinona, Tail Activewear, Lucky In Love and more."),
                          body, schema=[ORG, breadcrumb_ld(crumbs), {"@type": "CollectionPage", "url": URL + "/brands", "name": "Brands"}]))

# ------------------------------------------------------------------ home
def build_home():
    tiles = [
        ('/womens-golf-clothes', 'Golf apparel', '/img/shg/6a3d18b4-672d-4cbe-bfce-ecce71dc2d4f.jpg', 'Golfer in a sleeveless top and white golf pants'),
        ('/tennis-clothes-women', 'Tennis apparel', '/img/shg/f95525f4-2d20-4608-98b7-4b006c2820e0.jpg', 'Tennis player in a black tank and printed skirt'),
        ('/golf-dresses', 'Golf dresses', '/img/shg/968ce8c4-a1c8-4f86-a4e1-c135432c8025.jpg', 'Golfer in a plaid sleeveless golf dress'),
    ]
    tile_html = ''.join(f'<li><a href="{h}">{img_tag(s, a, cls="tile-img", lazy=(i > 0))}<span class="tile-label sr">{E(l)}</span></a></li>' for i, (h, l, s, a) in enumerate(tiles))
    styles = [
        ('/the-fringe', 'Bold prints', '/8dc766dd-6c48-43a3-b4d4-666395f21938/-/format/auto/-/preview/3000x3000/-/quality/lighter/image_file.jpg', 'Leopard print golf outfit flat lay with a pink skort'),
        ('/fore-ladies-tee-box', 'The Tee Box', '/51b69ab6-92fe-4478-baf3-c04c8cbb0853/-/format/auto/-/preview/3000x3000/-/quality/lighter/image_file.jpg', 'Fore Ladies Tee Box filled with golf apparel and accessories'),
        ('/womens-golf-shirts', 'Classic stripes', '/49df4388-dcd7-49f2-a681-8ef195d12680/-/format/auto/-/preview/3000x3000/-/quality/lighter/image_file.jpg', 'Blue striped golf top with a printed skort and white shoes'),
        ('/red-white-and-blue', 'Plaid and color', '/f284fad5-9639-4715-a527-83c9b461db4d/-/format/auto/-/preview/3000x3000/-/quality/lighter/image_file.jpg', 'Plaid golf pants with a red polo and visor'),
    ]
    style_html = ''.join(f'<li><a href="{h}">{img_tag(s, a, cls="style-img")}<span>{E(l)}</span></a></li>' for h, l, s, a in styles)
    featured = sort_products([p for p in PRODUCTS.values() if p.get('img') and not p.get('final_sale')])[:8]
    lst = sorted(ALLPOSTS.values(), key=lambda p: post_date(p), reverse=True)[:3]
    quotes = ''.join(f'<li><blockquote><p>“{E(t["quote"])}”</p><footer>— {E(t["name"])}, {E(t["place"])}</footer></blockquote></li>' for t in TESTI)
    body = f'''<section class="hero"><div class="wrap">
<h1>Women's Golf Clothes, Golf Dresses and Tennis Apparel for Every Style</h1>
<p class="hero-sub">Woman-owned. Woman-operated. Woman-focused. We know what women want on the course, because we are women who play.</p>
<p class="hero-cta"><a class="btn" href="/womens-golf-clothes">Browse golf apparel</a> <a class="btn btn-ghost" href="/womens-golf-clothes-size-charts">Size &amp; fit guide</a></p>
</div></section>
<div class="wrap">
<ul class="tiles">{tile_html}</ul>
<section class="home-intro prose"><h2>Confidence starts with what you wear</h2>
<p>The premise behind Fore Ladies Golf is simple: confidence is paramount on the golf course, and more often than not, that starts with our clothes. Anyone who plays knows golf is as much a mental game as a physical one — when we look good, we feel good.</p>
<p>Fore women, by women. We are golfers, and we believe personal style reflects personality. Whether you are a pants-and-polo player or prefer flirty skorts and bold prints, you will find ideas here, plus <a href="/womens-golf-clothes-size-charts">size charts</a>, a <a href="/petite-womens-golf-clothes">petite fit guide</a> and <a href="/blog">style articles</a>.</p>
<p class="notice">{E(SITE["checkout_note"])} The catalog stays online as a style and sizing reference.</p></section>
<section><h2 class="sec-h">Discover your style</h2><ul class="styles">{style_html}</ul></section>
<section><h2 class="sec-h">From the catalog</h2><ul class="grid">{"".join(product_card(p) for p in featured)}</ul></section>
<section class="quotes"><h2 class="sec-h">What our customers said</h2><ul>{quotes}</ul></section>
<section><h2 class="sec-h">Latest from the blog</h2><ul class="post-grid">{"".join(post_card(p) for p in lst)}</ul><p class="more-link"><a href="/blog">All articles</a></p></section>
</div>'''
    schema = [ORG, {"@type": "WebSite", "@id": URL + "/#website", "url": URL + "/", "name": "Fore Ladies Golf", "publisher": {"@id": URL + "/#org"}, "inLanguage": "en-US"}]
    write('/', page('/', title_for('/', "Women's Golf Clothes & Golf Dresses | Fore Ladies Golf"),
                    desc_for('/', "Women's golf clothes, golf dresses, skorts and tennis apparel from a woman-owned golf boutique — with size charts, fit guides and style ideas."),
                    body, schema=schema, og_image='/img/og-default.jpg'))

# ------------------------------------------------------------------ 404
def build_404():
    body = '''<div class="wrap narrow"><article class="prose page-body"><h1>Page not found</h1>
<p>The page you were looking for has moved or is no longer available. Many older product pages were retired when styles sold out.</p>
<ul><li><a href="/womens-golf-clothes">Women's golf apparel</a></li><li><a href="/golf-dresses">Golf dresses</a></li><li><a href="/bottoms/skorts">Golf skorts</a></li><li><a href="/tennis-clothes-women">Tennis apparel</a></li><li><a href="/womens-golf-clothes-size-charts">Size charts &amp; fit guide</a></li><li><a href="/blog">Blog</a></li></ul></article></div>'''
    html_ = page('/404', 'Page not found | Fore Ladies Golf', 'This page could not be found.', body, robots='noindex, follow', canonical=False)
    open(os.path.join(ROOT, '404.html'), 'w', encoding='utf-8').write(html_)

# ------------------------------------------------------------------ sitemap, feed, robots, htaccess
def build_sitemap():
    urls = []
    def add(path, lastmod, imgs=()):
        urls.append((path, lastmod, imgs))
    add('/', TODAY_S, ['/img/shg/6a3d18b4-672d-4cbe-bfce-ecce71dc2d4f.jpg'])
    for path in ['/blog', '/brands', '/sitemap']: add(path, TODAY_S)
    for p in PAGES.values(): add(p['path'], TODAY_S)
    for c in CATS.values():
        if cat_indexable(c): add(c['path'], TODAY_S)
    for p in PRODUCTS.values():
        if product_indexable(p): add(p['path'], TODAY_S, [p['img']['src']] if p.get('img') else [])
    for p in ALLPOSTS.values():
        add(p['path'], p.get('updated') or TODAY_S if not p.get('new') else (p.get('updated') or p.get('date')), [p['img']] if p.get('img') else [])
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    for path, lm, imgs in urls:
        out.append(f'<url><loc>{xesc(URL + ("/" if path == "/" else path))}</loc><lastmod>{lm}</lastmod>' +
                   ''.join(f'<image:image><image:loc>{xesc(URL + i)}</image:loc></image:image>' for i in imgs) + '</url>')
    out.append('</urlset>')
    open(os.path.join(ROOT, 'sitemap.xml'), 'w').write('\n'.join(out) + '\n')
    return [u[0] for u in urls]

def build_feed():
    lst = sorted(ALLPOSTS.values(), key=lambda p: post_date(p), reverse=True)[:20]
    items = []
    for p in lst:
        d = dt.datetime.fromisoformat(post_date(p)).strftime('%a, %d %b %Y 09:00:00 +0000')
        items.append(f'<item><title>{xesc(p["title"])}</title><link>{URL}{p["path"]}</link><guid>{URL}{p["path"]}</guid><pubDate>{d}</pubDate><description>{xesc(trim(p.get("description") or first_sentences(p["body_html"], 200), 220))}</description></item>')
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel><title>Fore Ladies Golf Blog</title><link>{URL}/blog</link><atom:link href="{URL}/feed.xml" rel="self" type="application/rss+xml"/><description>Women's golf style, fit and dress-code guides from Fore Ladies Golf.</description><language>en-us</language><lastBuildDate>{dt.datetime.combine(TODAY, dt.time(9)).strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>
{chr(10).join(items)}
</channel></rss>
'''
    open(os.path.join(ROOT, 'feed.xml'), 'w').write(rss)

def build_robots():
    open(os.path.join(ROOT, 'robots.txt'), 'w').write(f'''User-agent: *
Allow: /
Disallow: /_build/
Disallow: /search
Disallow: /cart
Disallow: /checkout
Disallow: /login
Disallow: /wishlist

Sitemap: {URL}/sitemap.xml
''')

def htaccess_escape(p):
    return re.escape(p.lstrip('/')).replace('\\-', '-').replace('\\/', '/')

def build_htaccess():
    m = REDIR['map']
    lines = ['# Generated by _build/build.py — edit _build/content/redirects.json instead.',
             'Options -Indexes -MultiViews', 'DirectorySlash Off', 'ErrorDocument 404 /404.html', '',
             '<IfModule mod_rewrite.c>', 'RewriteEngine On', '',
             '# Private folders',
             'RewriteRule ^(_build|\\.git|data|README\\.md)(/|$) - [F,L]', '',
             '# Old platform URLs',
             'RewriteRule ^(rss\\.php|blog/rss|blog/feed|feed)(\\.html)?/?$ https://fore-ladies.com/feed.xml? [R=301,L]',
             'RewriteRule ^xmlsitemap\\.php$ https://fore-ladies.com/sitemap.xml? [R=301,L]',
             'RewriteRule ^(cart|checkout|login|wishlist|compare|account|giftcertificates)(\\.php|\\.html)?/?$ https://fore-ladies.com/? [R=301,L]',
             'RewriteRule ^(login_|wishlist_|giftcertificates_|account_)[^/]*$ https://fore-ladies.com/? [R=301,L]',
             'RewriteRule ^products_productId[^/]*$ https://fore-ladies.com/? [R=301,L]', '',
             '# Old store search pages -> closest category']
    for k, v in REDIR['search']:
        lines.append(f'RewriteRule ^search[^/]*{re.escape(k)}[^/]*$ https://fore-ladies.com{v}? [R=301,L,NC]')
    for k, v in (('dress', '/golf-dresses'), ('sk(o|i)rt', '/bottoms/skorts'), ('pant', '/bottoms/pants'), ('jacket', '/outerwear/jackets'), ('tennis', '/tennis-clothes-women')):
        lines += [f'RewriteCond %{{QUERY_STRING}} search_query=[^&]*{k} [NC]', f'RewriteRule ^search\\.php$ https://fore-ladies.com{v}? [R=301,L]']
    lines += ['RewriteRule ^search(\\.php)?[^/]*$ https://fore-ladies.com/womens-golf-clothes? [R=301,L]', '',
              '# Retired, merged or empty pages and their old variants (one hop)']
    for k in sorted(m):
        if k.startswith('/search'): continue
        lines.append(f'RewriteRule ^{htaccess_escape(k)}(\\.html)?/?$ https://fore-ladies.com{m[k]}? [R=301,L]')
    lines += ['',
              '# Sort / filter / pagination variants -> the category itself (only if it exists)',
              'RewriteCond %{DOCUMENT_ROOT}/$1.html -f',
              'RewriteRule ^(.+?)/(sort-[a-z]+(-page-[0-9]+)?|page-[0-9]+|price_min[^/]*|filter[^/]*)(\\.html)?/?$ https://fore-ladies.com/$1? [R=301,L]', '',
              ]
    lines += ['',
              '# index.html -> /',
              'RewriteCond %{THE_REQUEST} \\s/+index(\\.html)?[\\s?]',
              'RewriteRule ^index(\\.html)?$ https://fore-ladies.com/ [R=301,L]',
              '# .html in the address bar -> clean URL',
              'RewriteCond %{THE_REQUEST} \\s/+([^\\s?]+?)\\.html[\\s?]',
              'RewriteRule ^ https://fore-ladies.com/%1 [R=301,L,NE]',
              '# trailing slash -> clean URL (old BigCommerce links used it)',
              'RewriteCond %{REQUEST_URI} ^/(.+)/$',
              'RewriteRule ^ https://fore-ladies.com/%1 [R=301,L,NE]',
              '# ?m=1 and other old query junk on pages',
              'RewriteCond %{QUERY_STRING} (^|&)(m=1|sort=|page=|setCurrencyId=|action=)',
              'RewriteRule ^(.*)$ https://fore-ladies.com/$1? [R=301,L,NE]',
              '# www -> non-www',
              'RewriteCond %{HTTP_HOST} ^www\\.(.+)$ [NC]',
              'RewriteRule ^(.*)$ https://fore-ladies.com/$1 [R=301,L,NE]',
              '',
              '# Serve clean URLs from .html files',
              'RewriteCond %{REQUEST_FILENAME}.html -f',
              'RewriteRule ^(.+)$ $1.html [L]',
              '</IfModule>', '',
              '<IfModule mod_headers.c>',
              '<FilesMatch "\\.(css|js|woff2|jpg|jpeg|png|webp|svg|ico)$">', 'Header set Cache-Control "public, max-age=2592000"', '</FilesMatch>',
              '<FilesMatch "\\.(html|xml)$">', 'Header set Cache-Control "public, max-age=600"', '</FilesMatch>',
              'Header always set X-Content-Type-Options "nosniff"',
              'Header always set Referrer-Policy "strict-origin-when-cross-origin"',
              '</IfModule>', '',
              '<IfModule mod_deflate.c>', 'AddOutputFilterByType DEFLATE text/html text/css application/javascript application/xml text/xml image/svg+xml application/rss+xml', '</IfModule>', '']
    open(os.path.join(ROOT, '.htaccess'), 'w').write('\n'.join(lines))

# ------------------------------------------------------------------ icons + manifest + og
def build_icons():
    from PIL import Image, ImageDraw, ImageFont
    acc = SITE['colors']['accent']
    def make(size):
        im = Image.new('RGB', (size, size), '#111111'); d = ImageDraw.Draw(im)
        f = ImageFont.truetype(os.path.join(B, 'assets-src', 'Poppins-SemiBold.ttf'), int(size * 0.42)) if os.path.exists(os.path.join(B, 'assets-src', 'Poppins-SemiBold.ttf')) else ImageFont.load_default()
        t = 'FL'; w = d.textlength(t, font=f)
        d.text(((size - w) / 2, size * 0.24), t, font=f, fill='white')
        d.rectangle([size * 0.2, size * 0.78, size * 0.8, size * 0.82], fill=acc)
        return im
    if not os.path.exists(os.path.join(ROOT, 'favicon.ico')):
        src = os.path.join(ROOT, SITE['favicon_src'].lstrip('/'))
        Image.open(src).save(os.path.join(ROOT, 'favicon.ico'), sizes=[(32, 32)])
    for name, s in (('apple-touch-icon.png', 180), ('icon-192.png', 192), ('icon-512.png', 512)):
        if not os.path.exists(os.path.join(ROOT, name)): make(s).save(os.path.join(ROOT, name), optimize=True)
    open(os.path.join(ROOT, 'icon.svg'), 'w').write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#111"/><text x="32" y="40" font-family="Arial,Helvetica,sans-serif" font-size="26" font-weight="700" fill="#fff" text-anchor="middle">FL</text><rect x="14" y="48" width="36" height="3" fill="{acc}"/></svg>\n')
    json.dump({"name": "Fore Ladies Golf", "short_name": "Fore Ladies", "start_url": "/", "display": "browser", "background_color": "#ffffff", "theme_color": "#111111",
               "icons": [{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}]},
              open(os.path.join(ROOT, 'site.webmanifest'), 'w'), indent=1)

def main():
    global NAV
    asset_versions(); NAV = nav_html(); prepare_products()
    build_icons()
    build_home(); build_products(); build_categories(); build_blog(); build_pages(); build_brands(); build_html_sitemap(); build_404()
    sm = build_sitemap(); build_feed(); build_robots(); build_htaccess()
    # stale page check: html files that are not written by this build
    stale = []
    for f in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if rel.startswith(('_build', '.git', 'node_modules')) or rel == '404.html': continue
        path = '/' if rel == 'index.html' else '/' + rel[:-5]
        if path not in WRITTEN: stale.append(rel)
    print(f'built {len(WRITTEN)} pages, sitemap {len(sm)} urls, new articles {len(NEW)}')
    if stale: print('WARNING stale html files not generated by build:', stale[:20])

if __name__ == '__main__':
    main()
