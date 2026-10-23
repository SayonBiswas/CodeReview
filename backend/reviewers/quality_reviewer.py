import re
import json
import subprocess
import tempfile
import os
from typing import List
from . import Finding


class QualityReviewer:
    @property
    def category(self) -> str:
        return "quality"

    def analyze(self, code: str, language: str, **kwargs) -> List[Finding]:
        findings = []
        lines = code.split('\n')

        if language != "python":
            return findings

        # Check for long functions (> 50 lines)
        function_stack = []
        function_start = 0
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r'^def\s+\w+\s*\(', stripped):
                function_stack.append(i)
                function_start = i
            elif stripped.startswith('def ') and function_stack:
                function_stack = [i]
                function_start = i
            elif stripped and not stripped.startswith('#') and not stripped.startswith(' ') and not stripped.startswith('\t'):
                if function_stack:
                    func_length = i - function_start
                    if func_length > 50:
                        findings.append(Finding(
                            rule_id="QUAL001",
                            category="quality",
                            severity="Medium",
                            line_no=function_start,
                            title="Function too long",
                            description=f"Function is {func_length} lines long (recommended: < 50)",
                            fix="Break this function into smaller, more focused functions"
                        ))
                    function_stack = []

        # Check for missing docstrings
        for i, line in enumerate(lines, 1):
            if re.match(r'^def\s+\w+\s*\(', line.strip()):
                # Check if next non-empty line is a docstring
                docstring_found = False
                for j in range(i, min(i + 3, len(lines) + 1)):
                    if j < len(lines):
                        next_line = lines[j].strip()
                        if next_line.startswith('"""') or next_line.startswith("'''"):
                            docstring_found = True
                            break
                        if next_line and not next_line.startswith('#'):
                            break
                if not docstring_found:
                    findings.append(Finding(
                        rule_id="QUAL002",
                        category="quality",
                        severity="Low",
                        line_no=i,
                        title="Missing docstring",
                        description="Function lacks a docstring",
                        fix='Add a docstring: """Description of function"""'
                    ))

        # Check for leftover print() statements
        for i, line in enumerate(lines, 1):
            if re.search(r'\bprint\s*\(', line):
                findings.append(Finding(
                    rule_id="QUAL003",
                    category="quality",
                    severity="Low",
                    line_no=i,
                    title="Leftover print() statement",
                    description="Debug print statement found in code",
                    fix="Remove or replace with proper logging"
                ))

        # Check for TODO comments
        for i, line in enumerate(lines, 1):
            if re.search(r'\bTODO\b', line, re.IGNORECASE):
                findings.append(Finding(
                    rule_id="QUAL004",
                    category="quality",
                    severity="Low",
                    line_no=i,
                    title="TODO comment found",
                    description="Unresolved TODO comment in code",
                    fix="Address the TODO or remove the comment"
                ))

        # Run Pylint
        findings.extend(self._run_pylint(code))

        # Run Radon for complexity
        findings.extend(self._run_radon(code))

        return findings

    def _run_pylint(self, code: str) -> List[Finding]:
        findings = []
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ['pylint', '--output-format=json', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                if result.stdout:
                    pylint_output = json.loads(result.stdout)
                    for msg in pylint_output:
                        severity_map = {
                            'error': 'High',
                            'warning': 'Medium',
                            'convention': 'Low',
                            'refactor': 'Low'
                        }
                        findings.append(Finding(
                            rule_id=f"PYLINT_{msg.get('message-id', 'UNKNOWN')}",
                            category="quality",
                            severity=severity_map.get(msg.get('type'), 'Low'),
                            line_no=msg.get('line', 0),
                            title=msg.get('symbol', 'Pylint issue'),
                            description=msg.get('message', ''),
                            fix=msg.get('message', 'Review and fix this quality issue')
                        ))
            finally:
                os.unlink(temp_file)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            pass
        return findings

    def _run_radon(self, code: str) -> List[Finding]:
        findings = []
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_file = f.name

            try:
                # Cyclomatic complexity
                result = subprocess.run(
                    ['radon', 'cc', temp_file, '-a'],
                    capture_output=True,
                    text=True,
                    timeout=20
                )
                for line in result.stdout.split('\n'):
                    if line.strip() and '(' in line:
                        match = re.search(r'(\w+)\s+\(.*\):\s+(\d+)', line)
                        if match:
                            func_name, complexity = match.groups()
                            if int(complexity) > 10:
                                findings.append(Finding(
                                    rule_id="RADON_CC",
                                    category="quality",
                                    severity="High",
                                    line_no=0,
                                    title=f"High cyclomatic complexity in {func_name}",
                                    description=f"Complexity is {complexity} (recommended: < 10)",
                                    fix="Simplify function logic or extract helper functions"
                                ))
            finally:
                os.unlink(temp_file)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return findings
