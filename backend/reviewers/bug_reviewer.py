import ast
import re
from typing import List
from . import Finding


class BugReviewer:
    @property
    def category(self) -> str:
        return "bug"

    def analyze(self, code: str, language: str, **kwargs) -> List[Finding]:
        findings = []
        lines = code.split('\n')

        if language != "python":
            return findings

        # Check for bare except
        for i, line in enumerate(lines, 1):
            if re.search(r'except\s*:', line):
                findings.append(Finding(
                    rule_id="BUG001",
                    category="bug",
                    severity="High",
                    line_no=i,
                    title="Bare except clause",
                    description="Except clause catches all exceptions, including system-exiting ones",
                    fix="Specify the exception type: except Exception as e:"
                ))

        # Check for mutable default arguments
        for i, line in enumerate(lines, 1):
            if re.search(r'def\s+\w+\s*\([^)]*=\s*\[', line):
                findings.append(Finding(
                    rule_id="BUG002",
                    category="bug",
                    severity="High",
                    line_no=i,
                    title="Mutable default argument (list)",
                    description="Mutable default arguments are shared across function calls",
                    fix="Use None as default and create list inside function: def f(x=None): x = x or []"
                ))
            if re.search(r'def\s+\w+\s*\([^)]*=\s*\{', line):
                findings.append(Finding(
                    rule_id="BUG003",
                    category="bug",
                    severity="High",
                    line_no=i,
                    title="Mutable default argument (dict)",
                    description="Mutable default arguments are shared across function calls",
                    fix="Use None as default and create dict inside function: def f(x=None): x = x or {}"
                ))

        # Check for == None or != None
        for i, line in enumerate(lines, 1):
            if re.search(r'==\s*None\s*([,)])', line) or re.search(r'!=\s*None\s*([,)])', line):
                findings.append(Finding(
                    rule_id="BUG004",
                    category="bug",
                    severity="Medium",
                    line_no=i,
                    title="Comparison with None using == or !=",
                    description="Use 'is None' or 'is not None' for None comparisons",
                    fix="Replace == None with is None and != None with is not None"
                ))

        # Check for len(x) == 0
        for i, line in enumerate(lines, 1):
            if re.search(r'len\s*\([^)]+\)\s*==\s*0', line):
                findings.append(Finding(
                    rule_id="BUG005",
                    category="bug",
                    severity="Low",
                    line_no=i,
                    title="Unnecessary len() check",
                    description="Use 'if not x:' instead of 'if len(x) == 0:'",
                    fix="Replace len(x) == 0 with not x"
                ))

        # Check for open() without with statement
        for i, line in enumerate(lines, 1):
            if re.search(r'\bopen\s*\(', line) and not re.search(r'with\s+.*open\s*\(', line):
                # Check if the previous line has 'with'
                if i == 1 or not re.search(r'with\s', lines[i-2]):
                    findings.append(Finding(
                        rule_id="BUG006",
                        category="bug",
                        severity="High",
                        line_no=i,
                        title="File opened without context manager",
                        description="File may not be properly closed",
                        fix="Use 'with open(...) as f:' instead of just 'open(...)'"
                    ))

        # AST-based checks
        try:
            tree = ast.parse(code)
            findings.extend(self._check_shadowed_builtins(tree))
        except SyntaxError:
            pass

        return findings

    def _check_shadowed_builtins(self, tree: ast.AST) -> List[Finding]:
        findings = []
        builtins = {'list', 'dict', 'set', 'str', 'int', 'float', 'bool', 'type', 'object',
                   'range', 'len', 'print', 'input', 'open', 'sum', 'max', 'min', 'abs',
                   'all', 'any', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed'}

        class BuiltinShadowChecker(ast.NodeVisitor):
            def __init__(self):
                self.findings = []

            def visit_FunctionDef(self, node):
                for arg in node.args.args:
                    if arg.arg in builtins:
                        self.findings.append(Finding(
                            rule_id="BUG007",
                            category="bug",
                            severity="Medium",
                            line_no=node.lineno,
                            title=f"Shadowed builtin: {arg.arg}",
                            description=f"Variable name '{arg.arg}' shadows a Python builtin",
                            fix=f"Rename variable to avoid shadowing builtin '{arg.arg}'"
                        ))
                self.generic_visit(node)

            def visit_Assign(self, node):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in builtins:
                        self.findings.append(Finding(
                            rule_id="BUG007",
                            category="bug",
                            severity="Medium",
                            line_no=node.lineno,
                            title=f"Shadowed builtin: {target.id}",
                            description=f"Variable name '{target.id}' shadows a Python builtin",
                            fix=f"Rename variable to avoid shadowing builtin '{target.id}'"
                        ))
                self.generic_visit(node)

        checker = BuiltinShadowChecker()
        checker.visit(tree)
        return checker.findings
