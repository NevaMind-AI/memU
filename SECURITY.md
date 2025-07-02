# Security Policy

## Supported Versions

We provide security updates for the following versions of PersonaLab:

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of PersonaLab seriously. If you discover a security vulnerability, please follow these steps:

### How to Report

1. **Do not create a public issue** for security vulnerabilities
2. Send an email to [security@personalab.ai] with the following information:
   - Description of the vulnerability
   - Steps to reproduce the issue
   - Potential impact assessment
   - Any suggested fixes (if available)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt of your report within 48 hours
- **Initial Assessment**: We will provide an initial assessment within 5 business days
- **Updates**: We will keep you informed of our progress throughout the investigation
- **Resolution**: We aim to resolve critical vulnerabilities within 90 days

### Security Best Practices

When using PersonaLab, please follow these security guidelines:

#### API Key Management
- Never commit API keys to version control
- Use environment variables for sensitive configuration
- Rotate API keys regularly
- Use the principle of least privilege for API permissions

#### Database Security
- Use strong passwords for database connections
- Enable SSL/TLS for database connections in production
- Regularly backup your data
- Keep your database software updated

#### Production Deployment
- Use PostgreSQL instead of SQLite for production environments
- Enable proper authentication and authorization
- Use HTTPS for all network communications
- Implement proper logging and monitoring
- Regularly update dependencies

#### Data Privacy
- Be mindful of sensitive data in conversation logs
- Implement data retention policies
- Consider data encryption at rest
- Follow relevant privacy regulations (GDPR, CCPA, etc.)

### Vulnerability Disclosure Policy

- We will coordinate disclosure timing with you
- We prefer coordinated disclosure after a fix is available
- We will credit you for the discovery (unless you prefer anonymity)
- We may provide a security advisory for significant vulnerabilities

### Security Updates

Security updates will be released as:
- Patch releases for critical vulnerabilities
- Minor releases for moderate vulnerabilities
- Major releases for architectural security improvements

### Contact

For security-related questions or concerns:
- Email: security@personalab.ai
- For general issues: Create an issue on GitHub (non-security only)

Thank you for helping keep PersonaLab secure! 