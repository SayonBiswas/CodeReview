import re
import json
import subprocess
import tempfile
import os
from typing import List
from . import Finding


class SecurityReviewer:
    @property
    def category(self) -> str:
        return "security"

    def analyze(self, code: str, language: str, **kwargs) -> List[Finding]:
        findings = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            # Hardcoded secrets
            if re.search(r'(sk-|pk-|Bearer\s+[a-zA-Z0-9]{20,}|password\s*=\s*["\'][^"\']{8,}["\'])', line):
                findings.append(Finding(
                    rule_id="SEC001",
                    category="security",
                    severity="Critical",
                    line_no=i,
                    title="Hardcoded secret detected",
                    description="Potential API key, password, or secret found in code",
                    fix="Move secrets to environment variables or a configuration file"
                ))

            # SQL injection patterns
            if re.search(r'(execute\([\'"].*%[\'"]|query\([\'"].*\+.*[\'"])', line):
                findings.append(Finding(
                    rule_id="SEC002",
                    category="security",
                    severity="High",
                    line_no=i,
                    title="Potential SQL injection",
                    description="String concatenation in SQL query detected",
                    fix="Use parameterized queries instead of string concatenation"
                ))

            # eval/exec
            if re.search(r'\b(eval|exec)\s*\(', line):
                findings.append(Finding(
                    rule_id="SEC003",
                    category="security",
                    severity="Critical",
                    line_no=i,
                    title="Use of eval() or exec()",
                    description="Dynamic code execution is dangerous",
                    fix="Avoid eval/exec; use safer alternatives like ast.literal_eval"
                ))

            # Hardcoded IPs and localhost URLs
            if re.search(r'(https?://(?:127\.|0\.0\.0\.0|localhost|192\.168\.|10\.))', line):
                findings.append(Finding(
                    rule_id="SEC004",
                    category="security",
                    severity="Medium",
                    line_no=i,
                    title="Hardcoded private IP or localhost URL",
                    description="Private IP addresses or localhost URLs should not be hardcoded",
                    fix="Use environment variables for URLs"
                ))

            # Non-HTTPS calls
            if re.search(r'http://(?!localhost)', line) and not re.search(r'https://', line):
                findings.append(Finding(
                    rule_id="SEC005",
                    category="security",
                    severity="Medium",
                    line_no=i,
                    title="Non-HTTPS URL detected",
                    description="Unencrypted HTTP connection detected",
                    fix="Use HTTPS for secure communication"
                ))

        # Run Bandit for Python code
        if language == "python":
            findings.extend(self._run_bandit(code))

        return findings

    def _run_bandit(self, code: str) -> List[Finding]:
        findings = []
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['bandit', '-f', 'json', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                if result.stdout:
                    bandit_output = json.loads(result.stdout)
                    for issue in bandit_output.get('results', []):
                        severity_map = {
                            'HIGH': 'High',
                            'MEDIUM': 'Medium',
                            'LOW': 'Low'
                        }
                        findings.append(Finding(
                            rule_id=f"BANDIT_{issue.get('test_id', 'UNKNOWN')}",
                            category="security",
                            severity=severity_map.get(issue.get('issue_severity'), 'Low'),
                            line_no=issue.get('line_number', 0),
                            title=issue.get('test_name', 'Unknown issue'),
                            description=issue.get('issue_text', ''),
                            fix=issue.get('issue_text', 'Review and fix this security issue')
                        ))
            finally:
                os.unlink(temp_file)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass
        return findings
