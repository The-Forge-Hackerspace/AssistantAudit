"""
Tests pour `app.core.http_helpers.safe_content_disposition` (TOS-76).

Couvre :
- AC1 : encodage RFC 5987 (`filename*=UTF-8''…`).
- AC2 : strip `\\r`, `\\n`, `"` AVANT interpolation.
- AC3 : header propre face à un filename malicieux (CRLF + Set-Cookie).
- AC4 : noms non-ASCII (accents français, kanji) restent percent-encodés.
- AC5 : un seul point de construction du header — vérifié indirectement par la route
       `api/v1/files.py::download_file` qui appelle ce helper (cf. test_files_route_uses_helper).
"""

from pathlib import Path

from app.core.http_helpers import safe_content_disposition


def test_safe_content_disposition_simple_ascii():
    """AC1 — Filename ASCII simple : header complet RFC 5987."""
    result = safe_content_disposition("rapport.pdf")
    assert result == "attachment; filename=\"rapport.pdf\"; filename*=UTF-8''rapport.pdf"


def test_safe_content_disposition_strips_crlf_and_quote():
    """AC2 + AC3 — Filename malicieux avec CRLF, quote, Set-Cookie : strippés."""
    malicious = '"; \r\nSet-Cookie: evil=1"'
    result = safe_content_disposition(malicious)
    # Aucun CR ni LF dans la valeur du header — bloque le response splitting.
    assert "\r" not in result
    assert "\n" not in result
    # Pas de double-quote injectée dans le filename ASCII fallback.
    # (Le header global contient une seule paire de quotes encadrant le fallback.)
    assert result.count('"') == 2
    # Le percent-encoding doit contenir les caractères encodés (pas l'attaque brute en clair).
    assert "%0D" not in result  # CR strippé, pas encodé
    assert "%0A" not in result  # LF strippé, pas encodé


def test_safe_content_disposition_french_accents():
    """AC4 — Accents français : percent-encoded UTF-8 dans filename*."""
    result = safe_content_disposition("café.pdf")
    # caf%C3%A9 = 'é' en UTF-8 percent-encoded.
    assert "filename*=UTF-8''caf%C3%A9.pdf" in result
    # Fallback ASCII garde un placeholder pour les vieux navigateurs.
    assert 'filename="caf' in result


def test_safe_content_disposition_kanji():
    """AC4 — Kanji : percent-encoded UTF-8 valide."""
    result = safe_content_disposition("報告.txt")
    # 報 = E5 A0 B1, 告 = E5 91 8A en UTF-8.
    assert "filename*=UTF-8''%E5%A0%B1%E5%91%8A.txt" in result


def test_safe_content_disposition_emoji():
    """AC4 — Emoji (4 octets UTF-8) : percent-encoded valide."""
    result = safe_content_disposition("rapport_🔥.pdf")
    # 🔥 = F0 9F 94 A5 en UTF-8.
    assert "filename*=UTF-8''rapport_%F0%9F%94%A5.pdf" in result


def test_safe_content_disposition_empty_returns_default():
    """Filename vide ou None : nom par défaut `download`."""
    assert safe_content_disposition("") == "attachment; filename=\"download\"; filename*=UTF-8''download"
    assert safe_content_disposition(None) == "attachment; filename=\"download\"; filename*=UTF-8''download"


def test_safe_content_disposition_inline_disposition():
    """`disposition=inline` est respecté (preview de fichier)."""
    result = safe_content_disposition("image.png", disposition="inline")
    assert result.startswith("inline; filename=")


def test_files_route_uses_helper_not_raw_fstring():
    """AC5 — La route `files.py::download_file` doit utiliser le helper, pas une f-string brute.

    Garde-fou contre les régressions : si quelqu'un réintroduit `f'attachment; filename="{filename}"'`
    dans un router de l'API v1, ce test échoue.
    """
    api_v1 = Path(__file__).resolve().parent.parent / "app" / "api" / "v1"
    forbidden = 'f\'attachment; filename="{filename}"\''
    for py_file in api_v1.glob("*.py"):
        content = py_file.read_text()
        assert forbidden not in content, (
            f"Header injection vulnerability re-introduced in {py_file.name}: "
            f"use safe_content_disposition() from app.core.http_helpers instead."
        )
    # Sanity check — files.py importe et utilise bien le helper.
    files_py = (api_v1 / "files.py").read_text()
    assert "safe_content_disposition" in files_py
