"""Détection de profil de collecte à partir d'un host Nmap (TOS-13).

Helpers purs (sans I/O DB) pour normaliser les hôtes scannés et déterminer
le profil de collecte applicable. Découpe issue de TOS-85.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict

# Profils supportés par la détection automatique.
# Les profils "stormshield" / "fortigate" existent côté collecteur mais ne
# sont pas auto-détectables de façon fiable depuis un scan Nmap : ils doivent
# être choisis explicitement par l'auditeur.
AutoCollectProfile = Literal["linux_server", "windows_server", "opnsense"]


# Ports "signaux" pour la détection.
_SSH_PORT = 22
_WINRM_HTTP_PORT = 5985
_WINRM_HTTPS_PORT = 5986


class NmapPort(TypedDict, total=False):
    port: int
    protocol: str
    state: str
    service: str


class NmapHost(TypedDict, total=False):
    """Hôte Nmap normalisé à partir du JSON renvoyé par l'agent.

    Les agents renvoient soit des clés courtes (ip/mac/os/port) soit les
    clés longues historiques (ip_address/mac_address/os_guess/port_number).
    `_normalize_host` unifie les deux formats.
    """

    ip: str
    hostname: str
    mac: str
    vendor: str
    os: str
    ports: list[NmapPort]


def _normalize_host(raw: dict[str, Any]) -> NmapHost:
    """Transforme un host brut agent en NmapHost normalisé."""
    raw_ports = raw.get("ports") or []
    ports: list[NmapPort] = []
    for p in raw_ports:
        if not isinstance(p, dict):
            continue
        ports.append(
            {
                "port": int(p.get("port") or p.get("port_number") or 0),
                "protocol": str(p.get("proto") or p.get("protocol") or "tcp"),
                "state": str(p.get("state") or ""),
                "service": str(p.get("service") or p.get("service_name") or ""),
            }
        )
    return {
        "ip": str(raw.get("ip") or raw.get("ip_address") or ""),
        "hostname": str(raw.get("hostname") or ""),
        "mac": str(raw.get("mac") or raw.get("mac_address") or ""),
        "vendor": str(raw.get("vendor") or ""),
        "os": str(raw.get("os") or raw.get("os_guess") or ""),
        "ports": ports,
    }


def _open_port_numbers(host: NmapHost) -> set[int]:
    """Retourne l'ensemble des numéros de ports dans l'état `open` pour un hôte."""
    ports: set[int] = set()
    for p in host.get("ports") or []:
        if p.get("state") == "open" and p.get("port"):
            ports.add(int(p["port"]))
    return ports


def _matches(value: Optional[str], *needles: str) -> bool:
    """True si `value` (case-insensitive) contient au moins un des `needles`."""
    if not value:
        return False
    haystack = value.lower()
    return any(n in haystack for n in needles)


def _host_signals(host: NmapHost) -> dict:
    """Agrège les signaux textuels utiles à la détection (OS + banners services)."""
    os_guess = host.get("os") or ""
    # Concatène les services des ports pour détecter OPNsense/FreeBSD via les
    # banners SSH ou HTTP. L'agent fusionne déjà product/version/extra_info
    # dans le champ `service`.
    banners: list[str] = []
    for p in host.get("ports") or []:
        if p.get("state") != "open":
            continue
        svc = p.get("service")
        if svc:
            banners.append(svc)
    return {"os_guess": os_guess, "banners": " ".join(banners)}


def detect_collect_profile(host: NmapHost) -> AutoCollectProfile | None:
    """
    Détermine le profil de collecte approprié pour un hôte découvert.

    Règles (dans l'ordre) :
      1. OPNsense/pfSense/FreeBSD + SSH ouvert → ``"opnsense"`` (plus spécifique
         que linux_server, doit donc être testé en premier).
      2. Windows + WinRM (5985/5986) ouvert → ``"windows_server"``.
      3. Linux/Unix + SSH (22) ouvert → ``"linux_server"``.
      4. SSH seul sans OS identifié → ``"linux_server"`` (fallback raisonnable).
      5. WinRM seul sans OS identifié → ``"windows_server"``.
      6. Aucun port compatible → ``None`` (l'hôte sera skippé).

    Retourne ``None`` si aucun profil n'est applicable : l'orchestrateur
    incrémentera alors ``hosts_skipped`` et continuera avec les autres hôtes.
    """
    signals = _host_signals(host)
    os_text = signals["os_guess"]
    banners_text = signals["banners"]
    open_ports = _open_port_numbers(host)

    has_ssh = _SSH_PORT in open_ports
    has_winrm = _WINRM_HTTP_PORT in open_ports or _WINRM_HTTPS_PORT in open_ports

    is_opnsense = _matches(os_text, "opnsense", "pfsense", "freebsd") or _matches(
        banners_text, "opnsense", "pfsense"
    )
    is_windows = _matches(os_text, "windows", "microsoft")
    is_linux = _matches(os_text, "linux", "ubuntu", "debian", "centos", "redhat", "rhel", "fedora", "alpine")

    # 1. OPNsense / pfSense — doit passer avant linux (SSH aussi ouvert)
    if is_opnsense and has_ssh:
        return "opnsense"

    # 2. Windows confirmé + WinRM ouvert
    if is_windows and has_winrm:
        return "windows_server"

    # 3. Linux confirmé + SSH ouvert
    if is_linux and has_ssh:
        return "linux_server"

    # 4. SSH seul sans OS clair — on tente linux_server
    if has_ssh and not has_winrm:
        return "linux_server"

    # 5. WinRM seul sans OS clair — on tente windows_server
    if has_winrm and not has_ssh:
        return "windows_server"

    # 6. Rien d'exploitable
    return None


# Profil de collecte → (methode de collecte, port par defaut, type equipement)
_PROFILE_METHOD: dict[AutoCollectProfile, tuple[str, int, str]] = {
    "linux_server": ("ssh", 22, "serveur"),
    "opnsense": ("ssh", 22, "firewall"),
    "windows_server": ("winrm", 5985, "serveur"),
}
