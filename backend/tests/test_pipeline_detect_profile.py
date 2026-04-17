"""Tests unitaires du helper `detect_collect_profile` (TOS-13 / T003).

Le helper est pur (ni DB ni I/O) : on construit des dicts NmapHost in-memory
pour simuler la sortie JSON d'un agent Nmap, ce qui garde ces tests rapides
et isoles.
"""

from __future__ import annotations

from app.services.pipeline_service import NmapHost, detect_collect_profile


def _make_host(
    *,
    os_guess: str | None = None,
    ports: list[tuple[int, str]] | None = None,
    banners: dict[int, str] | None = None,
) -> NmapHost:
    """Construit un NmapHost (dict) avec des ports ouverts."""
    port_list = []
    for port_num, state in ports or []:
        banner = (banners or {}).get(port_num) or ""
        port_list.append(
            {
                "port": port_num,
                "protocol": "tcp",
                "state": state,
                "service": banner,
            }
        )
    return {
        "ip": "10.0.0.1",
        "hostname": "",
        "mac": "",
        "vendor": "",
        "os": os_guess or "",
        "ports": port_list,
    }


class TestDetectCollectProfile:
    def test_linux_ssh_open_returns_linux_server(self):
        host = _make_host(os_guess="Linux 5.15 (Ubuntu 22.04)", ports=[(22, "open")])
        assert detect_collect_profile(host) == "linux_server"

    def test_windows_with_winrm_returns_windows_server(self):
        host = _make_host(os_guess="Windows Server 2019", ports=[(5985, "open")])
        assert detect_collect_profile(host) == "windows_server"

    def test_windows_with_winrm_https_returns_windows_server(self):
        host = _make_host(os_guess="Microsoft Windows 10", ports=[(5986, "open")])
        assert detect_collect_profile(host) == "windows_server"

    def test_opnsense_takes_precedence_over_linux(self):
        # OPNsense expose SSH (22) et tourne sur FreeBSD : on doit reconnaitre
        # le profil specifique, pas retomber sur linux_server.
        host = _make_host(os_guess="FreeBSD 13 (OPNsense 23.7)", ports=[(22, "open")])
        assert detect_collect_profile(host) == "opnsense"

    def test_opnsense_detected_via_banner_when_os_absent(self):
        host = _make_host(
            os_guess=None,
            ports=[(22, "open")],
            banners={22: "OpenSSH 8.8 (OPNsense)"},
        )
        assert detect_collect_profile(host) == "opnsense"

    def test_ssh_only_without_os_falls_back_to_linux(self):
        host = _make_host(os_guess=None, ports=[(22, "open")])
        assert detect_collect_profile(host) == "linux_server"

    def test_winrm_only_without_os_falls_back_to_windows(self):
        host = _make_host(os_guess=None, ports=[(5985, "open")])
        assert detect_collect_profile(host) == "windows_server"

    def test_closed_ssh_port_is_ignored(self):
        host = _make_host(os_guess="Linux", ports=[(22, "closed")])
        assert detect_collect_profile(host) is None

    def test_no_usable_port_returns_none(self):
        # Seulement HTTP/HTTPS ouverts — ni SSH ni WinRM.
        host = _make_host(os_guess="Linux", ports=[(80, "open"), (443, "open")])
        assert detect_collect_profile(host) is None

    def test_empty_ports_returns_none(self):
        host = _make_host(os_guess="Windows", ports=[])
        assert detect_collect_profile(host) is None

    def test_windows_without_winrm_returns_none(self):
        # Windows detecte mais WinRM ferme et SSH absent : rien d'exploitable.
        host = _make_host(os_guess="Windows Server", ports=[(3389, "open")])
        assert detect_collect_profile(host) is None

    def test_both_ssh_and_winrm_linux_os_prefers_linux(self):
        host = _make_host(
            os_guess="Linux Ubuntu 22.04",
            ports=[(22, "open"), (5985, "open")],
        )
        assert detect_collect_profile(host) == "linux_server"

    def test_both_ssh_and_winrm_windows_os_prefers_windows(self):
        host = _make_host(
            os_guess="Windows Server 2022",
            ports=[(22, "open"), (5985, "open")],
        )
        assert detect_collect_profile(host) == "windows_server"
