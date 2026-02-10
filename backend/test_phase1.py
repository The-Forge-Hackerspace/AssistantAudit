"""
Test complet Phase 1 — Valide toute la chaine fonctionnelle :
  Auth → Entreprise → Site → Equipement → Audit → Campaign → Assessment → ControlResult
"""
import sys
import httpx

BASE = "http://127.0.0.1:8000/api/v1"
PASS = 0
FAIL = 0


def check(label: str, response: httpx.Response, expected: int = 200):
    global PASS, FAIL
    ok = response.status_code == expected
    tag = "[OK]" if ok else "[FAIL]"
    print(f"  {tag} {label} -> {response.status_code}", end="")
    if not ok:
        FAIL += 1
        print(f"  (expected {expected})")
        try:
            print(f"       Detail: {response.json()}")
        except Exception:
            print(f"       Body: {response.text[:200]}")
    else:
        PASS += 1
        print()
    return response


print("=" * 65)
print("  TEST PHASE 1 — Chaine complete")
print("=" * 65)

client = httpx.Client(base_url=BASE, timeout=10)

# 1. AUTH ---------------------------------------------------------------
print("\n[1] Authentification")
r = check("POST /auth/login", client.post("/auth/login", data={"username": "admin", "password": "Admin@2026!"}))
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

check("GET  /auth/me", client.get("/auth/me", headers=headers))

# 2. ENTREPRISE ---------------------------------------------------------
print("\n[2] Entreprise")
r = check("POST /entreprises", client.post("/entreprises", headers=headers, json={
    "nom": "TestCorp",
    "adresse": "10 rue de test",
    "secteur_activite": "IT",
    "contacts": [{"nom": "Jean Test", "role": "RSSI", "email": "jean@test.fr", "is_main_contact": True}],
}), 201)
ent_id = r.json()["id"]
check("GET  /entreprises", client.get("/entreprises", headers=headers))
check("GET  /entreprises/{id}", client.get(f"/entreprises/{ent_id}", headers=headers))

# 3. SITE ---------------------------------------------------------------
print("\n[3] Sites")
r = check("POST /sites", client.post("/sites", headers=headers, json={
    "nom": "Siege Paris",
    "adresse": "1 rue de Rivoli, 75001 Paris",
    "entreprise_id": ent_id,
}), 201)
site_id = r.json()["id"]
check("GET  /sites", client.get("/sites", headers=headers))
check("GET  /sites?entreprise_id=", client.get(f"/sites?entreprise_id={ent_id}", headers=headers))
check("GET  /sites/{id}", client.get(f"/sites/{site_id}", headers=headers))
r = check("PUT  /sites/{id}", client.put(f"/sites/{site_id}", headers=headers, json={"adresse": "1 place Vendome"}))

# 4. EQUIPEMENTS --------------------------------------------------------
print("\n[4] Equipements")
# Firewall
r = check("POST /equipements (firewall)", client.post("/equipements", headers=headers, json={
    "site_id": site_id,
    "type_equipement": "firewall",
    "ip_address": "10.0.0.1",
    "hostname": "FW-PARIS-01",
    "fabricant": "Fortinet",
    "os_detected": "FortiOS 7.4.1",
    "license_status": "active",
    "rules_count": 245,
}), 201)
fw_id = r.json()["id"]

# Serveur
r = check("POST /equipements (serveur)", client.post("/equipements", headers=headers, json={
    "site_id": site_id,
    "type_equipement": "serveur",
    "ip_address": "10.0.0.10",
    "hostname": "SRV-DC01",
    "fabricant": "Dell",
    "os_detected": "Windows Server 2022",
    "os_version_detail": "21H2 Build 20348.2527",
    "role_list": {"roles": ["AD DS", "DNS", "DHCP"]},
}), 201)
srv_id = r.json()["id"]

# Switch
r = check("POST /equipements (reseau)", client.post("/equipements", headers=headers, json={
    "site_id": site_id,
    "type_equipement": "reseau",
    "ip_address": "10.0.0.254",
    "hostname": "SW-CORE-01",
    "fabricant": "Cisco",
    "firmware_version": "16.12.4",
}), 201)
sw_id = r.json()["id"]

check("GET  /equipements", client.get("/equipements", headers=headers))
check("GET  /equipements?site_id=", client.get(f"/equipements?site_id={site_id}", headers=headers))
check("GET  /equipements?type=firewall", client.get("/equipements?type_equipement=firewall", headers=headers))
check("GET  /equipements/{id}", client.get(f"/equipements/{fw_id}", headers=headers))
r = check("PUT  /equipements/{id}", client.put(f"/equipements/{fw_id}", headers=headers, json={
    "status_audit": "EN_COURS",
    "notes_audit": "Audit en cours par Jean",
}))
# Vérifier les champs spécifiques
detail = r.json()
assert detail["type_equipement"] == "firewall", f"Type should be firewall, got {detail['type_equipement']}"
assert detail["rules_count"] == 245, f"rules_count should be 245, got {detail.get('rules_count')}"
print("  [OK] Champs specifiques firewall OK")
PASS += 1

# 5. AUDIT --------------------------------------------------------------
print("\n[5] Audit")
r = check("POST /audits", client.post("/audits", headers=headers, json={
    "nom_projet": "Audit Secu Q1 2026",
    "entreprise_id": ent_id,
    "objectifs": "Evaluer la posture securite",
    "limites": "Perimetre reseau interne",
}), 201)
audit_id = r.json()["id"]
check("GET  /audits", client.get("/audits", headers=headers))
check("GET  /audits/{id}", client.get(f"/audits/{audit_id}", headers=headers))

# 6. FRAMEWORKS ---------------------------------------------------------
print("\n[6] Frameworks")
check("GET  /frameworks", client.get("/frameworks", headers=headers))
r = check("GET  /frameworks/1", client.get("/frameworks/1", headers=headers))
fw_framework_id = None
# Trouver le framework firewall
r2 = client.get("/frameworks", headers=headers)
for fw in r2.json()["items"]:
    if "firewall" in fw["name"].lower():
        fw_framework_id = fw["id"]
        break
if fw_framework_id:
    print(f"  [INFO] Framework Firewall = ID {fw_framework_id}")

# 7. CAMPAIGN & ASSESSMENT -----------------------------------------------
print("\n[7] Campagne d'evaluation")
r = check("POST /assessments/campaigns", client.post("/assessments/campaigns", headers=headers, json={
    "name": "Campagne Q1 2026",
    "description": "Evaluation trimestrielle de securite",
    "audit_id": audit_id,
}), 201)
camp_id = r.json()["id"]
check("GET  /assessments/campaigns", client.get("/assessments/campaigns", headers=headers))
check("POST start campaign", client.post(f"/assessments/campaigns/{camp_id}/start", headers=headers))

print("\n[8] Assessment (Equipement x Framework)")
if fw_framework_id:
    r = check("POST /assessments", client.post(
        f"/assessments?campaign_id={camp_id}", headers=headers, json={
            "equipement_id": fw_id,
            "framework_id": fw_framework_id,
            "notes": "Firewall principal site Paris",
        }
    ), 201)
    assess_id = r.json()["id"]
    results_count = len(r.json().get("results", []))
    print(f"  [INFO] Assessment ID={assess_id}, {results_count} control results generes")

    check("GET  /assessments/{id}", client.get(f"/assessments/{assess_id}", headers=headers))

    # Mettre a jour un resultat de controle
    if results_count > 0:
        result_id = r.json()["results"][0]["id"]
        check("PUT  /assessments/results/{id}", client.put(f"/assessments/results/{result_id}", headers=headers, json={
            "status": "compliant",
            "evidence": "Firmware v7.4.1 verifie, a jour",
            "comment": "Conforme au referentiel",
        }))

# 8. Verify campaign detail
check("GET  /assessments/campaigns/{id}", client.get(f"/assessments/campaigns/{camp_id}", headers=headers))
check("POST complete campaign", client.post(f"/assessments/campaigns/{camp_id}/complete", headers=headers))

# 9. CONFLICT TESTS ------------------------------------------------------
print("\n[9] Tests de conflits / erreurs")
check("POST /sites doublon", client.post("/sites", headers=headers, json={
    "nom": "Siege Paris", "entreprise_id": ent_id,
}), 409)
check("POST /equipements IP doublon", client.post("/equipements", headers=headers, json={
    "site_id": site_id, "type_equipement": "equipement", "ip_address": "10.0.0.1",
}), 409)
check("GET  /sites/999 (404)", client.get("/sites/999", headers=headers), 404)
check("GET  /equipements/999 (404)", client.get("/equipements/999", headers=headers), 404)

# SUMMARY ----------------------------------------------------------------
print("\n" + "=" * 65)
print(f"  RESULTATS : {PASS} OK / {FAIL} FAIL")
print("=" * 65)

client.close()
sys.exit(1 if FAIL > 0 else 0)
