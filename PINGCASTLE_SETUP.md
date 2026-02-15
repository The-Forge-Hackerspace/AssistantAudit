# PingCastle Integration - Setup and Testing Guide

## Overview

PingCastle is now fully integrated into AssistantAudit for advanced Active Directory auditing. This document describes the implementation and how to test it.

## What Was Implemented

### 1. Automatic Repository Cloning (Windows)

The `start.ps1` script now automatically:
- Clones the PingCastle repository from GitHub to `tools/pingcastle/`
- Updates the repository on each launch (git pull)
- Configures `PINGCASTLE_PATH` in `.env` automatically
- Creates the tools directory if it doesn't exist

### 2. Backend Components (Already Existed)

- **Runner**: `backend/app/tools/pingcastle_runner/runner.py`
  - Executes PingCastle.exe in healthcheck mode
  - Parses XML reports
  - Generates standardized findings

- **Service**: `backend/app/services/pingcastle_service.py`
  - Orchestrates PingCastle audits
  - Manages background execution
  - Maps findings to AD framework controls
  - Persists results to database

- **Model**: `backend/app/models/pingcastle_result.py`
  - Stores audit results, scores, and risk rules
  - Linked to equipment (domain controllers)

- **API Endpoints**: `backend/app/api/v1/tools.py`
  - POST `/api/v1/tools/pingcastle` - Launch audit
  - GET `/api/v1/tools/pingcastle-results` - List audits
  - GET `/api/v1/tools/pingcastle-results/{id}` - Get audit details
  - DELETE `/api/v1/tools/pingcastle-results/{id}` - Delete audit
  - POST `/api/v1/tools/pingcastle-results/{id}/prefill/{assessment_id}` - Prefill controls

- **WebSocket Terminal**: `backend/app/api/v1/pingcastle_terminal.py`
  - `/api/v1/tools/pingcastle/terminal` WebSocket endpoint
  - Interactive terminal with real-time I/O
  - Authentication via JWT query parameter

### 3. Frontend Components (Already Existed)

- **Page**: `frontend/src/app/outils/pingcastle/page.tsx`
  - Two tabs: Automated audit and Interactive terminal
  - Launch form with DC/domain/credentials
  - Results table with scores and maturity level
  - Detailed view with risk rules and domain info

- **Terminal Component**: `frontend/src/components/pingcastle-terminal.tsx`
  - xterm.js integration
  - WebSocket connection to backend
  - Real-time terminal I/O

- **API Client**: `frontend/src/services/api.ts`
  - `launchPingCastle()` - Start audit
  - `listPingCastleResults()` - Get audits
  - `getPingCastleResult()` - Get details
  - `deletePingCastleResult()` - Delete audit
  - `prefillFromPingCastle()` - Map to controls

## Testing Instructions

### 1. Test Automatic Setup (Windows)

```powershell
# Run the startup script
.\start.ps1

# Verify PingCastle was cloned
dir tools\pingcastle

# Check that .env was updated
cat .env | Select-String "PINGCASTLE_PATH"
```

Expected output:
- `tools/pingcastle/` directory exists with PingCastle repository
- `.env` contains `PINGCASTLE_PATH=<root>\tools\pingcastle\PingCastle.exe`

### 2. Test Backend API

#### a. Check Configuration
```bash
# Verify settings are loaded
curl http://localhost:8000/api/v1/health
```

#### b. Launch Automated Audit
```bash
# POST to launch PingCastle audit
curl -X POST http://localhost:8000/api/v1/tools/pingcastle \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "target_host": "192.168.1.10",
    "domain": "corp.local",
    "username": "CORP\\admin",
    "password": "P@ssw0rd"
  }'
```

Expected response:
```json
{
  "id": 1,
  "status": "running",
  "target_host": "192.168.1.10",
  "domain": "corp.local",
  ...
}
```

#### c. List Audits
```bash
curl http://localhost:8000/api/v1/tools/pingcastle-results \
  -H "Authorization: Bearer <token>"
```

#### d. Get Audit Details
```bash
curl http://localhost:8000/api/v1/tools/pingcastle-results/1 \
  -H "Authorization: Bearer <token>"
```

### 3. Test Frontend

#### a. Access PingCastle Page
1. Navigate to `http://localhost:3000/outils`
2. Click on "PingCastle" card
3. Should see two tabs: "Audit automatisé" and "Terminal interactif"

#### b. Test Automated Audit
1. Go to "Audit automatisé" tab
2. Fill in the form:
   - Contrôleur de domaine: `192.168.1.10` or `dc01.corp.local`
   - Domaine AD: `corp.local`
   - Utilisateur: `CORP\admin` or `admin@corp.local`
   - Mot de passe: `***`
3. Click "Lancer l'audit"
4. Should see audit in "Historique des audits" table with status "running"
5. Wait for completion (5-10 minutes typically)
6. Status should change to "success"
7. Click eye icon to view details

#### c. Test Interactive Terminal
1. Go to "Terminal interactif" tab
2. Should see xterm.js terminal
3. PingCastle menu should appear
4. Test navigation with keyboard
5. Try running a scan option

### 4. Test Integration with Audit Workflow

#### a. Create Assessment
1. Create an audit project
2. Add a domain controller equipment
3. Create an assessment campaign
4. Create an assessment with Active Directory framework

#### b. Run PingCastle and Prefill
1. Launch PingCastle audit for the DC
2. Wait for completion
3. Go to assessment details
4. Use prefill feature to map PingCastle findings to controls

Expected mapping:
- `PC-GLOBAL` → Control `AD-020` (Global score)
- `PC-PRIV` → Control `AD-001` (Privileged accounts)
- `PC-STALE` → Control `AD-002` (Stale objects)
- `PC-TRUST` → Control `AD-010` (Trusts)
- `PC-ANOMALY` → Control `AD-012` (Anomalies)

## Troubleshooting

### PingCastle.exe not found
- Check if `tools/pingcastle/` directory exists
- Verify Git is installed: `git --version`
- Manually clone: `git clone https://github.com/netwrix/pingcastle tools/pingcastle`
- Download release: https://github.com/netwrix/pingcastle/releases
- Set `PINGCASTLE_PATH` in `.env` manually

### Audit fails with "Access Denied"
- Verify credentials are correct
- User must have domain admin rights
- Check firewall allows connection to DC
- Ensure PingCastle.exe runs on Windows

### Terminal not connecting
- Check JWT token is valid (not expired)
- Verify WebSocket endpoint: `ws://localhost:8000/api/v1/tools/pingcastle/terminal?token=<jwt>`
- Check browser console for errors
- Ensure user has "admin" or "auditeur" role

### Prefill not working
- Verify PingCastle audit completed successfully
- Check that assessment uses Active Directory framework
- Ensure control ref_ids match: AD-001, AD-002, AD-010, AD-012, AD-020
- Check logs for mapping errors

## Architecture Notes

### Two Execution Modes

1. **Automated (Non-Interactive)**
   - Command: `PingCastle.exe --healthcheck --server DC --level Full`
   - Runs in background thread
   - Parses XML report
   - Generates findings
   - Stores in database

2. **Interactive (Terminal)**
   - Command: `PingCastle.exe` (no args)
   - Opens main menu
   - Real-time I/O via WebSocket
   - No parsing or storage

### Data Flow

```
User → Frontend → API → Service → Runner → PingCastle.exe
                                      ↓
                                   XML Report
                                      ↓
                                    Parser
                                      ↓
                                   Findings
                                      ↓
                                   Database
                                      ↓
                                  Assessment
                                  (prefill)
```

### Security Considerations

- Passwords are NOT stored in database (only used during execution)
- JWT authentication required for all endpoints
- Only admin/auditeur roles can launch audits
- WebSocket requires valid JWT token
- PingCastle runs with user-provided credentials (least privilege)

## Future Enhancements

Potential improvements for future iterations:

1. **Scheduled Audits**: Cron-like scheduling for automatic AD audits
2. **Email Notifications**: Alert on audit completion or critical findings
3. **Trend Analysis**: Track score evolution over time
4. **Custom Rules**: Define organization-specific security rules
5. **Multi-Domain**: Support auditing multiple AD domains/forests
6. **Report Export**: PDF/HTML report generation from findings
7. **BloodHound Integration**: Combine with BloodHound for path analysis
8. **Remediation Tracking**: Link findings to remediation tasks

## References

- PingCastle GitHub: https://github.com/netwrix/pingcastle
- PingCastle Documentation: https://www.pingcastle.com/documentation/
- Active Directory Security: https://docs.microsoft.com/en-us/windows-server/identity/ad-ds/
