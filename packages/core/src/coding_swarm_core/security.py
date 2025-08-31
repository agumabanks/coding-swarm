"""
Enhanced Security Framework for Sanaa
Provides encryption, access controls, and vulnerability assessment
"""
from __future__ import annotations

import os
import json
import hashlib
import secrets
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta
import jwt
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


@dataclass
class User:
    """User representation with roles and permissions"""
    id: str
    username: str
    email: str
    roles: List[str]
    permissions: List[str]
    created_at: datetime
    last_login: Optional[datetime] = None


@dataclass
class SecurityToken:
    """Security token for authentication"""
    token: str
    user_id: str
    expires_at: datetime
    token_type: str  # 'access' or 'refresh'


@dataclass
class Vulnerability:
    """Security vulnerability representation"""
    id: str
    severity: str
    category: str
    title: str
    description: str
    file_path: str
    line_number: Optional[int]
    cwe_id: Optional[str]
    recommendation: str
    discovered_at: datetime


class EncryptionHandler:
    """Handles encryption/decryption of sensitive data"""

    def __init__(self, key_path: Optional[Path] = None):
        self.key_path = key_path or Path.home() / ".sanaa" / "encryption.key"
        self._ensure_key_exists()
        self.fernet = self._load_key()

    def _ensure_key_exists(self):
        """Ensure encryption key exists"""
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.key_path.exists():
            # Generate a new key
            key = Fernet.generate_key()
            with open(self.key_path, 'wb') as f:
                f.write(key)

    def _load_key(self) -> Fernet:
        """Load encryption key"""
        with open(self.key_path, 'rb') as f:
            key = f.read()
        return Fernet(key)

    def encrypt_data(self, data: str) -> str:
        """Encrypt string data"""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt dictionary data"""
        json_data = json.dumps(data)
        return self.encrypt_data(json_data)

    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt dictionary data"""
        json_data = self.decrypt_data(encrypted_data)
        return json.loads(json_data)


class AccessControlEngine:
    """Role-Based Access Control (RBAC) system"""

    def __init__(self):
        self.roles: Dict[str, List[str]] = {
            'admin': ['*'],  # Full access
            'developer': [
                'project:read', 'project:write', 'project:delete',
                'agent:execute', 'agent:read',
                'api:access', 'debug:access'
            ],
            'viewer': [
                'project:read', 'agent:read', 'api:access'
            ],
            'guest': [
                'project:read'
            ]
        }

        self.users: Dict[str, User] = {}
        self.active_sessions: Dict[str, SecurityToken] = {}

    def add_user(self, user: User):
        """Add a user to the system"""
        self.users[user.id] = user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user credentials"""
        # This would typically check against a database
        # For now, return None (implement proper auth later)
        return None

    def authorize_action(self, user: User, resource: str, action: str) -> bool:
        """Check if user is authorized for an action"""
        required_permission = f"{resource}:{action}"

        # Check if user has the required permission
        for role in user.roles:
            if role in self.roles:
                permissions = self.roles[role]
                if '*' in permissions or required_permission in permissions:
                    return True

        return False

    def create_access_token(self, user: User) -> SecurityToken:
        """Create JWT access token"""
        expires_at = datetime.utcnow() + timedelta(hours=1)

        payload = {
            'user_id': user.id,
            'username': user.username,
            'roles': user.roles,
            'permissions': user.permissions,
            'exp': expires_at.timestamp(),
            'iat': datetime.utcnow().timestamp()
        }

        token = jwt.encode(payload, self._get_jwt_secret(), algorithm='HS256')

        security_token = SecurityToken(
            token=token,
            user_id=user.id,
            expires_at=expires_at,
            token_type='access'
        )

        return security_token

    def validate_token(self, token: str) -> Optional[User]:
        """Validate JWT token and return user"""
        try:
            payload = jwt.decode(token, self._get_jwt_secret(), algorithms=['HS256'])

            user_id = payload['user_id']
            if user_id in self.users:
                return self.users[user_id]

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

        return None

    def _get_jwt_secret(self) -> str:
        """Get JWT secret key"""
        # In production, this should be from environment variables
        return os.getenv('SANAA_JWT_SECRET', 'default-secret-change-in-production')


class VulnerabilityScanner:
    """Automated security vulnerability scanner"""

    def __init__(self):
        self.vulnerability_patterns = self._load_patterns()

    def _load_patterns(self) -> Dict[str, Any]:
        """Load vulnerability detection patterns"""
        return {
            'hardcoded_secrets': {
                'pattern': r'(?i)(password|secret|key|token)\s*[=:]\s*["\'][^"\']+["\']',
                'severity': 'high',
                'category': 'credentials',
                'description': 'Hardcoded credentials detected'
            },
            'sql_injection': {
                'pattern': r'(?i)(select|insert|update|delete).*\$\{.*\}',
                'severity': 'critical',
                'category': 'injection',
                'description': 'Potential SQL injection vulnerability'
            },
            'xss_vulnerable': {
                'pattern': r'innerHTML\s*[=]\s*.*\+.*',
                'severity': 'high',
                'category': 'xss',
                'description': 'Potential XSS vulnerability'
            },
            'weak_crypto': {
                'pattern': r'(?i)(md5|sha1)\s*\(',
                'severity': 'medium',
                'category': 'cryptography',
                'description': 'Weak cryptographic function usage'
            }
        }

    def scan_codebase(self, project_path: str) -> List[Vulnerability]:
        """Scan codebase for vulnerabilities"""
        vulnerabilities = []
        project_path = Path(project_path)

        # Scan all relevant files
        for file_path in project_path.rglob('*'):
            if file_path.is_file() and self._is_relevant_file(file_path):
                try:
                    content = file_path.read_text()
                    file_vulns = self._scan_file(content, str(file_path))
                    vulnerabilities.extend(file_vulns)
                except Exception as e:
                    print(f"Error scanning {file_path}: {e}")

        return vulnerabilities

    def _is_relevant_file(self, file_path: Path) -> bool:
        """Check if file should be scanned"""
        relevant_extensions = ['.py', '.js', '.ts', '.php', '.java', '.cpp', '.c', '.go', '.rs']
        return file_path.suffix in relevant_extensions

    def _scan_file(self, content: str, file_path: str) -> List[Vulnerability]:
        """Scan individual file for vulnerabilities"""
        vulnerabilities = []
        lines = content.split('\n')

        for pattern_name, pattern_config in self.vulnerability_patterns.items():
            import re
            matches = re.finditer(pattern_config['pattern'], content)

            for match in matches:
                line_number = content[:match.start()].count('\n') + 1

                vulnerability = Vulnerability(
                    id=f"{pattern_name}_{file_path}_{line_number}",
                    severity=pattern_config['severity'],
                    category=pattern_config['category'],
                    title=pattern_config['description'],
                    description=f"Found {pattern_name} pattern at line {line_number}",
                    file_path=file_path,
                    line_number=line_number,
                    recommendation=self._get_recommendation(pattern_name),
                    discovered_at=datetime.utcnow()
                )

                vulnerabilities.append(vulnerability)

        return vulnerabilities

    def _get_recommendation(self, pattern_name: str) -> str:
        """Get security recommendation for vulnerability type"""
        recommendations = {
            'hardcoded_secrets': 'Move credentials to environment variables or secure key management system',
            'sql_injection': 'Use parameterized queries or prepared statements',
            'xss_vulnerable': 'Use textContent instead of innerHTML or sanitize input',
            'weak_crypto': 'Use stronger cryptographic functions like SHA-256 or bcrypt'
        }

        return recommendations.get(pattern_name, 'Review and fix security issue')


class SecurityManager:
    """Main security manager coordinating all security components"""

    def __init__(self):
        self.encryption = EncryptionHandler()
        self.access_control = AccessControlEngine()
        self.vulnerability_scanner = VulnerabilityScanner()
        self.audit_log: List[Dict[str, Any]] = []

    async def encrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive data fields"""
        encrypted_data = data.copy()

        sensitive_fields = ['password', 'secret', 'key', 'token', 'api_key']

        for field in sensitive_fields:
            if field in encrypted_data and isinstance(encrypted_data[field], str):
                encrypted_data[field] = self.encryption.encrypt_data(encrypted_data[field])

        return encrypted_data

    async def decrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive data fields"""
        decrypted_data = data.copy()

        sensitive_fields = ['password', 'secret', 'key', 'token', 'api_key']

        for field in sensitive_fields:
            if field in decrypted_data and isinstance(decrypted_data[field], str):
                try:
                    decrypted_data[field] = self.encryption.decrypt_data(decrypted_data[field])
                except:
                    # If decryption fails, keep original value
                    pass

        return decrypted_data

    async def validate_access(self, user_id: str, resource: str, action: str) -> bool:
        """Validate user access to resource"""
        if user_id not in self.access_control.users:
            return False

        user = self.access_control.users[user_id]
        authorized = self.access_control.authorize_action(user, resource, action)

        # Log access attempt
        self._log_access_attempt(user_id, resource, action, authorized)

        return authorized

    async def scan_security_vulnerabilities(self, project_path: str) -> List[Vulnerability]:
        """Scan project for security vulnerabilities"""
        return self.vulnerability_scanner.scan_codebase(project_path)

    def _log_access_attempt(self, user_id: str, resource: str, action: str, authorized: bool):
        """Log access attempts for audit purposes"""
        log_entry = {
            'timestamp': datetime.utcnow(),
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'authorized': authorized,
            'ip_address': 'system'  # Would be actual IP in production
        }

        self.audit_log.append(log_entry)

        # Keep only last 1000 entries
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

    def get_audit_log(self, user_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get audit log entries"""
        log_entries = self.audit_log

        if user_id:
            log_entries = [entry for entry in log_entries if entry['user_id'] == user_id]

        return log_entries[-limit:]


# Global security manager instance
security_manager = SecurityManager()


def get_security_manager() -> SecurityManager:
    """Get global security manager instance"""
    return security_manager