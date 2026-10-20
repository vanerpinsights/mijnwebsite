#!/usr/bin/env python3
"""Bouwt de website naar de map dist/.

Gebruik:  python3 build.py
Daarna lokaal bekijken:  python3 -m http.server 8000 --directory dist
en open http://localhost:8000

Teksten aanpassen: src/i18n/nl.json, en.json, de.json
Instellingen (boekingslink, statistieken): site.json
Geen extra pakketten nodig, alleen Python 3.
"""
import datetime
import hashlib
import html
import json
import re
import shutil
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"
STATIC = ROOT / "static"
DIST = ROOT / "dist"

FLAGS = {
    "nl": '<svg class="flag" viewBox="0 0 9 6" aria-hidden="true"><rect width="9" height="6" fill="#21468B"/><rect width="9" height="4" fill="#fff"/><rect width="9" height="2" fill="#AE1C28"/></svg>',
    "en": '<svg class="flag" viewBox="0 0 60 30" aria-hidden="true"><clipPath id="uk-s"><path d="M0,0 v30 h60 v-30 z"/></clipPath><clipPath id="uk-t"><path d="M30,15 h30 v15 z v15 h-30 z h-30 v-15 z v-15 h30 z"/></clipPath><g clip-path="url(#uk-s)"><path d="M0,0 v30 h60 v-30 z" fill="#012169"/><path d="M0,0 L60,30 M60,0 L0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 L60,30 M60,0 L0,30" clip-path="url(#uk-t)" stroke="#C8102E" stroke-width="4"/><path d="M30,0 v30 M0,15 h60" stroke="#fff" stroke-width="10"/><path d="M30,0 v30 M0,15 h60" stroke="#C8102E" stroke-width="6"/></g></svg>',
    "de": '<svg class="flag" viewBox="0 0 5 3" aria-hidden="true"><rect width="5" height="3" fill="#FFCE00"/><rect width="5" height="2" fill="#DD0000"/><rect width="5" height="1" fill="#000"/></svg>',
}

MONTHS = {
    "nl": ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"],
}

# Paginanaam -> pad binnen een taal ("" = homepage)
PAGES = {"home": "", "privacy": "privacy/"}

TOKEN = re.compile(r"\{\{\{\s*([\w]+)\s*\}\}\}|\{\{\s*([\w]+)\s*\}\}")


def render(template, ctx, name="template"):
    def sub(m):
        raw_key, esc_key = m.group(1), m.group(2)
        key = raw_key or esc_key
        if key not in ctx:
            raise KeyError(f"{name}: onbekende sleutel '{key}'")
        val = str(ctx[key])
        return val if raw_key else html.escape(val, quote=True)
    return TOKEN.sub(sub, template)


def url_for(lang, page, cfg):
    prefix = "" if lang == cfg["default_language"] else f"{lang}/"
    return "/" + prefix + PAGES[page]


def nice_date(iso, lang):
    d = datetime.date.fromisoformat(iso)
    if lang == "en":
        return f"{d.day} {MONTHS['en'][d.month - 1]} {d.year}"
    if lang == "de":
        return f"{d.day}. {MONTHS['de'][d.month - 1]} {d.year}"
    return f"{d.day} {MONTHS['nl'][d.month - 1]} {d.year}"


def main():
    cfg = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    langs = cfg["languages"]
    tr = {l: json.loads((SRC / "i18n" / f"{l}.json").read_text(encoding="utf-8")) for l in langs}

    # Controle: alle talen hebben dezelfde sleutels
    keys = set(tr[cfg["default_language"]])
    for l in langs:
        missing = keys - set(tr[l])
        if missing:
            raise SystemExit(f"{l}.json mist: {', '.join(sorted(missing))}")

    layout = (SRC / "templates" / "layout.html").read_text(encoding="utf-8")
    bodies = {p: (SRC / "templates" / f"{p}.html").read_text(encoding="utf-8") for p in list(PAGES) + ["404"]}

    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(STATIC, DIST)
    build_id = hashlib.sha1((STATIC / "assets" / "style.css").read_bytes()).hexdigest()[:8]
    base = cfg["base_url"].rstrip("/")

    analytics = ""
    if cfg.get("plausible_domain"):
        analytics = f'<script defer data-domain="{html.escape(cfg["plausible_domain"])}" src="https://plausible.io/js/script.js"></script>'

    def context(lang, page_id, page_key):
        t = tr[lang]
        ctx = dict(t)
        ctx.update({
            "lang": lang,
            "base_url": base,
            "email": cfg["email"],
            "phone_display": cfg["phone_display"],
            "phone_intl": cfg["phone_intl"],
            "linkedin": cfg["linkedin"],
            "kvk_number": cfg["kvk"],
            "year": datetime.date.today().year,
            "build_id": build_id,
            "page_id": page_id,
            "home_url": url_for(lang, "home", cfg),
            "privacy_url": url_for(lang, "privacy", cfg),
            "analytics": analytics,
            "head_extra": "",
            "robots_meta": "",
            "booking_service": cfg.get("booking_service", ""),
            "privacy_updated": cfg["privacy_updated"],
            "privacy_updated_display": nice_date(cfg["privacy_updated"], lang),
        })
        # Plan een kennismaking: echte boekingslink, of anders een voorbereide e-mail
        if cfg.get("booking_url"):
            ctx["booking_href"] = cfg["booking_url"]
            ctx["booking_target"] = ' target="_blank" rel="noopener"'
        else:
            subj = urllib.parse.quote(t["booking_subject"])
            body = urllib.parse.quote(urllib.parse.unquote(t["booking_body"]))
            ctx["booking_href"] = f"mailto:{cfg['email']}?subject={subj}&body={body}"
            ctx["booking_target"] = ""

        # HTML-blokken in de vertalingen kunnen zelf {{email}} e.d. bevatten
        for k, v in list(ctx.items()):
            if isinstance(v, str) and k.startswith("privacy_") and "{{" in v:
                ctx[k] = render(v, ctx, f"{lang}.{k}")
        ctx["privacy_booking_block"] = ctx["privacy_booking"] if cfg.get("booking_url") else ""
        ctx["privacy_analytics_block"] = ctx["privacy_analytics_on"] if analytics else ctx["privacy_analytics_off"]

        # Taalknoppen: link naar dezelfde pagina in de andere taal
        links = []
        for l in langs:
            cur = ' aria-current="true"' if l == lang else ""
            href = url_for(l, page_key, cfg) if page_key else url_for(l, "home", cfg)
            links.append(
                f'<a class="lang-btn" href="{href}" hreflang="{l}" lang="{l}"{cur} '
                f'title="{html.escape(tr[l]["_name"])}" aria-label="{html.escape(tr[l]["_name"])}">'
                f'{FLAGS[l]}<span>{l.upper()}</span></a>'
            )
        ctx["lang_switch"] = "\n          ".join(links)

        if page_key:
            ctx["canonical"] = base + url_for(lang, page_key, cfg)
            alt = [f'<link rel="alternate" hreflang="{l}" href="{base}{url_for(l, page_key, cfg)}">' for l in langs]
            alt.append(f'<link rel="alternate" hreflang="x-default" href="{base}{url_for(cfg["default_language"], page_key, cfg)}">')
            ctx["hreflang_links"] = "\n  ".join(alt)
        else:
            ctx["canonical"] = base + "/404.html"
            ctx["hreflang_links"] = ""
        return ctx

    def write(path, text):
        out = DIST / path.lstrip("/")
        if path.endswith("/"):
            out = out / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        return out

    jsonld = {
        "@context": "https://schema.org",
        "@type": "ProfessionalService",
        "name": "Van Erp Insights",
        "url": base + "/",
        "logo": base + "/assets/img/logo.png",
        "image": base + "/assets/img/wim-1400.jpg",
        "email": cfg["email"],
        "telephone": cfg["phone_intl"],
        "founder": {"@type": "Person", "name": "Wim van Erp", "sameAs": [cfg["linkedin"]]},
        "sameAs": [cfg["linkedin"]],
        "knowsAbout": ["Salesforce", "Apex", "Salesforce Flow", "Sales Cloud", "Service Cloud",
                       "Marketing Cloud", "Data 360", "Copado", "AI", "Claude", "Gemini", "SAP",
                       "Microsoft Office", "Google Workspace"],
        "areaServed": "NL",
    }

    count = 0
    for lang in langs:
        t = tr[lang]
        # Homepage
        ctx = context(lang, "home", "home")
        ctx["page_title"] = t["title"]
        ctx["page_description"] = t["description"]
        ctx["head_extra"] = '<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False) + "</script>"
        ctx["content"] = render(bodies["home"], ctx, "home.html")
        write(url_for(lang, "home", cfg), render(layout, ctx, "layout.html")); count += 1

        # Privacy
        ctx = context(lang, "privacy", "privacy")
        ctx["page_title"] = f'{t["privacy_title"]} | Van Erp Insights'
        ctx["page_description"] = t["privacy_meta"]
        ctx["content"] = render(bodies["privacy"], ctx, "privacy.html")
        write(url_for(lang, "privacy", cfg), render(layout, ctx, "layout.html")); count += 1

    # 404 (Nederlands, met links naar de homepage)
    ctx = context(cfg["default_language"], "404", None)
    ctx["page_title"] = f'{tr["nl"]["nf_title"]} | Van Erp Insights'
    ctx["page_description"] = tr["nl"]["nf_text"]
    ctx["robots_meta"] = '<meta name="robots" content="noindex">'
    ctx["content"] = render(bodies["404"], ctx, "404.html")
    write("/404.html", render(layout, ctx, "layout.html")); count += 1

    # sitemap.xml met taalvarianten
    today = datetime.date.today().isoformat()
    urls = []
    for page in PAGES:
        for lang in langs:
            alts = "".join(
                f'\n    <xhtml:link rel="alternate" hreflang="{l}" href="{base}{url_for(l, page, cfg)}"/>' for l in langs
            )
            urls.append(f"  <url>\n    <loc>{base}{url_for(lang, page, cfg)}</loc>\n    <lastmod>{today}</lastmod>{alts}\n  </url>")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(urls) + "\n</urlset>\n", encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n", encoding="utf-8")
    (DIST / "site.webmanifest").write_text(json.dumps({
        "name": "Van Erp Insights", "short_name": "Van Erp Insights", "start_url": "/",
        "display": "browser", "background_color": "#F8FBFB", "theme_color": "#002140",
        "icons": [{"src": "/assets/img/icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "/assets/img/icon-512.png", "sizes": "512x512", "type": "image/png"}],
    }, indent=2), encoding="utf-8")

    print(f"Klaar: {count} pagina's in {DIST}")


if __name__ == "__main__":
    main()
