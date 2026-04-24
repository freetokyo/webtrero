#!/usr/bin/env python3
"""Remove guest account references from translation JSON files.

Run from the repo root:
    python3 web/scripts/update_no_guest.py
"""

import json
import os
import re
from bs4 import BeautifulSoup

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRANS_DIR = os.path.join(BASE, "translations")

LANGS = ["da", "de", "es", "fr", "it", "ko", "nb", "nl", "pl", "sv", "zh-Hans", "zh-Hant"]

# ---------------------------------------------------------------------------
# Hardcoded translations for new / updated string keys
# ---------------------------------------------------------------------------
NEW_TRANSLATIONS = {
    "Accounts": {
        "da": "Konti",
        "de": "Konten",
        "es": "Cuentas",
        "fr": "Comptes",
        "it": "Account",
        "ko": "계정",
        "nb": "Kontoer",
        "nl": "Accounts",
        "pl": "Konta",
        "sv": "Konton",
        "zh-Hans": "账号",
        "zh-Hant": "帳號",
    },
    "Q. Do I need to create an account?": {
        "da": "Sp. Skal jeg oprette en konto?",
        "de": "F. Muss ich ein Konto erstellen?",
        "es": "P. ¿Necesito crear una cuenta?",
        "fr": "Q. Dois-je créer un compte ?",
        "it": "D. Devo creare un account?",
        "ko": "Q. 계정을 만들어야 하나요?",
        "nb": "Sp. Må jeg opprette en konto?",
        "nl": "V. Moet ik een account aanmaken?",
        "pl": "P. Czy muszę założyć konto?",
        "sv": "F. Måste jag skapa ett konto?",
        "zh-Hans": "问：需要创建账号吗？",
        "zh-Hant": "問：需要建立帳號嗎？",
    },
    "Yes. Please sign up with your email address or Apple ID on the sign-in screen.": {
        "da": "Ja. Tilmeld dig med din e-mailadresse eller Apple ID på log ind-skærmen.",
        "de": "Ja. Bitte registriere dich mit deiner E-Mail-Adresse oder Apple ID im Anmeldebildschirm.",
        "es": "Sí. Regístrate con tu dirección de correo electrónico o Apple ID en la pantalla de inicio de sesión.",
        "fr": "Oui. Veuillez vous inscrire avec votre adresse e-mail ou votre identifiant Apple sur l'écran de connexion.",
        "it": "Sì. Registrati con il tuo indirizzo e-mail o Apple ID nella schermata di accesso.",
        "ko": "네. 로그인 화면에서 이메일 주소 또는 Apple ID로 등록해 주세요.",
        "nb": "Ja. Registrer deg med e-postadressen din eller Apple ID på påloggingsskjermen.",
        "nl": "Ja. Meld je aan met je e-mailadres of Apple ID op het aanmeldingsscherm.",
        "pl": "Tak. Zarejestruj się swoim adresem e-mail lub Apple ID na ekranie logowania.",
        "sv": "Ja. Registrera dig med din e-postadress eller ditt Apple-ID på inloggningsskärmen.",
        "zh-Hans": "是的。请在登录界面使用电子邮件地址或 Apple ID 注册。",
        "zh-Hant": "是的。請在登入畫面使用電子郵件地址或 Apple ID 註冊。",
    },
    "Email / Apple authentication": {
        "da": "E-mail / Apple-godkendelse",
        "de": "E-Mail / Apple-Anmeldung",
        "es": "Autenticación por correo electrónico / Apple",
        "fr": "Authentification par e-mail / Apple",
        "it": "Autenticazione e-mail / Apple",
        "ko": "이메일 / Apple 인증",
        "nb": "E-post / Apple-autentisering",
        "nl": "E-mail / Apple-authenticatie",
        "pl": "Uwierzytelnianie e-mail / Apple",
        "sv": "E-post / Apple-autentisering",
        "zh-Hans": "电子邮件 / Apple 身份验证",
        "zh-Hant": "電子郵件 / Apple 驗證",
    },
}

# guest/member substring in analytics value → sign-in state replacement
GUEST_MEMBER_PATTERNS = {
    "da": ("gæst/medlem", "loginstatus"),
    "de": ("Gast/Mitglied", "Anmeldestatus"),
    "fr": ("invité/membre", "état de connexion"),
    "ko": ("게스트/회원", "로그인 상태"),
    "nb": ("gjest/medlem", "påloggingsstatus"),
    "nl": ("gast/lid", "aanmeldstatus"),
    "pl": ("gość/członek", "stan logowania"),
    "sv": ("gäst/medlem", "inloggningsstatus"),
    "zh-Hans": ("访客/会员", "登录状态"),
    "zh-Hant": ("訪客/會員", "登入狀態"),
    # es and it don't have explicit guest/member in the value, no replacement needed
}

# New first <li> for terms block 0 (account types without guest mode)
NEW_TERMS_LI = {
    "da": "<li>Brugere kan bruge appen via e-mailadresse eller Apple ID.</li>",
    "de": "<li>Nutzer können über E-Mail-Adresse oder Apple ID auf die App zugreifen.</li>",
    "es": "<li>Los usuarios pueden acceder a la aplicación mediante dirección de correo electrónico o Apple ID.</li>",
    "fr": "<li>Les utilisateurs peuvent accéder à l'application via leur adresse e-mail ou leur identifiant Apple.</li>",
    "it": "<li>Gli utenti possono accedere all'app tramite indirizzo e-mail o Apple ID.</li>",
    "ko": "<li>사용자는 이메일 주소 또는 Apple ID를 통해 앱을 이용할 수 있습니다.</li>",
    "nb": "<li>Brukere kan bruke appen via e-postadresse eller Apple ID.</li>",
    "nl": "<li>Gebruikers kunnen de app gebruiken via e-mailadres of Apple ID.</li>",
    "pl": "<li>Użytkownicy mogą korzystać z aplikacji za pomocą adresu e-mail lub Apple ID.</li>",
    "sv": "<li>Användare kan komma åt appen via e-postadress eller Apple ID.</li>",
    "zh-Hans": "<li>用户可通过电子邮件地址或 Apple ID 使用本应用。</li>",
    "zh-Hant": "<li>用戶可透過電子郵件地址或 Apple ID 使用本應用程式。</li>",
}

# ---------------------------------------------------------------------------
# Old / new string keys
# ---------------------------------------------------------------------------
OLD_ANALYTICS_KEY = (
    "Event information such as sign-in type, onboarding completion, workout start/finish, "
    "goal creation/update, body-record save, paywall exposure, and share actions, plus "
    "usage-state properties such as guest/member and plan type."
)
NEW_ANALYTICS_KEY = (
    "Event information such as sign-in type, onboarding completion, workout start/finish, "
    "goal creation/update, body-record save, paywall exposure, and share actions, plus "
    "usage-state properties such as sign-in state and plan type."
)

OLD_SUPPORT_INTRO_KEY = (
    "Guest mode, free-plan limits, how previous values work, Apple Health integration, "
    "Apple Watch support, and whether CSV export is available are the topics people most "
    "often check before purchase."
)
NEW_SUPPORT_INTRO_KEY = (
    "Free-plan limits, how previous values work, Apple Health integration, Apple Watch "
    "support, and whether CSV export is available are the topics people most often check "
    "before purchase."
)

KEYS_TO_DELETE = {
    "Can I use it as a guest?",
    "Yes. You can still log workouts as a guest. If you want to use another device or plan "
    "to keep using the app long term, moving later to an email or Apple account is safer.",
}

# old key → new key (value will be provided via NEW_TRANSLATIONS or kept/modified)
RENAME_MAP = {
    "Accounts & Guest Mode": "Accounts",
    "Q. Can I use the app without creating an account?": "Q. Do I need to create an account?",
    "Yes. Guest mode is supported. You can keep logging as a guest, but if you want to use "
    "another device or keep data for long-term use, we recommend later moving to an email "
    "or Apple account.": (
        "Yes. Please sign up with your email address or Apple ID on the sign-in screen."
    ),
    "Email / Apple / guest authentication": "Email / Apple authentication",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def update_strings(strings: dict, lang: str) -> dict:
    new_strings = {}

    for key, val in strings.items():
        if key in KEYS_TO_DELETE:
            continue

        if key in RENAME_MAP:
            new_key = RENAME_MAP[key]
            # Use hardcoded translation if available; otherwise derive from old value
            trans = NEW_TRANSLATIONS.get(new_key, {})
            new_strings[new_key] = trans.get(lang, val)

        elif key == OLD_ANALYTICS_KEY:
            # Replace guest/member with sign-in state equivalent
            new_val = val
            if lang in GUEST_MEMBER_PATTERNS:
                old_pattern, replacement = GUEST_MEMBER_PATTERNS[lang]
                new_val = val.replace(old_pattern, replacement)
            new_strings[NEW_ANALYTICS_KEY] = new_val

        elif key == OLD_SUPPORT_INTRO_KEY:
            # Strip the first phrase (e.g. "Gastmodus, " or "访客模式、")
            # Handle both Western ", " and CJK "、" separators
            new_val = re.sub(r'^[^，,、]+[，,、]\s*', '', val)
            if new_val:
                new_val = new_val[0].upper() + new_val[1:]
            else:
                new_val = val
            new_strings[NEW_SUPPORT_INTRO_KEY] = new_val

        else:
            new_strings[key] = val

    return new_strings


def update_index_block_11(html_content: str) -> str:
    """Remove the first <li> (guest mode) from index lang-en block 11."""
    soup = BeautifulSoup(html_content, "html.parser")
    lis = soup.find_all("li")
    if lis:
        lis[0].decompose()
    return str(soup)


def update_terms_block_0(html_content: str, lang: str) -> str:
    """Replace first <li> (account types) and remove third <li> (guest data)."""
    soup = BeautifulSoup(html_content, "html.parser")
    lis = soup.find_all("li")

    # Replace first li with new account types text (without guest mode)
    if lis:
        new_li_html = NEW_TERMS_LI.get(
            lang, "<li>Users may access the app via email address or Apple ID.</li>"
        )
        new_li_soup = BeautifulSoup(new_li_html, "html.parser")
        lis[0].replace_with(new_li_soup.find("li"))

    # Re-find lis after replacement, then remove the third one (guest data transfer)
    lis = soup.find_all("li")
    if len(lis) >= 3:
        lis[2].decompose()

    return str(soup)


def update_blocks(blocks: dict, lang: str) -> dict:
    new_blocks = {}
    for page, page_blocks in blocks.items():
        new_page_blocks = {}
        for idx, html_content in page_blocks.items():
            if page == "index.html" and idx == "11":
                new_page_blocks[idx] = update_index_block_11(html_content)
            elif page == "terms.html" and idx == "0":
                new_page_blocks[idx] = update_terms_block_0(html_content, lang)
            else:
                new_page_blocks[idx] = html_content
        new_blocks[page] = new_page_blocks
    return new_blocks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    for lang in LANGS:
        filepath = os.path.join(TRANS_DIR, f"{lang}.json")
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        data["strings"] = update_strings(data.get("strings", {}), lang)
        data["blocks"] = update_blocks(data.get("blocks", {}), lang)

        # Write back with 2-space indent, ensure_ascii=False
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Verify JSON is valid
        with open(filepath, encoding="utf-8") as f:
            json.load(f)

        print(f"  {lang}: OK")

    print("\nAll translation files updated successfully.")


if __name__ == "__main__":
    main()
