"""
Helpers HTTP partagés pour les routes de téléchargement de fichiers.

Centralise la construction du header `Content-Disposition` selon la
RFC 5987 (filename* en UTF-8 percent-encoded) avec un fallback ASCII
pour les vieux navigateurs. Strip systématique des caractères CR/LF/quote
avant interpolation pour éviter l'injection de header
(cf. rapport ln-620 finding S-003 — Header injection).
"""

from urllib.parse import quote


def safe_content_disposition(filename: str | None, disposition: str = "attachment") -> str:
    """Construit un header `Content-Disposition` RFC 5987 sans risque d'injection.

    Strip CR/LF/quote du filename AVANT toute interpolation pour neutraliser
    les tentatives d'injection de header (`\\r\\n` permettrait d'injecter
    un faux `Set-Cookie` ou de scinder la réponse HTTP). Encode ensuite le
    filename en UTF-8 percent-encoded selon RFC 5987 (`filename*=UTF-8''…`)
    avec un fallback ASCII (`filename="…"`) pour les vieux navigateurs qui
    ne comprennent pas `filename*`.

    Args:
        filename: nom de fichier brut tel que conservé en base. Peut être
            None ou vide — un nom par défaut `download` est alors utilisé.
        disposition: `attachment` (download forcé) ou `inline` (preview).

    Returns:
        Header value prêt à être posé dans `headers={"Content-Disposition": …}`.
    """
    safe = (filename or "download").replace("\r", "").replace("\n", "").replace('"', "")
    if not safe:
        safe = "download"
    # Fallback ASCII pour vieux navigateurs : remplace les non-ASCII par '_'.
    ascii_fallback = safe.encode("ascii", "replace").decode("ascii").replace("?", "_")
    # RFC 5987 : percent-encode en UTF-8, safe='' force l'encodage des caractères ASCII spéciaux.
    quoted = quote(safe, safe="")
    return f"{disposition}; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quoted}"
