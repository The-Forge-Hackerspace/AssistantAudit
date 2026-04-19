"""Tests pour le calcul de progression hybride nmap."""

from app.services.scan_progress import compute_progress, reset_task


class TestPhaseProgress:
    def test_initial_state_is_zero(self):
        reset_task("t1")
        assert compute_progress("t1", []) == 0

    def test_syn_scan_phase_interpolation(self):
        reset_task("t-syn")
        # Phase SYN = 15% -> 60%
        compute_progress("t-syn", ["Initiating SYN Stealth Scan at 20:18"])
        # Intra-phase à 50% -> milieu de [15, 60] = 37
        pct = compute_progress("t-syn", ["SYN Stealth Scan Timing: About 50% done; ETC: 20:18"])
        assert 36 <= pct <= 38

    def test_phase_transition_does_not_regress(self):
        reset_task("t-trans")
        # SYN à 88%
        compute_progress("t-trans", ["Initiating SYN Stealth Scan at 20:18"])
        compute_progress("t-trans", ["SYN Stealth Scan Timing: About 88% done"])
        progress_at_88 = compute_progress("t-trans", [])
        # Service scan démarre (60-85%) -> début à 60% mais on a déjà 54%
        compute_progress("t-trans", ["Initiating Service scan at 20:19"])
        new_pct = compute_progress("t-trans", ["Service scan Timing: About 5% done"])
        assert new_pct >= progress_at_88


class TestHostsFloor:
    def test_hosts_completed_provides_floor(self):
        reset_task("t-hosts")
        compute_progress("t-hosts", ["Scanning 4 hosts [65535 ports/host]"])
        compute_progress("t-hosts", ["Stats: 0:00:05 elapsed; 1 hosts completed (4 up), 4 undergoing SYN Stealth Scan"])
        # 1/4 = 25% plancher minimum
        pct = compute_progress("t-hosts", [])
        assert pct >= 25

    def test_hosts_floor_combined_with_phase(self):
        reset_task("t-combo")
        # 254 hôtes, 100 done = 39% plancher
        compute_progress("t-combo", ["Scanning 254 hosts [1000 ports/host]"])
        compute_progress("t-combo", ["Initiating SYN Stealth Scan at 20:18"])
        compute_progress("t-combo", ["Stats: 0:00:30 elapsed; 100 hosts completed"])
        # Phase SYN à 5% -> phase_progress ≈ 17%, mais host_floor = 39%
        pct = compute_progress("t-combo", ["SYN Stealth Scan Timing: About 5% done"])
        assert pct >= 39


class TestMonotonic:
    def test_progress_never_decreases(self):
        reset_task("t-mono")
        compute_progress("t-mono", ["Initiating SYN Stealth Scan at 20:18"])
        compute_progress("t-mono", ["SYN Stealth Scan Timing: About 88% done"])
        high = compute_progress("t-mono", [])
        # Nouvelle phase à 0% — progression ne doit pas chuter
        compute_progress("t-mono", ["Initiating Service scan at 20:19"])
        low_attempt = compute_progress("t-mono", ["Service scan Timing: About 0% done"])
        assert low_attempt >= high

    def test_clamped_to_100(self):
        reset_task("t-clamp")
        compute_progress("t-clamp", ["Scanning 1 hosts"])
        compute_progress("t-clamp", ["1 hosts completed (1 up)"])
        pct = compute_progress("t-clamp", [], fallback_pct=999)
        assert pct == 100


class TestFallbackPct:
    def test_fallback_used_when_no_lines(self):
        reset_task("t-fb")
        # Pas d'init de phase -> phase par défaut [0, 100]
        # fallback 50% -> global 50%
        pct = compute_progress("t-fb", [], fallback_pct=50)
        assert pct == 50

    def test_fallback_scaled_within_detected_phase(self):
        reset_task("t-fb-phase")
        # Phase SYN détectée mais pas encore de Timing intra-phase
        compute_progress("t-fb-phase", ["Initiating SYN Stealth Scan at 20:18"])
        # fallback 60% interprété comme 60% dans [15, 60] -> 15 + 45*0.6 = 42
        pct = compute_progress("t-fb-phase", [], fallback_pct=60)
        assert 41 <= pct <= 43
