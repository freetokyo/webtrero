#!/usr/bin/env python3
"""Generate static HTML pages for all supported languages.

Usage:
    python3 web/scripts/gen_langs.py
Generates web/{lang}/ directories for every language defined in web/translations/.
"""

import json
import os
import re
from bs4 import BeautifulSoup, Comment

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANS_DIR = os.path.join(BASE, "translations")
PAGES = ["index.html", "support.html", "privacy_policy.html", "terms.html"]

# All language codes (ja = default/root, en = already generated via gen_en.py)
ALL_LANGS = ["ja", "en", "de", "da", "es", "fr", "it", "ko", "nb", "nl", "pl", "sv", "zh-Hans", "zh-Hant"]

def page_url(lang, page):
    """Return the canonical URL for a given lang/page combo."""
    base = "https://trero.app"
    slug = "" if page == "index.html" else page
    if lang == "ja":
        return f"{base}/{slug}"
    return f"{base}/{lang}/{slug}" if slug else f"{base}/{lang}/"

def all_hreflang_links(page):
    """Return list of (hreflang, href) for every language + x-default."""
    links = []
    for lang in ALL_LANGS:
        links.append((lang, page_url(lang, page)))
    links.append(("x-default", page_url("ja", page)))
    return links

def transform(src_path, page, lang, t):
    """Transform source HTML into a static single-language page."""
    with open(src_path, encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")
    meta = t.get("meta", {}).get(page, {})
    strings = t.get("strings", {})
    blocks = t.get("blocks", {}).get(page, {})

    # 1. lang attribute
    soup.html["lang"] = lang

    # 2. title
    if meta.get("title") and soup.title:
        soup.title.string = meta["title"]

    # 3. meta description
    desc_tag = soup.find("meta", attrs={"name": "description"})
    if desc_tag and meta.get("description"):
        desc_tag["content"] = meta["description"]

    # 4. canonical
    canonical_url = page_url(lang, page)
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical:
        canonical["href"] = canonical_url

    # 5. hreflang — rebuild with all languages
    for link in soup.find_all("link", attrs={"rel": "alternate"}):
        link.decompose()
    if canonical:
        insert_after = canonical
    else:
        insert_after = soup.find("link", attrs={"rel": "canonical"}) or soup.head
    for hreflang, href in all_hreflang_links(page):
        new_link = soup.new_tag("link", rel="alternate", hreflang=hreflang, href=href)
        if insert_after and hasattr(insert_after, "insert_after"):
            insert_after.insert_after(new_link)
            insert_after = new_link
        else:
            soup.head.append(new_link)

    # 6. OG / Twitter meta
    og_map = {
        "og:title": meta.get("og_title", meta.get("title", "")),
        "og:description": meta.get("og_description", meta.get("description", "")),
        "og:url": canonical_url,
        "og:locale": t.get("og_locale", "en_US"),
    }
    for prop, val in og_map.items():
        if val:
            tag = soup.find("meta", attrs={"property": prop})
            if tag:
                tag["content"] = val
    tw_map = {
        "twitter:title": og_map["og:title"],
        "twitter:description": og_map["og:description"],
    }
    for name, val in tw_map.items():
        if val:
            tag = soup.find("meta", attrs={"name": name})
            if tag:
                tag["content"] = val

    # 7. data-en elements: replace with translated text (fallback to data-en)
    for el in soup.find_all(attrs={"data-en": True}):
        en_val = el.get("data-en", "")
        translated = strings.get(en_val, en_val)
        el.clear()
        inner = BeautifulSoup(translated, "html.parser")
        for child in inner.contents:
            el.append(child.__copy__())
        del el["data-en"]
        if el.has_attr("data-ja"):
            del el["data-ja"]

    # 8. lang-en blocks: replace inner HTML with translated version (fallback to English)
    for i, el in enumerate(soup.find_all(class_="lang-en")):
        key = str(i)
        if key in blocks:
            el.clear()
            inner = BeautifulSoup(blocks[key], "html.parser")
            for child in inner.contents:
                el.append(child.__copy__())
        classes = [c for c in el.get("class", []) if c != "lang-en"]
        if classes:
            el["class"] = classes
        else:
            del el["class"]

    # 9. Remove lang-ja elements
    for el in soup.find_all(class_="lang-ja"):
        el.decompose()

    # 10. Remove lang-toggle
    for el in soup.find_all(class_="lang-toggle"):
        el.decompose()

    # 11. Remove applyLang / META JS blocks
    for script in soup.find_all("script"):
        src = script.string or ""
        if any(x in src for x in ["applyLang", "META =", "detectInitialLang", "copyURL"]):
            script.decompose()

    # 12. JSON-LD inLanguage
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        src = script.string or ""
        if '"inLanguage"' in src:
            src = re.sub(r'"inLanguage":\s*\[.*?\]', f'"inLanguage": "{lang}"', src)
            src = src.replace('"inLanguage": "en"', f'"inLanguage": "{lang}"')
            script.string = src

    # 13. apple-itunes-app app-argument for index
    if page == "index.html":
        banner = soup.find("meta", attrs={"name": "apple-itunes-app"})
        if banner:
            banner["content"] = f"app-id=6760746164, app-argument={canonical_url}"

    return str(soup)


def main():
    trans_files = [f for f in os.listdir(TRANS_DIR) if f.endswith(".json")]
    langs = [f[:-5] for f in trans_files]
    print(f"Found translations: {sorted(langs)}\n")

    for lang in sorted(langs):
        with open(os.path.join(TRANS_DIR, f"{lang}.json"), encoding="utf-8") as f:
            t = json.load(f)

        out_dir = os.path.join(BASE, lang)
        os.makedirs(out_dir, exist_ok=True)

        for page in PAGES:
            src = os.path.join(BASE, page)
            dst = os.path.join(out_dir, page)
            result = transform(src, page, lang, t)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(result)
            print(f"  {lang}/{page}")

    print(f"\nDone: {len(langs)} languages × {len(PAGES)} pages = {len(langs)*len(PAGES)} files")


if __name__ == "__main__":
    main()
