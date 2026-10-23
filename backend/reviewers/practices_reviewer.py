import re
from typing import List
from . import Finding


class PracticesReviewer:
    @property
    def category(self) -> str:
        return "practices"

    def analyze(self, code: str, language: str, **kwargs) -> List[Finding]:
        findings = []
        lines = code.split('\n')

        if language != "python":
            return findings

        # Check for wildcard imports
        for i, line in enumerate(lines, 1):
            if re.search(r'from\s+\S+\s+import\s+\*', line):
                findings.append(Finding(
                    rule_id="PRAC001",
                    category="practices",
                    severity="Medium",
                    line_no=i,
                    title="Wildcard import",
                    description="Wildcard imports pollute namespace and make code unclear",
                    fix="Import specific names: from module import name1, name2"
                ))

        # Check for global variables (simple heuristic)
        global_vars = set()
        for i, line in enumerate(lines, 1):
            if re.match(r'^[A-Z_][A-Z0-9_]*\s*=', line.strip()) and not line.strip().startswith('#'):
                var_name = re.match(r'^([A-Z_][A-Z0-9_]*)', line.strip())
                if var_name and var_name.group(1) not in {'True', 'False', 'None'}:
                    global_vars.add((i, var_name.group(1)))

        for line_no, var_name in global_vars:
            findings.append(Finding(
                rule_id="PRAC002",
                category="practices",
                severity="Low",
                line_no=line_no,
                title=f"Global variable: {var_name}",
                description="Global variables can make code hard to maintain and test",
                fix="Consider using class attributes or function parameters instead"
            ))

        # Check for magic numbers
        for i, line in enumerate(lines, 1):
            # Look for standalone numbers (not in comments, not 0, 1, -1)
            if re.search(r'(?<![\w.])\b(?!0|1|-1)[2-9]\d*\b(?![\w.])', line) and not line.strip().startswith('#'):
                # Exclude numbers in context of version strings, dates, etc.
                if not re.search(r'(version|date|time|port|timeout)', line, re.IGNORECASE):
                    findings.append(Finding(
                        rule_id="PRAC003",
                        category="practices",
                        severity="Low",
                        line_no=i,
                        title="Magic number",
                        description="Unnamed numeric literal without clear meaning",
                        fix="Define a constant with a descriptive name"
                    ))

        # Check for missing if __name__ == "__main__" guard
        has_main_guard = False
        for i, line in enumerate(lines, 1):
            if re.search(r"if\s+__name__\s*==\s*['\"]__main__['\"]", line):
                has_main_guard = True
                break

        # Check if there's top-level executable code
        has_top_level_code = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('import') and not stripped.startswith('from') and not stripped.startswith('def') and not stripped.startswith('class'):
                if re.match(r'^[a-zA-Z_]', stripped):
                    has_top_level_code = True
                    break

        if has_top_level_code and not has_main_guard:
            findings.append(Finding(
                rule_id="PRAC004",
                category="practices",
                severity="Low",
                line_no=0,
                title="Missing if __name__ == '__main__' guard",
                description="Top-level executable code should be guarded",
                fix="Wrap top-level code in: if __name__ == '__main__':"
            ))

        return findings
