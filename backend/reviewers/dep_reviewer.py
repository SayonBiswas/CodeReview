import subprocess
import tempfile
import os
import re
from typing import List
from . import Finding


class DepReviewer:
    @property
    def category(self) -> str:
        return "dependency"

    def analyze(self, code: str, language: str, **kwargs) -> List[Finding]:
        findings = []
        requirements = kwargs.get('requirements', '')

        if not requirements or language != "python":
            return findings

        # Run Safety
        findings.extend(self._run_safety(requirements))

        # Run pip-audit
        findings.extend(self._run_pip_audit(requirements))

        # Check for unpinned versions
        findings.extend(self._check_unpinned_versions(requirements))

        return findings

    def _run_safety(self, requirements: str) -> List[Finding]:
        findings = []
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(requirements)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['safety', 'check', '--file', temp_file, '--json'],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                if result.stdout:
                    try:
                        safety_output = eval(result.stdout)
                        if isinstance(safety_output, list):
                            for vuln in safety_output:
                                findings.append(Finding(
                                    rule_id="DEP_SAFETY",
                                    category="dependency",
                                    severity="High",
                                    line_no=0,
                                    title=f"Vulnerability in {vuln.get('package', 'unknown')}",
                                    description=f"CVE: {vuln.get('id', 'unknown')} - {vuln.get('advisory', 'Security vulnerability detected')}",
                                    fix=f"Upgrade to safe version: {vuln.get('advisory', 'Check details')}"
                                ))
                    except (SyntaxError, TypeError):
                        pass
            finally:
                os.unlink(temp_file)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return findings

    def _run_pip_audit(self, requirements: str) -> List[Finding]:
        findings = []
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(requirements)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['pip-audit', '--format', 'json', '--requirement', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                if result.stdout:
                    try:
                        import json
                        audit_output = json.loads(result.stdout)
                        for vuln in audit_output.get('dependencies', []):
                            for vuln_detail in vuln.get('vulnerabilities', []):
                                findings.append(Finding(
                                    rule_id="DEP_AUDIT",
                                    category="dependency",
                                    severity="High",
                                    line_no=0,
                                    title=f"Vulnerability in {vuln.get('name', 'unknown')}",
                                    description=f"{vuln_detail.get('id', 'unknown')} - {vuln_detail.get('description', 'Security vulnerability')}",
                                    fix=f"Upgrade to: {vuln_detail.get('fix', [])}"
                                ))
                    except (json.JSONDecodeError, KeyError):
                        pass
            finally:
                os.unlink(temp_file)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return findings

    def _check_unpinned_versions(self, requirements: str) -> List[Finding]:
        findings = []
        lines = requirements.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('#'):
                # Check for unpinned versions (no ==, >=, <=, ~=, etc.)
                if re.match(r'^[a-zA-Z0-9_-]+$', line):
                    findings.append(Finding(
                        rule_id="DEP_UNPINNED",
                        category="dependency",
                        severity="Low",
                        line_no=i,
                        title=f"Unpinned version: {line}",
                        description="Dependency version is not pinned, which can lead to unexpected changes",
                        fix=f"Pin version: {line}==<version>"
                    ))
        return findings
