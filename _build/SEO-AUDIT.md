# fore-ladies.com — SEO audit ও rebuild (অক্টোবর ২০২৬)

> এই repo public, তাই এখানে Search Console-এর কোনো সংখ্যা রাখা হয়নি। সংখ্যা ও trend থাকবে private report doc-এ।

## ১. আগের অবস্থা (live site, ২৫ অক্টোবর ২০২৬)

- Site ছিল পুরোনো **BigCommerce store-এর static কপি**, Hostinger-এ host করা। Cart, login, checkout, contact form, wishlist — কিছুই কাজ করত না।
- Exit popup-এ checkout discount code (CART10) দেখাত, অথচ checkout নেই।
- **Product-এর মূল ছবি** আসত `cdn11.bigcommerce.com` থেকে — সেই CDN বন্ধ, তাই প্রায় সব product page-এ ছবি ভাঙা ছিল। 343 product-এর মধ্যে মাত্র 98টির ছবি site-এর নিজের folder-এ পাওয়া গেছে।
- Category page-এর product card-এ কোনো ছবি ছিল না (scrape-এ মুছে গিয়েছিল)।
- **Sitemap-এ URL `.html` ছাড়া**, কিন্তু canonical tag `.html` সহ — Google দুই রকম সংকেত পাচ্ছিল। www ও non-www দুটোই 200 দিত (redirect নেই)।
- পুরোনো store-এর URL শেষে `/` দিত; এখন সেগুলো **500 error** দিত (যেমন `/abacus-clark-...-red/`)।
- Crawl-এ 1,586 URL: 799টি 200, **779টি ভাঙা internal link (404)**, 8টি 500। Sort/filter/page/search variant মিলিয়ে ~300 duplicate-ধাঁচের page index-যোগ্য ছিল।
- কয়েকটি page সম্পূর্ণ ফাঁকা (scrape ব্যর্থ) কিন্তু 200 দিত: ৪টি blog post, কিছু product, tag page।
- Footer-এর social link Fore Ladies-এর নয়, **BigCommerce-এর নিজের** Facebook/Instagram/TikTok-এ যেত।
- Menu ও blog-এ `foreladiesgolf.com`-এর link — সেই domain এখন **অস্তিত্বহীন (NXDOMAIN)**, কেউ কিনে spam বসাতে পারে। আরও মৃত/সন্দেহজনক external link: bit.ly (১৬টি), lorenaslinks.org (domain suspended), golfforeafrica.org-এর পুরোনো page (404), charitynavigator-এর পুরোনো profile link, epnygolf.com (brand বন্ধ হচ্ছে), colorstreet.com promo।
- প্রতি page-এর HTML 150–280 KB, ৫০টির বেশি বাইরের script (Klaviyo, Justuno, Smile.io, Shogun, OptinMonster, Facebook, Bing, Affiliatly…)। GA4 শুধু homepage-এ।
- কোনো page-এ Organization/Article schema ছিল না; product page-এর পুরোনো Product schema-য় ভুল URL (trailing slash) ও মেয়াদোত্তীর্ণ price।
- Spam/adult check: কোনো লুকানো link, injected script বা জুয়া/adult content পাওয়া যায়নি ("casino" শব্দটি একটি LPGA/Symetra tour post-এর স্বাভাবিক উল্লেখ)।
- Search Console: Domain property `fore-ladies.com` verify করা ছিল না; পরে URL-prefix property `https://fore-ladies.com/` verified পাওয়া গেছে (নিচে Launch দেখুন)।

## ২. যা করা হয়েছে

### Site rebuild (সব URL ও ছবির path একই)
- Python generator `_build/build.py` + content JSON (`_build/content/`)। 467টি page, এক CSS, ছোট JS, self-hosted Poppins/Arimo font, lazy image + width/height, সব page-এ একটি GA4 tag।
- Brand রঙ (কালো + গোলাপি #e9446e), লোগো ও font রাখা হয়েছে।
- Product page: ছবি (যেখানে আছে), brand, sizes, color, "last listed price", বিবরণ, fit টিপস, সম্পর্কিত style guide, একই category-র আরও product। স্পষ্ট নোট: online checkout এই site-এ এখন নেই। ছবি না থাকলে brand-রঙের placeholder।
- Category/brand page: সব variant-এর product একত্র করে এক page-এ; লম্বা বিবরণ grid-এর নিচে; সম্পর্কিত guide।
- প্রতি page: unique title (≤60) ও description (≤160), canonical, OG/Twitter, একটি H1, breadcrumb; schema — Organization, WebSite, BreadcrumbList, CollectionPage + ItemList, ItemPage, Blog/BlogPosting (about/mentions)।
- Thin category (০–২ product) ও একই item-এর duplicate listing: `noindex, follow`, sitemap থেকে বাদ।
- `sitemap.xml` (শুধু 200 + indexable, image সহ), `robots.txt`, `feed.xml`, `404.html`, HTML sitemap (`/sitemap`), favicon/manifest।
- `.htaccess`: `_build`, `.git`, `data` 403; www → non-www; `.html` → clean URL; trailing slash → clean; `?m=1`/sort query → clean; পুরোনো store-এর search, sort/page/price/filter variant, cart/login/checkout, rss/xmlsitemap — সব **এক hop**-এ 301। পুরোনো 623টি ফাঁকা/merge/হারানো URL প্রাসঙ্গিক page-এ 301।
- Local Apache-এ পরীক্ষা: sitemap-এর 406 URL সব 200; পুরোনো 1,586 URL-এর মধ্যে 853টি এক hop-এ 200-এ যায়, 453টি সরাসরি 200, বাকি 404গুলো আগেও 404 ছিল।

### Content
- **১৩টি নতুন article** (প্রতিটি 1,000–1,300 শব্দ, FAQ, table, internal link, title card): outfit guide, dress code, skort length, skort vs skirt vs shorts, cold weather, hot weather ও UPF, golf shoes, পোশাক পরিষ্কার, golf dress বাছাই, tennis vs golf পোশাক, golf trip packing list, প্রথম lesson/driving range, rain gear।
- পুরোনো ২টি post-এ আসল নতুন section ("Updated October 2026" নোট সহ): golf etiquette (dress code), golf bag essentials (weather kit)।
- Our Story page থেকে এমন feature-এর প্রতিশ্রুতি সরানো হয়েছে যা এখন নেই (checkout donation, "complete outfit" button, email list); brand তালিকায় brand page-এর link।
- Play for P.I.N.K. page-এ নোট: পুরোনো partnership; checkout ও discount code এখন সক্রিয় নয়।
- মৃত/ঝুঁকিপূর্ণ external link সরানো; `foreladiesgolf.com`-এর link যেখানে সম্ভব নিজের page-এ বদলানো।
- `_build/profile.md` (brand voice) ও `_build/entity-map.md` (যাচাই করা Wikipedia link)।

## ৩. 54-checkpoint score: **86/100** (rebuild-এর পর)

Pass 34, Partial 10, Fail 1, Owner 5, N/A 4। বিস্তারিত টেবিল report doc-এর Audit tab-এ।

বাকি প্রধান কাজ:
1. Search Console data দেখে (প্রতি সোম ও বৃহস্পতি) title/description, content ও internal link update।
2. Contact email/ফোন দিলে contact page ও E-E-A-T সম্পূর্ণ হবে।
3. ছবিহীন 245টি product-এর ছবি (owner-এর কাছে থাকলে) যোগ করা।
4. Competitor gap বিশ্লেষণ (GSC query জমা হলে)।

## ৪. Launch (২৫ অক্টোবর ২০২৬)
- Hostinger Git auto-deploy connect হয়েছে; নতুন site live — homepage, 13টি নতুন guide, 2টি update ও `sitemap.xml` সব 200।
- Search Console-এ URL-prefix property `https://fore-ladies.com/` verified; `sitemap.xml` resubmit; 18টি URL-এর indexing request (কোনো quota error নেই)। বিস্তারিত `_build/plan/GSC-PROGRESS.md`-এ, সংখ্যা private report doc-এ।
- নিয়মিত নতুন article-এর জন্য scheduled task চালু: সাধারণ মাসে প্রতি 3 দিনে, Nov–Dec ও Mar–May-তে একদিন পরপর (`_build/plan/CONTENT-CALENDAR.md`)। Search Console run প্রতি সোম ও বৃহস্পতি।
- Index হতে সাধারণত কয়েক সপ্তাহ লাগে; ranking বা indexing-এর নিশ্চয়তা দেওয়া যায় না।

## ৫. Owner-এর করণীয়
- Contact তথ্য (email) ও আসল social profile link দিন।
- ঐচ্ছিক: Domain property (`sc-domain:fore-ladies.com`) verify করতে DNS-এ Google TXT record।
- Search Console-এর Sitemaps থেকে পুরোনো `/sitemap.php` ও `/sitemap` সরিয়ে দিতে পারেন (এগুলো আগের store-এর)।
- সোম/বৃহস্পতির Search Console run-এর সময় (সকাল 09:46) computer ও Claude desktop app চালু রাখুন।
- Repo চাইলে Private করুন (তখন Search Console data repo-তে রাখা যাবে)।
