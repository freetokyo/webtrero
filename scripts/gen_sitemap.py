#!/usr/bin/env python3
"""Generate sitemap.xml for all supported languages.

Usage:
    python3 web/scripts/gen_sitemap.py
"""

import os

BASE_URL = "https://trero.app"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# All language codes in display order
ALL_LANGS = [
    "ja", "en",
    "da", "de", "es", "fr", "it", "ko", "nb", "nl", "pl", "sv", "zh-Hans", "zh-Hant",
    "ar", "ca", "cs", "el", "fi", "he", "hi", "hr", "hu", "id",
    "ms", "pt-BR", "pt-PT", "ro", "ru", "sk", "th", "tr", "uk", "vi",
]

REGIONAL_VARIANTS = {
    "en-AU": "en",
    "en-CA": "en",
    "en-GB": "en",
    "es-MX": "es",
    "fr-CA": "fr",
}

PAGES = ["index.html", "support.html", "privacy_policy.html", "terms.html"]


def page_url(lang, page):
    slug = "" if page == "index.html" else page
    if lang == "ja":
        return f"{BASE_URL}/{slug}"
    return f"{BASE_URL}/{lang}/{slug}" if slug else f"{BASE_URL}/{lang}/"


def page_priority(lang, page):
    if page == "index.html":
        if lang == "ja":
            return "1.0"
        if lang == "en":
            return "0.9"
        return "0.8"
    if page == "support.html":
        return "0.5" if lang in ("ja", "en") else "0.4"
    # privacy_policy, terms
    return "0.3" if lang in ("ja", "en") else "0.2"


def page_changefreq(page):
    if page == "index.html":
        return "weekly"
    if page == "support.html":
        return "monthly"
    return "yearly"


def all_hreflang_entries(page):
    entries = []
    for lang in ALL_LANGS:
        entries.append((lang, page_url(lang, page)))
    for variant, base_lang in REGIONAL_VARIANTS.items():
        entries.append((variant, page_url(base_lang, page)))
    entries.append(("x-default", page_url("ja", page)))
    return entries


def url_block(lang, page, indent="  "):
    loc = page_url(lang, page)
    lines = [f"{indent}<url>"]
    lines.append(f"{indent}  <loc>{loc}</loc>")
    for hreflang, href in all_hreflang_entries(page):
        lines.append(f'{indent}  <xhtml:link rel="alternate" hreflang="{hreflang}" href="{href}" />')
    lines.append(f"{indent}  <changefreq>{page_changefreq(page)}</changefreq>")
    lines.append(f"{indent}  <priority>{page_priority(lang, page)}</priority>")
    lines.append(f"{indent}</url>")
    return "\n".join(lines)


def main():
    out_path = os.path.join(BASE, "sitemap.xml")

    sections = []
    sections.append('<?xml version="1.0" encoding="UTF-8"?>')
    sections.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"')
    sections.append('        xmlns:xhtml="http://www.w3.org/1999/xhtml">')
    sections.append("")

    for lang in ALL_LANGS:
        lang_label = lang if lang != "ja" else "Japanese (default)"
        sections.append(f"  <!-- {lang_label} -->")
        for page in PAGES:
            sections.append(url_block(lang, page))
        sections.append("")

    sections.append("</urlset>")

    content = "\n".join(sections) + "\n"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    total_urls = len(ALL_LANGS) * len(PAGES)
    print(f"Wrote {out_path}")
    print(f"  {len(ALL_LANGS)} languages × {len(PAGES)} pages = {total_urls} URL entries")


if __name__ == "__main__":
    main()
