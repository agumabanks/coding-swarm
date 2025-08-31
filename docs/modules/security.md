# Security Module Documentation

## Overview

The Security Module (`packages/core/src/coding_swarm_core/security.py`) provides comprehensive security features for the Sanaa system, including encryption, access control, and vulnerability assessment.

## Features

### 1. Encryption Handler
- **End-to-end encryption** for sensitive data
- **AES encryption** using Fernet (cryptography library)
- **Dictionary encryption** for complex data structures
- **Secure key management** with automatic key generation

### 2. Access Control Engine
- **Role-Based Access Control (RBAC)** system
- **JWT token authentication** with configurable expiration
- **User management** with roles and permissions
- **Audit logging** for security events

### 3. Vulnerability Scanner
- **Automated security scanning** for codebases
- **Pattern-based detection** for common vulnerabilities
- **CWE mapping** for standardized vulnerability classification
- **Confidence scoring** for vulnerability assessment

## API Reference

### EncryptionHandler

```python
from coding_swarm_core.security import EncryptionHandler

# Initialize encryption handler
encryptor = EncryptionHandler()

# Encrypt data
encrypted = encryptor.encrypt_data("sensitive data")
decrypted = encryptor.decrypt_data(encrypted)

# Encrypt dictionaries
data = {"password": "secret", "api_key": "key123"}
encrypted_dict = encryptor.encrypt_dict(data)
decrypted_dict = encryptor.decrypt_dict(encrypted_dict)
```

### AccessControlEngine

```python
from coding_swarm_core.security import AccessControlEngine

# Initialize access control
ac = AccessControlEngine()

# Add user
user = User(id="user1", username="john", email="john@example.com", roles=["developer"])
ac.add_user(user)

# Authenticate user
user = ac.authenticate_user("john", "password")

# Check permissions
has_access = ac.authorize_action(user, "project", "read")

# Create access token
token = ac.create_access_token(user)

# Validate token
validated_user = ac.validate_token(token.token)
```

### VulnerabilityScanner

```python
from coding_swarm_core.security import VulnerabilityScanner

# Initialize scanner
scanner = VulnerabilityScanner()

# Scan codebase
vulnerabilities = scanner.scan_codebase("/path/to/project")

# Process results
for vuln in vulnerabilities:
    print(f"Severity: {vuln.severity}")
    print(f"Title: {vuln.title}")
    print(f"Description: {vuln.description}")
    print(f"Recommendation: {vuln.recommendation}")
```

## Configuration

### Environment Variables

- `SANAA_JWT_SECRET`: JWT signing secret (auto-generated if not set)
- `SANAA_ENCRYPTION_KEY_PATH`: Path to encryption key file

### Security Roles

- **admin**: Full system access
- **developer**: Project and agent management
- **viewer**: Read-only access
- **guest**: Limited access

## Dependencies

- `cryptography>=41.0.0`: For encryption operations
- `PyJWT>=2.0.0`: For JWT token handling
- `bcrypt>=4.0.0`: For password hashing

## Security Best Practices

### Data Protection
- Always encrypt sensitive data before storage
- Use strong encryption keys and rotate regularly
- Implement proper key management procedures

### Access Control
- Follow principle of least privilege
- Regularly review user permissions
- Implement multi-factor authentication for admin accounts

### Vulnerability Management
- Run regular security scans
- Address high-severity vulnerabilities immediately
- Keep dependencies updated

## Integration Points

### With Other Modules
- **Performance Monitor**: Security metrics and alerts
- **User Interfaces**: Authentication integration
- **Advanced Debugging**: Security vulnerability detection

### External Systems
- **Identity Providers**: OAuth2 integration support
- **Security Information and Event Management (SIEM)**: Audit log export
- **Vulnerability Databases**: CWE and OWASP integration

## Error Handling

The security module provides comprehensive error handling:

- **EncryptionError**: Encryption/decryption failures
- **AuthenticationError**: Authentication failures
- **AuthorizationError**: Permission denied errors
- **SecurityScanError**: Vulnerability scanning errors

## Monitoring and Logging

### Audit Logs
- All security events are logged with timestamps
- User actions are tracked for compliance
- Failed authentication attempts are recorded

### Metrics
- Authentication success/failure rates
- Vulnerability scan results
- Access control violations

## Performance Considerations

- Encryption operations are optimized for performance
- JWT validation uses efficient algorithms
- Vulnerability scanning can be run asynchronously
- Memory usage is minimized for large codebases

## Troubleshooting

### Common Issues

1. **Encryption key not found**
   - Solution: Check key file path or regenerate keys

2. **JWT token expired**
   - Solution: Implement token refresh mechanism

3. **Vulnerability scan timeout**
   - Solution: Limit scan scope or increase timeout

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger('sanaa.security').setLevel(logging.DEBUG)
```

## Future Enhancements

- **Multi-factor authentication (MFA)**
- **OAuth2 provider integration**
- **Advanced threat detection**
- **Compliance reporting (GDPR, HIPAA)**
- **Zero-trust architecture support**

## Examples

### Complete Security Setup

```python
from coding_swarm_core.security import SecurityManager

# Initialize security manager
security = SecurityManager()

# Encrypt sensitive data
user_data = {"email": "user@example.com", "api_key": "secret123"}
encrypted = security.encrypt_sensitive_data(user_data)

# Validate access
user_id = "user123"
has_access = security.validate_access(user_id, "project", "read")

# Scan for vulnerabilities
vulnerabilities = security.scan_security_vulnerabilities("/path/to/project")
```

This module provides enterprise-grade security features while maintaining ease of use and integration with the broader Sanaa ecosystem.