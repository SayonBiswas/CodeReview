from typing import List, Dict
from .reviewers import Finding


class Aggregator:
    SEVERITY_WEIGHTS = {
        'Critical': 10,
        'High': 7,
        'Medium': 4,
        'Low': 1
    }

    SEVERITY_ORDER = ['Critical', 'High', 'Medium', 'Low']

    @staticmethod
    def merge_findings(all_findings: List[List[Finding]]) -> List[Finding]:
        merged = []
        seen = set()

        for findings_list in all_findings:
            for finding in findings_list:
                key = (finding.category, finding.line_no, finding.title)
                if key not in seen:
                    seen.add(key)
                    merged.append(finding)

        return merged

    @staticmethod
    def sort_findings(findings: List[Finding]) -> List[Finding]:
        def sort_key(finding: Finding):
            severity_order = {'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3}
            return (severity_order.get(finding.severity, 4), finding.line_no or 0)

        return sorted(findings, key=sort_key)

    @staticmethod
    def calculate_score(findings: List[Finding]) -> int:
        total_deduction = 0
        for finding in findings:
            weight = Aggregator.SEVERITY_WEIGHTS.get(finding.severity, 0)
            total_deduction += weight

        score = max(0, 100 - total_deduction)
        return score

    @staticmethod
    def calculate_grade(score: int) -> str:
        if score >= 90:
            return 'A'
        elif score >= 70:
            return 'B'
        elif score >= 50:
            return 'C'
        else:
            return 'F'

    @staticmethod
    def get_summary_counts(findings: List[Finding]) -> Dict[str, int]:
        counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
        for finding in findings:
            if finding.severity in counts:
                counts[finding.severity] += 1
        return counts

    @staticmethod
    def select_for_ai(findings: List[Finding], max_count: int = 10) -> List[Finding]:
        sorted_findings = Aggregator.sort_findings(findings)
        selected = []
        for finding in sorted_findings:
            if finding.severity in ['Critical', 'High']:
                selected.append(finding)
                if len(selected) >= max_count:
                    break
        return selected

    @staticmethod
    def compare_sessions(old_findings: List[Finding], new_findings: List[Finding]) -> Dict[str, List[str]]:
        old_set = {(f.category, f.title) for f in old_findings}
        new_set = {(f.category, f.title) for f in new_findings}

        resolved = list(old_set - new_set)
        still_open = list(old_set & new_set)
        new = list(new_set - old_set)

        return {
            'resolved': [f"{cat}: {title}" for cat, title in resolved],
            'still_open': [f"{cat}: {title}" for cat, title in still_open],
            'new': [f"{cat}: {title}" for cat, title in new]
        }
