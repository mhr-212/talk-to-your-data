Security Policy

Reporting a Vulnerability

If you discover a security vulnerability in this project, please email security@[your-domain] instead of using the public issue tracker.

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge your report within 48 hours and work with you to resolve it responsibly.

Security Features

Input Validation
- User input treated as untrusted text (never interpolated into SQL)
- Multi-point validation before SQL generation
- Type and length checking on all endpoints

SQL Injection Prevention
- 13-point validator blocks dangerous keywords and patterns
- Forbidden: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, GRANT, REVOKE, COPY, VACUUM, ANALYZE, LOCK
- Forbidden patterns: semicolons, comments (-- and /**/), UNION, INTERSECT, EXCEPT, CTEs, INTO, FOR UPDATE, information_schema, pg_*
- Table allowlist per user role
- Read-only database session enforcement (PostgreSQL)
- Statement timeout: 5 seconds

Authentication & Authorization
- JWT tokens with expiration (default 24 hours)
- Role-based access control (RBAC): analyst, finance, admin
- Table-level permissions per role
- HTTP 403 for unauthorized access

Rate Limiting
- Global: 200 requests/hour per IP
- Query endpoint: 20 requests/minute per IP
- HTTP 429 when limits exceeded

Error Handling
- Generic error messages (no stack traces to users)
- Actionable validation errors (e.g., "Available tables: X")
- Logging for audit trail (no PII in logs)

Data Protection
- Connections over HTTPS/TLS (recommended for production)
- Passwords in database URLs masked in logs
- No sensitive data in error messages
- Query results inherit database row-level security

Performance & Abuse Prevention
- Query timeout enforces maximum resource usage
- LIMIT auto-injection prevents runaway queries
- Result caching reduces duplicate processing
- Audit logging enables incident investigation

Best Practices for Deployment

Development
- Use DEV_FALLBACK_MODE=false only with valid API keys
- Never commit .env with real credentials
- Use strong, unique database passwords
- Enable PostgreSQL statement logging for audit

Production
- Use environment variables or secret manager (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)
- Deploy behind reverse proxy (nginx, Apache) with HTTPS/TLS
- Enable HTTPS with valid certificate
- Use database read-only user with minimal grants
- Implement VPN/firewall access to API
- Set up monitoring and alerting
- Rotate API keys regularly
- Enforce strong authentication (MFA if possible)
- Use RBAC to limit data exposure

Database Hardening
- Create read-only application user:
  CREATE USER app_user WITH PASSWORD 'strong_password';
  GRANT CONNECT ON DATABASE talk_to_data TO app_user;
  GRANT USAGE ON SCHEMA public TO app_user;
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_user;

- Disable dangerous functions in application context
- Use row-level security (RLS) for multi-tenant scenarios
- Audit query logs regularly

Testing
- Validate SQL injection prevention (test suite included)
- Test with invalid roles and table access
- Fuzz with large inputs and special characters
- Load test with concurrent requests
- Verify error messages don't leak info

Dependencies
- Keep Python, Flask, and libraries updated
- Monitor for CVEs in dependencies: pip list --outdated
- Use pip-audit for vulnerability scanning: pip-audit
- Review CHANGELOG for breaking updates

Secrets Management

Do NOT commit to version control:
- .env files with API keys or database passwords
- Private SSH keys
- Database backups
- OAuth tokens
- AWS/Azure credentials

Use instead:
- .env.example with placeholders
- Environment variables in CI/CD
- Secret manager services
- Docker secrets for container deployments

Known Limitations
- LLM can hallucinate table/column names; validator prevents execution
- RBAC is role-based, not user-based fine-grained ACLs
- In-memory storage (logs, cache, analytics) is lost on restart
- No end-to-end encryption for data in transit within app
- No audit trail of failed login attempts

Roadmap for Hardening
- Role-based field-level access control
- Persistent audit logging to database
- IP allowlist per user/role
- SAML/LDAP integration for enterprise auth
- Data masking for sensitive columns
- Encryption at rest for cached results
- Rate limiting by user_id (not just IP)

Security Scanning

Recommended tools:
- bandit (Python security linter): bandit -r .
- pip-audit (dependency vulnerabilities): pip-audit
- OWASP ZAP (web app testing)
- Snyk (continuous vulnerability monitoring)

Compliance Notes
- GDPR: Ensure data privacy; implement right-to-erasure for logs
- HIPAA: Requires data encryption, audit trails, business associates
- SOC 2: Implement monitoring, incident response, access controls
- PCI DSS: Required if processing payment data

Contact
For security questions or responsible disclosure, contact security@[your-domain].

Last Updated: 2026-01-19
