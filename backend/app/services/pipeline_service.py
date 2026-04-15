"""
PipelineService — Orchestration du pipeline multi-étapes (TOS-13 / US009).

Enchaîne scan Nmap → création d'équipements → collectes SSH/WinRM pour un
sous-réseau. Ce module contient aussi les helpers purs (détection de profil)
pour rester facilement testables.
"""

from __future__ import annotations

from typing import Literal, Optional

from ..models.scan import ScanHost

# Profils supportés par la détection automatique.
# Les profils "stormshield" / "fortigate" existent côté collecteur mais ne
# sont pas auto-détectables de façon fiable depuis un scan Nmap : ils doivent
# être choisis explicitement par l'auditeur.
AutoCollectProfile = Literal["linux_server", "windows_server", "opnsense"]


# Ports "signaux" pour la détection.
_SSH_PORT = 22
_WINRM_HTTP_PORT = 5985
_WINRM_HTTPS_PORT = 5986


def _open_port_numbers(host: ScanHost) -> set[int]:
    """Retourne l'ensemble des numéros de ports dans l'état `open` pour un hôte."""
    ports: set[int] = set()
    for p in host.ports or []:
        if p.state == "open" and p.port_number is not None:
            ports.add(int(p.port_number))
    return ports


def _matches(value: Optional[str], *needles: str) -> bool:
    """True si `value` (case-insensitive) contient au moins un des `needles`."""
    if not value:
        return False
    haystack = value.lower()
    return any(n in haystack for n in needles)


def _host_signals(host: ScanHost) -> dict:
    """Agrège les signaux textuels utiles à la détection (OS + banners services)."""
    os_guess = host.os_guess or ""
    # Concatène les `product`/`version`/`extra_info` des ports pour détecter
    # OPNsense/FreeBSD via les banners SSH ou HTTP.
    banners: list[str] = []
    for p in host.ports or []:
        if p.state != "open":
            continue
        for field in (p.product, p.version, p.extra_info, p.service_name):
            if field:
                banners.append(field)
    return {"os_guess": os_guess, "banners": " ".join(banners)}


def detect_collect_profile(host: ScanHost) -> AutoCollectProfile | None:
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
