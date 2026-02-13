"""
Package collectors : collecte d'informations via SSH, WinRM, LDAP, etc.
"""
from .ssh_collector import collect_via_ssh, SSHCollectResult
from .winrm_collector import collect_via_winrm, WinRMCollectResult

__all__ = [
    "collect_via_ssh",
    "SSHCollectResult",
    "collect_via_winrm",
    "WinRMCollectResult",
]
