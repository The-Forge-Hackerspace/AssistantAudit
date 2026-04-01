"""
Package collectors : collecte d'informations via SSH, WinRM, LDAP, etc.
"""
from .ssh_collector import SSHCollectResult, collect_via_ssh
from .winrm_collector import WinRMCollectResult, collect_via_winrm

__all__ = [
    "collect_via_ssh",
    "SSHCollectResult",
    "collect_via_winrm",
    "WinRMCollectResult",
]
