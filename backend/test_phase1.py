"""
Test complet Phase 1 — Valide toute la chaine fonctionnelle :
  Auth → Entreprise → Site → Equipement → Audit → Campaign → Assessment → ControlResult → Score
  + contrôle d'accès par rôle (lecteur / auditeur / admin)
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
print("  TEST PHASE 1 — Chaine complete + Roles + Scoring")
print("=" * 65)

client = httpx.Client(base_url=BASE, timeout=10)

# 1. AUTH ---------------------------------------------------------------
print("\n[1] Authentification")
r = check("POST /auth/login (admin)", client.post("/auth/login", data={"username": "admin", "password": "Admin@2026!"}))
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

check("GET  /auth/me", client.get("/auth/me", headers=headers))

# Créer un auditeur et un lecteur pour tester les rôles
check("POST /auth/register (auditeur)", client.post("/auth/register", headers=headers, json={
    "username": "auditeur1", "email": "auditeur@test.fr", "password": "Audit@2026!", "role": "auditeur",
}), 201)
check("POST /auth/register (lecteur)", client.post("/auth/register", headers=headers, json={
    "username": "lecteur1", "email": "lecteur@test.fr", "password": "Lect@2026!", "role": "lecteur",
}), 201)

# Login auditeur
r = client.post("/auth/login", data={"username": "auditeur1", "password": "Audit@2026!"})
auditeur_headers = {"Authorization": f"Bearer " + r.json()["access_token"]}

# Login lecteur
r = client.post("/auth/login", data={"username": "lecteur1", "password": "Lect@2026!"})
lecteur_headers = {"Authorization": f"Bearer " + r.json()["access_token"]}

# 2. ENTREPRISE ---------------------------------------------------------
print("\n[2] Entreprise")
r = check("POST /entreprises (admin)", client.post("/entreprises", headers=headers, json={
    "nom": "TestCorp",
    "adresse": "10 rue de test",
    "secteur_activite": "IT",
    "contacts": [{"nom": "Jean Test", "role": "RSSI", "email": "jean@test.fr", "is_main_contact": True}],
}), 201)
ent_id = r.json()["id"]
check("GET  /entreprises (lecteur)", client.get("/entreprises", headers=lecteur_headers))
check("POST /entreprises (lecteur=403)", client.post("/entreprises", headers=lecteur_headers, json={
    "nom": "Blocked",
}), 403)

# 3. SITE ---------------------------------------------------------------
print("\n[3] Sites")
r = check("POST /sites (auditeur)", client.post("/sites", headers=auditeur_headers, json={
    "nom": "Siege Paris",
    "adresse": "1 rue de Rivoli, 75001 Paris",
    "entreprise_id": ent_id,
}), 201)
site_id = r.json()["id"]
check("GET  /sites (lecteur)", client.get("/sites", headers=lecteur_headers))
check("DELETE /sites (lecteur=403)", client.delete(f"/sites/{site_id}", headers=lecteur_headers), 403)
check("DELETE /sites (auditeur=403)", client.delete(f"/sites/{site_id}", headers=auditeur_headers), 403)

# 4. EQUIPEMENTS --------------------------------------------------------
print("\n[4] Equipements")
r = check("POST /equipements (firewall)", client.post("/equipements", headers=auditeur_headers, json={
    "site_id": site_id, "type_equipement": "firewall",
    "ip_address": "10.0.0.1", "hostname": "FW-PARIS-01",
    "fabricant": "Fortinet", "os_detected": "FortiOS 7.4.1",
    "license_status": "active", "rules_count": 245,
}), 201)
fw_id = r.json()["id"]

r = check("POST /equipements (serveur)", client.post("/equipements", headers=auditeur_headers, json={
    "site_id": site_id, "type_equipement": "serveur",
    "ip_address": "10.0.0.10", "hostname": "SRV-DC01",
    "fabricant": "Dell", "os_detected": "Windows Server 2022",
    "os_version_detail": "21H2 Build 20348.2527",
    "role_list": {"roles": ["AD DS", "DNS", "DHCP"]},
}), 201)
srv_id = r.json()["id"]

check("GET  /equipements (lecteur)", client.get("/equipements", headers=lecteur_headers))
check("PUT  /equipements (auditeur)", client.put(f"/equipements/{fw_id}", headers=auditeur_headers, json={
    "status_audit": "EN_COURS",
}))
check("DELETE /equipements (auditeur=403)", client.delete(f"/equipements/{fw_id}", headers=auditeur_headers), 403)

# 5. AUDIT --------------------------------------------------------------
print("\n[5] Audit")
r = check("POST /audits (auditeur)", client.post("/audits", headers=auditeur_headers, json={
    "nom_projet": "Audit Secu Q1 2026",
    "entreprise_id": ent_id,
    "objectifs": "Evaluer la posture securite",
}), 201)
audit_id = r.json()["id"]
check("GET  /audits/{id}", client.get(f"/audits/{audit_id}", headers=headers))
check("DELETE /audits (auditeur=403)", client.delete(f"/audits/{audit_id}", headers=auditeur_headers), 403)

# 6. FRAMEWORKS ---------------------------------------------------------
print("\n[6] Frameworks")
r = check("GET  /frameworks", client.get("/frameworks", headers=headers))
fw_framework_id = None
for fw in r.json()["items"]:
    if "firewall" in fw["name"].lower():
        fw_framework_id = fw["id"]
        break
print(f"  [INFO] Framework Firewall = ID {fw_framework_id}")

# 7. CAMPAIGN & ASSESSMENT -----------------------------------------------
print("\n[7] Campagne d'evaluation")
r = check("POST /assessments/campaigns", client.post("/assessments/campaigns", headers=auditeur_headers, json={
    "name": "Campagne Q1 2026",
    "description": "Evaluation trimestrielle",
    "audit_id": audit_id,
}), 201)
camp_id = r.json()["id"]
check("POST start campaign", client.post(f"/assessments/campaigns/{camp_id}/start", headers=auditeur_headers))
check("POST campaign (lecteur=403)", client.post("/assessments/campaigns", headers=lecteur_headers, json={
    "name": "Blocked", "audit_id": audit_id,
}), 403)

print("\n[8] Assessment (Equipement x Framework)")
r = check("POST /assessments", client.post(
    f"/assessments?campaign_id={camp_id}", headers=auditeur_headers, json={
        "equipement_id": fw_id,
        "framework_id": fw_framework_id,
        "notes": "Firewall principal site Paris",
    }
), 201)
assess_id = r.json()["id"]
results = r.json().get("results", [])
results_count = len(results)
print(f"  [INFO] Assessment ID={assess_id}, {results_count} control results generes")

# Mettre a jour quelques resultats (mix de statuts)
if results_count >= 5:
    check("PUT result compliant", client.put(f"/assessments/results/{results[0]['id']}", headers=auditeur_headers, json={
        "status": "compliant", "evidence": "Firmware OK", "comment": "Conforme",
    }))
    check("PUT result compliant", client.put(f"/assessments/results/{results[1]['id']}", headers=auditeur_headers, json={
        "status": "compliant", "evidence": "SSH only",
    }))
    check("PUT result non_compliant", client.put(f"/assessments/results/{results[2]['id']}", headers=auditeur_headers, json={
        "status": "non_compliant", "evidence": "Regle any-any trouvee", "remediation_note": "Supprimer regle",
    }))
    check("PUT result partially", client.put(f"/assessments/results/{results[3]['id']}", headers=auditeur_headers, json={
        "status": "partially_compliant", "evidence": "Partiellement ok",
    }))
    check("PUT result N/A", client.put(f"/assessments/results/{results[4]['id']}", headers=auditeur_headers, json={
        "status": "not_applicable",
    }))

# 9. SCORING -------------------------------------------------------------
print("\n[9] Scoring")
r = check("GET /assessments/{id}/score", client.get(f"/assessments/{assess_id}/score", headers=headers))
score_data = r.json()
print(f"  [INFO] Score = {score_data.get('score')}%  "
      f"({score_data.get('compliant')} OK / {score_data.get('non_compliant')} KO / "
      f"{score_data.get('partially_compliant')} partiel / {score_data.get('not_assessed')} non eval)")
assert score_data["compliant"] == 2, f"Expected 2 compliant, got {score_data['compliant']}"
assert score_data["non_compliant"] == 1, f"Expected 1 non_compliant, got {score_data['non_compliant']}"
assert score_data["by_severity"] != {}, "by_severity should not be empty"
print("  [OK] Score detail coherent")
PASS += 1

r = check("GET /campaigns/{id}/score", client.get(f"/assessments/campaigns/{camp_id}/score", headers=headers))

check("GET /assessments/999/score (404)", client.get("/assessments/999/score", headers=headers), 404)

# Complete campaign
check("POST complete campaign", client.post(f"/assessments/campaigns/{camp_id}/complete", headers=auditeur_headers))

# 10. CONFLICT TESTS ------------------------------------------------------
print("\n[10] Tests de conflits / erreurs")
check("POST /sites doublon (409)", client.post("/sites", headers=auditeur_headers, json={
    "nom": "Siege Paris", "entreprise_id": ent_id,
}), 409)
check("POST /equipements IP doublon (409)", client.post("/equipements", headers=auditeur_headers, json={
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
