#!/usr/bin/env python3
"""Generate English-only static HTML files for web/en/ from web/*.html."""

import os
import re
import sys
from bs4 import BeautifulSoup, Comment

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE)
OUT_DIR = os.path.join(BASE, "en")

# English meta values extracted from each file's META / applyLang
EN_META = {
    "index.html": {
        "title": "Trero | Workout Tracker & Gym Log App for iPhone",
        "description": "Trero is an iPhone workout tracker for people who want faster gym logging, clearer goal tracking, progress analysis, body metrics, and Apple Watch support in one app.",
        "og_title": "Trero | Workout Tracker & Gym Log App for iPhone",
        "og_description": "Check previous records, reuse past values, track exercise goals, review body metrics, and log sets from Apple Watch in one app.",
        "canonical": "https://trero.app/en/",
        "hreflang_ja": "https://trero.app/",
        "hreflang_en": "https://trero.app/en/",
        "og_url": "https://trero.app/en/",
    },
    "support.html": {
        "title": "Support & FAQ | Trero Workout Tracker App",
        "description": "Read Trero support answers covering account setup, workout logging, goals, body metrics, Apple Health, Apple Watch, notifications, and Free vs Pro.",
        "og_title": "Support & FAQ | Trero Workout Tracker App",
        "og_description": "Read Trero support answers covering account setup, workout logging, goals, body metrics, Apple Health, Apple Watch, notifications, and Free vs Pro.",
        "canonical": "https://trero.app/en/support.html",
        "hreflang_ja": "https://trero.app/support.html",
        "hreflang_en": "https://trero.app/en/support.html",
        "og_url": "https://trero.app/en/support.html",
    },
    "privacy_policy.html": {
        "title": "Privacy Policy | Trero – Workout Tracker App",
        "description": "Read Trero's Privacy Policy to understand what data we collect, how third-party services are used, and how to delete your account.",
        "og_title": "Privacy Policy | Trero – Workout Tracker App",
        "og_description": "Read Trero's Privacy Policy to understand what data we collect, how third-party services are used, and how to delete your account.",
        "canonical": "https://trero.app/en/privacy_policy.html",
        "hreflang_ja": "https://trero.app/privacy_policy.html",
        "hreflang_en": "https://trero.app/en/privacy_policy.html",
        "og_url": "https://trero.app/en/privacy_policy.html",
    },
    "terms.html": {
        "title": "Terms of Service | Trero – Workout Tracker App",
        "description": "Review Trero's Terms of Service covering accounts, plans, prohibited conduct, user data rights, and subscription billing terms.",
        "og_title": "Terms of Service | Trero – Workout Tracker App",
        "og_description": "Review Trero's Terms of Service covering accounts, plans, prohibited conduct, user data rights, and subscription billing terms.",
        "canonical": "https://trero.app/en/terms.html",
        "hreflang_ja": "https://trero.app/terms.html",
        "hreflang_en": "https://trero.app/en/terms.html",
        "og_url": "https://trero.app/en/terms.html",
    },
}


def transform(src_path, filename):
    meta = EN_META[filename]
    with open(src_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")

    # 1. lang attribute
    soup.html["lang"] = "en"

    # 2. title
    if soup.title:
        soup.title.string = meta["title"]

    # 3. meta description
    desc = soup.find("meta", attrs={"name": "description"})
    if desc:
        desc["content"] = meta["description"]

    # 4. canonical
    canonical = soup.find("link", attrs={"rel": "canonical"})
    if canonical:
        canonical["href"] = meta["canonical"]

    # 5. hreflang
    for link in soup.find_all("link", attrs={"rel": "alternate"}):
        hreflang = link.get("hreflang", "")
        if hreflang == "ja":
            link["href"] = meta["hreflang_ja"]
        elif hreflang == "en":
            link["href"] = meta["hreflang_en"]
        elif hreflang == "x-default":
            link["href"] = meta["hreflang_ja"]

    # 6. OG tags
    og_map = {
        "og:title": meta["og_title"],
        "og:description": meta["og_description"],
        "og:url": meta["og_url"],
        "og:locale": "en_US",
        "og:locale:alternate": "ja_JP",
    }
    for prop, val in og_map.items():
        tag = soup.find("meta", attrs={"property": prop})
        if tag:
            tag["content"] = val

    # 7. Twitter
    tw_map = {
        "twitter:title": meta["og_title"],
        "twitter:description": meta["og_description"],
    }
    for name, val in tw_map.items():
        tag = soup.find("meta", attrs={"name": name})
        if tag:
            tag["content"] = val

    # 8. data-en elements: set innerHTML to data-en value, remove both attrs
    for el in soup.find_all(attrs={"data-en": True}):
        en_val = el.get("data-en", "")
        # Clear children and set inner HTML from data-en
        el.clear()
        inner = BeautifulSoup(en_val, "html.parser")
        for child in inner.contents:
            el.append(child.__copy__())
        del el["data-en"]
        if el.has_attr("data-ja"):
            del el["data-ja"]

    # 9. Remove .lang-ja elements entirely
    for el in soup.find_all(class_="lang-ja"):
        el.decompose()

    # 10. .lang-en elements: remove the class (make them always visible)
    for el in soup.find_all(class_="lang-en"):
        classes = el.get("class", [])
        classes = [c for c in classes if c != "lang-en"]
        if classes:
            el["class"] = classes
        else:
            del el["class"]

    # 11. Remove .lang-toggle div (language switch buttons)
    for el in soup.find_all(class_="lang-toggle"):
        el.decompose()

    # 12. Remove scripts containing applyLang / META = / detectInitialLang / copyURL
    for script in soup.find_all("script"):
        src = script.string or ""
        if any(x in src for x in ["applyLang", "META =", "detectInitialLang", "copyURL"]):
            script.decompose()

    # 13. Remove share section (only makes sense on index with copyURL)
    #     Keep it if it exists but without the JS — the copy button just won't work.
    #     No action needed since JS is removed.

    # 14. JSON-LD: update inLanguage if present
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        src = script.string or ""
        if '"inLanguage"' in src:
            src = src.replace('"inLanguage": ["ja", "en"]', '"inLanguage": "en"')
            src = src.replace('"inLanguage": ["ja","en"]', '"inLanguage": "en"')
            script.string = src

    # 15. apple-itunes-app: update app-argument for index
    if filename == "index.html":
        banner = soup.find("meta", attrs={"name": "apple-itunes-app"})
        if banner:
            banner["content"] = 'app-id=6760746164, app-argument=https://trero.app/en/'

    return str(soup)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    files = list(EN_META.keys())
    for filename in files:
        src = os.path.join(SRC_DIR, filename)
        dst = os.path.join(OUT_DIR, filename)
        print(f"  {filename} -> en/{filename}", end=" ... ")
        result = transform(src, filename)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(result)
        print("done")
    print(f"\nGenerated {len(files)} files in web/en/")


if __name__ == "__main__":
    main()
