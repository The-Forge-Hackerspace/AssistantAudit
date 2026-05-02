"""Tests des helpers de masquage PII (TOS-82)."""

from app.core.logging_config import hash_username, mask_email, mask_ip


def test_hash_username_deterministic_and_short():
    """SHA-256 prefix de 12 chars, déterministe pour la même entrée."""
    h = hash_username("alice")
    assert len(h) == 12
    assert h == hash_username("alice")
    # Doit être différent d'une autre entrée
    assert h != hash_username("bob")


def test_hash_username_empty_returns_empty():
    assert hash_username("") == ""
    assert hash_username(None) == ""


def test_mask_email_normal():
    assert mask_email("user@example.com") == "u***@example.com"


def test_mask_email_short_local_part():
    """Local-part d'un seul caractère reste partiellement masqué."""
    assert mask_email("a@example.com") == "a***@example.com"


def test_mask_email_invalid_returns_empty():
    assert mask_email("") == ""
    assert mask_email(None) == ""
    assert mask_email("no-at-sign") == ""


def test_mask_ip_ipv4_zeros_last_octet():
    assert mask_ip("192.168.1.42") == "192.168.1.0"
    assert mask_ip("10.0.0.255") == "10.0.0.0"


def test_mask_ip_invalid_returns_empty():
    assert mask_ip("") == ""
    assert mask_ip(None) == ""
    assert mask_ip("not-an-ip") == ""


def test_mask_ip_ipv6_keeps_first_three_segments():
    """IPv6 : conserve les 48 premiers bits, reset le reste."""
    masked = mask_ip("2001:db8:abcd:1234:5678:9abc:def0:1234")
    assert masked.startswith("2001:0db8:abcd:")
    assert masked.endswith(":0:0:0:0:0")
