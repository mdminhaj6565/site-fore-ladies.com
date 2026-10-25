#!/usr/bin/env python3
"""Site checks. Exit code 1 = something to fix.
Usage: python3 _build/check.py            (whole site)
       python3 _build/check.py /blog/slug (also prints that page's details)
"""
import os, re, sys, json, glob, html, collections
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
problems = []
def prob(msg): problems.append(msg)

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.imgs = []; self.h1 = 0; self.title = ''; self.desc = ''; self.robots = ''; self.canon = ''
        self.in_title = False; self.ld = []; self.in_ld = False; self.buf = ''; self.ids = set()
    def handle_starttag(self, t, a):
        a = dict(a)
        if a.get('id'): self.ids.add(a['id'])
        if t == 'a' and a.get('href'): self.links.append(a['href'])
        if t == 'img': self.imgs.append((a.get('src') or '', a.get('alt'), a.get('width'), a.get('height')))
        if t == 'link' and a.get('rel') in ('stylesheet', 'icon', 'apple-touch-icon', 'manifest', 'preload') and a.get('href'): self.links.append(a['href'])
        if t == 'link' and a.get('rel') == 'canonical': self.canon = a.get('href', '')
        if t == 'script' and a.get('src'): self.links.append(a['src'])
        if t == 'h1': self.h1 += 1
        if t == 'title': self.in_title = True
        if t == 'meta' and a.get('name') == 'description': self.desc = a.get('content', '')
        if t == 'meta' and a.get('name') == 'robots': self.robots = a.get('content', '')
        if t == 'script' and a.get('type') == 'application/ld+json': self.in_ld = True; self.buf = ''
    def handle_endtag(self, t):
        if t == 'title': self.in_title = False
        if t == 'script' and self.in_ld: self.in_ld = False; self.ld.append(self.buf)
    def handle_data(self, d):
        if self.in_title: self.title += d
        if self.in_ld: self.buf += d

def path_of(f):
    rel = os.path.relpath(f, ROOT)
    return '/' if rel == 'index.html' else '/' + rel[:-5]

def exists(url):
    u = urlparse(url)
    if u.netloc and u.netloc not in ('fore-ladies.com', 'www.fore-ladies.com'): return True
    p = unquote(u.path)
    if p == '/' or p == '': return True
    fp = os.path.join(ROOT, p.lstrip('/'))
    if os.path.isfile(fp): return True
    if os.path.isfile(fp + '.html'): return True
    return False

def main():
    files = [f for f in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True)
             if not os.path.relpath(f, ROOT).startswith(('_build', '.git', 'node_modules'))]
    titles = collections.defaultdict(list); descs = collections.defaultdict(list)
    detail = sys.argv[1] if len(sys.argv) > 1 else None
    for f in files:
        path = path_of(f)
        p = P(); p.feed(open(f, encoding='utf-8').read())
        indexable = 'noindex' not in p.robots
        if os.path.basename(f) != '404.html':
            if p.h1 != 1: prob(f'{path}: {p.h1} <h1> elements')
            if not p.title.strip(): prob(f'{path}: missing <title>')
            if len(html.unescape(p.title)) > 60: prob(f'{path}: title longer than 60 ({len(p.title)})')
            if not p.desc: prob(f'{path}: missing meta description')
            if len(html.unescape(p.desc)) > 160: prob(f'{path}: description longer than 160')
            if indexable:
                titles[p.title].append(path); descs[p.desc].append(path)
            want = 'https://fore-ladies.com' + path
            if p.canon != want: prob(f'{path}: canonical {p.canon} != {want}')
        for l in p.links:
            if l.startswith(('mailto:', 'tel:', '#', 'javascript:')): continue
            if l.startswith('http') and 'fore-ladies.com' not in l: continue
            if not exists(l.split('#')[0].split('?')[0]): prob(f'{path}: broken link {l}')
            if re.search(r'\.html(\?|#|$)', l) and not l.startswith('http'): prob(f'{path}: internal link uses .html: {l}')
        for src, alt, w, h in p.imgs:
            if src.startswith('http') and 'fore-ladies.com' not in src: continue
            if not exists(src): prob(f'{path}: missing image {src}')
            if alt is None: prob(f'{path}: image without alt {src}')
            if not (w and h): prob(f'{path}: image without width/height {src}')
        for j in p.ld:
            try: json.loads(j)
            except Exception as e: prob(f'{path}: invalid JSON-LD ({e})')
        if detail and path == detail:
            print(f'{path}\n title: {p.title}\n desc: {p.desc}\n robots: {p.robots}\n h1: {p.h1}\n links: {len(p.links)} imgs: {len(p.imgs)} jsonld: {len(p.ld)}')
    for t, ps in titles.items():
        if len(ps) > 1: prob(f'duplicate title "{t}" on {ps[:4]}')
    for d, ps in descs.items():
        if len(ps) > 1: prob(f'duplicate description on {ps[:4]}')
    # new article word counts
    for f in glob.glob(os.path.join(ROOT, '_build', 'content', 'new', '*.html')):
        raw = open(f, encoding='utf-8').read()
        body = re.sub(r'^\s*<!--META.*?-->', '', raw, flags=re.S)
        n = len(re.sub(r'<[^>]+>', ' ', html.unescape(body)).split())
        if not 1000 <= n <= 1600: prob(f'{os.path.basename(f)}: {n} words (want 1,000–1,600)')
    # sitemap urls exist
    sm = open(os.path.join(ROOT, 'sitemap.xml')).read()
    for loc in re.findall(r'<loc>([^<]+)</loc>', sm):
        if not exists(loc): prob(f'sitemap: missing {loc}')
    print(f'checked {len(files)} html files — {len(problems)} problem(s)')
    for x in problems[:200]: print('PROBLEM', x)
    sys.exit(1 if problems else 0)

if __name__ == '__main__':
    main()
