# FRAMEWORKS KNOWLEDGE BASE

## OVERVIEW
Contains 12+ YAML compliance referentials defining security controls. These are auto-synced to the database on backend startup.

## FRAMEWORK LIST
- `active_directory_audit.yaml`
- `dns_dhcp_audit.yaml`
- `firewall_audit.yaml`
- `linux_server_audit.yaml`
- `m365_audit.yaml`
- `messagerie_audit.yaml`
- `peripheriques_audit.yaml`
- `sauvegarde_audit.yaml`
- `switch_audit.yaml`
- `vpn_audit.yaml`
- `wifi_audit.yaml`
- `windows_server_audit.yaml`

## YAML STRUCTURE
```yaml
metadata:
  name: "Audit Nom"
  version: "1.0"
  description: "Description"
  category: "Reseau"
controls:
  - id: "CTRL-01"
    title: "Titre du contrôle"
    description: "Détails"
    category: "Sécurité"
    severity: "high" # low, medium, high, critical
    verification_method: "Check config X"
    expected_result: "Y is set"
    remediation: "Set Y to Z"
```

## SYNC MECHANISM
1. Backend's `FrameworkService` scans this directory on startup.
2. It computes a SHA-256 hash for each YAML file.
3. If the hash differs from the stored version in the DB, it upserts the framework and its controls.

## CONVENTIONS
- **Language**: Content (titles, descriptions, remediations) is in **French**.
- **IDs**: Use unique, consistent IDs (e.g., AD-01, FW-05).
- **Adding**: Create a new `.yaml` file here and restart the backend.
- **Modifying**: Edit an existing `.yaml` and restart. The hash change triggers the update.
- **Deleting**: Removing a file does NOT delete it from the DB (manual cleanup required).
