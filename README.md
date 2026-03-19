# AssistantAudit

**Open-source IT infrastructure security auditing platform for penetration testers, security auditors, and IT compliance teams.**

AssistantAudit provides automated assessment of network devices, servers, cloud platforms (Microsoft 365), and compliance frameworks. Built with Python FastAPI backend, Next.js React frontend, and 12 customizable YAML frameworks (200+ controls). Includes integrated tools: Nmap scanner, SSL/TLS checker, SSH/WinRM collectors, Active Directory auditor, PingCastle, Monkey365 bridge, and configuration parsers.

---

## Features

✅ **Phase 1-3 Complete**

- **Multi-tenant management** — organize audits by company, site, and equipment
- **12 compliance frameworks** (200+ controls) — Firewall, Switch, Windows/Linux servers, Active Directory, Microsoft 365, DNS/DHCP, Wi-Fi, VPN, Sauvegarde, Messagerie, Périphériques, OPNsense
- **Automated compliance scoring** — real-time conformity status (compliant/non-compliant/partial/N/A)
- **45 REST API endpoints** — fully documented with Swagger UI
- **JWT authentication** — role-based access control (admin, auditor, reader)
- **Dynamic YAML frameworks** — SHA-256 integrity checking with automatic sync at startup
- **Nmap network scanner** — host discovery, port enumeration, OS fingerprinting
- **SSL/TLS certificate analyzer** — protocol detection, expiration warnings, security findings
- **SSH/WinRM remote collection** — automated system data gathering (Linux, Windows, FortiGate, OPNsense, Stormshield)
- **Active Directory auditor** — LDAP queries for domain security assessment
- **PingCastle integration** — AD health check with risk scoring
- **Monkey365 bridge** — Microsoft 365 / Azure AD automated audit
- **Configuration parser** — Fortinet FortiGate and OPNsense firewall rule analysis
- **Evidence attachments** — file upload/download for control result proof
- **Full React UI** (17 pages) — dashboard, entity CRUD, evaluation forms, dark mode, responsive design

🔄 **Phase 4: Tool Integrations (Testing)**
- All 7 tools implemented and integrated
- Ready for production testing

⏳ **Phase 5-6: Future**
- PDF/Word report generation (planned)
- AI-assisted remediation suggestions (planned)

---

## Tech Stack

### Backend
- **Python 3.13**
- **FastAPI** — high-performance async web framework
- **SQLAlchemy 2.0** — ORM with async support
- **Pydantic v2** — data validation and serialization
- **JWT OAuth2** — secure authentication with python-jose + bcrypt
- **Alembic** — database migrations

### Frontend
- **Next.js 16** (App Router)
- **React 19** + TypeScript
- **Tailwind CSS v4** — utility-first styling
- **shadcn/ui** — accessible component library
- **Recharts** — data visualization
- **Axios** — HTTP client with JWT interceptor
- **next-themes** — dark mode support

### Database
- **SQLite** (development)
- **PostgreSQL** (production, planned)

### Tools & Services
- **Nmap** — network discovery
- **OpenSSL** — TLS/certificate analysis
- **Monkey365** — M365/Azure AD auditor
- **PingCastle** — AD security assessment
- **Paramiko** — SSH remote execution
- **pywinrm** — WinRM remote PowerShell
- **ldap3** — LDAP queries for AD audit

---

## Prerequisites

- **Python 3.13+**
- **Node.js 18+**
- **PowerShell 7+** (for Monkey365 integration on Windows)
- **Git** (for tool auto-updates)

### Optional Tools
- **Nmap** — for network scanning (available on PATH)
- **OpenSSL** — for TLS testing (usually pre-installed)

---

## Installation

### Quick Start (Windows PowerShell)

```powershell
# Clone repository
git clone https://github.com/The-Forge-Hackerspace/AssistantAudit
cd AssistantAudit

# Run the startup script
.\start.ps1

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# Swagger UI: http://localhost:8000/docs
```

**First Login**
- Default admin credentials will be displayed after `start.ps1` completes
- Change password immediately in profile settings

### Advanced Options

```powershell
# Development mode (verbose logs, hot-reload)
.\start.ps1 --dev

# Production build mode
.\start.ps1 --build
```

### Manual Installation

**Backend:**
```bash
cd backend
python -m venv ../venv
# Windows: ..\venv\Scripts\Activate.ps1
# Linux/macOS: source ../venv/bin/activate
pip install -r requirements.txt

# Initialize database
python init_db.py

# Start server
cd ..
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend (in another terminal):**
```bash
cd frontend
npm install
npm run dev

# Open http://localhost:3000
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Security (REQUIRED for production)
SECRET_KEY=your-secret-key-min-32-chars

# Database
DATABASE_URL=sqlite:///./instance/assistantaudit.db
# DATABASE_URL=postgresql://user:password@localhost:5432/assistantaudit

# Application
ENV=development          # development | production
DEBUG=true
LOG_LEVEL=INFO

# Tools
NMAP_TIMEOUT=600         # Timeout in seconds
PINGCASTLE_TIMEOUT=300
MONKEY365_TIMEOUT=600

# Admin (optional - auto-generated if not set)
ADMIN_PASSWORD=your-secure-password
```

---

## Project Status

- ✅ **Phase 1:** Backend foundation (45 endpoints, 24 models, JWT auth)
- ✅ **Phase 2:** 12 YAML security frameworks with SHA-256 sync
- ✅ **Phase 3:** Full React UI (17 pages, dark mode, responsive)
- 🔄 **Phase 4:** Tool integrations (7/7 implemented, testing in progress)
- ⏳ **Phase 5:** PDF/Word report generation (planned)
- ⏳ **Phase 6:** AI-assisted remediation suggestions (planned)

**Sprint 0 Audit Status:** All critical security findings documented. Known issues and technical debt listed in [CONCEPT.md#known-issues](CONCEPT.md#-known-issues--technical-debt).

---

## API Documentation

### Interactive API Explorer
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Full API Reference
See [API.md](API.md) for complete endpoint documentation (45 endpoints across 14 services).

---

## Architecture

The application follows a layered architecture:

```
┌─────────────────────────────────────┐
│     Frontend (Next.js React)        │
│  17 pages, JWT auth, dark mode      │
└──────────────┬──────────────────────┘
               │ Axios + JWT Interceptor
┌──────────────┴──────────────────────┐
│     REST API (FastAPI)              │
│  45 endpoints, role-based auth      │
└──────────────┬──────────────────────┘
               │ SQLAlchemy ORM
┌──────────────┴──────────────────────┐
│  Core Engine                        │
│  ├─ Framework sync + versioning     │
│  ├─ Compliance scoring              │
│  ├─ Tool integration bridge         │
│  └─ 7 integrated audit tools        │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│  Database Layer                     │
│  SQLite (dev) → PostgreSQL (prod)   │
└─────────────────────────────────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design decisions.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Use TypeScript for frontend
- Write tests for new features
- Update documentation
- Run tests before submitting PR

---

## Security

AssistantAudit implements comprehensive security controls:

✅ **Authentication & Authorization**
- JWT tokens with 15-minute access + 7-day refresh
- Role-based access control (admin, auditor, reader)
- Password hashing with bcrypt

✅ **Data Protection**
- SQL injection prevention (SQLAlchemy ORM)
- Command injection mitigation (whitelisting, no shell=True)
- Path traversal protection (Path.resolve + is_relative_to checks)
- CSRF protection (SameSite cookies)
- XSS prevention (httpOnly tokens)

✅ **Infrastructure**
- Security headers (CSP, HSTS, X-Frame-Options, etc.)
- Rate limiting on authentication endpoints
- Comprehensive audit logging
- Dependency security scanning

**For security concerns**, please see [SECURITY.md](SECURITY.md) or contact maintainers privately.

---

## Known Issues

**Sprint 0 Audit (2026-03-20)** identified the following:

### Critical (Must Fix Before Production)
- Dashboard chart colors hardcoded (don't adapt to dark mode)
- 4 icon buttons missing accessibility labels
- 7 npm high-severity vulnerabilities

### High Priority
- 5 N+1 query patterns need optimization
- Database and infrastructure environment variable issues
- Several tools lack unit test coverage

### Medium Priority
- SSH private keys passed plaintext in API requests
- CORS origins should be environment-based
- WinRM SSL validation disabled in development

**Full details:** See [CONCEPT.md#-known-issues--technical-debt](CONCEPT.md#-known-issues--technical-debt)

---

## License

Proprietary — All rights reserved. For licensing inquiries, contact the maintainers.

---

## Support

### Documentation
- [API.md](API.md) — Complete API reference
- [ARCHITECTURE.md](ARCHITECTURE.md) — Technical architecture
- [CONCEPT.md](CONCEPT.md) — Vision, roadmap, and known issues
- [SECURITY.md](SECURITY.md) — Security audit findings

### Community
- **GitHub Issues** — Bug reports and feature requests
- **Discussions** — Questions and ideas

### Getting Help
For setup issues or questions:
1. Check documentation above
2. Search existing GitHub issues
3. Open a new issue with reproduction steps

---

## Roadmap

**Near-term (Next 2 Sprints)**
- Fix critical security findings from Sprint 0 audit
- Add unit test coverage for tools
- Implement CI/CD security scanning pipeline

**Mid-term (Q2 2026)**
- PostgreSQL production migration
- PDF/Word report generation
- Advanced role-based permissions

**Long-term (H2 2026)**
- AI-assisted remediation suggestions
- Custom framework marketplace
- SIEM integration
- Multi-language support

---

## Contact

**Project Owner:** T0SAGA97  
**GitHub:** https://github.com/The-Forge-Hackerspace/AssistantAudit

---

**Last Updated:** March 2026 (Sprint 0 Audit)
