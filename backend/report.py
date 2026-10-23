from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime
from typing import List
from .reviewers import Finding


class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1a1a2e')
        ))
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#16213e')
        ))
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=10,
            spaceAfter=6
        ))

    def generate_pdf(self, session_id: str, overall_score: int, grade: str,
                     language: str, review_type: str, findings: List[Finding]) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
                                topMargin=72, bottomMargin=18)

        story = []

        # Cover page
        story.append(Paragraph("Code Review Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.2 * inch))

        # Summary table
        summary_data = [
            ['Session ID', session_id],
            ['Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Language', language],
            ['Review Type', review_type],
            ['Overall Score', str(overall_score)],
            ['Grade', grade]
        ]

        summary_table = Table(summary_data, colWidths=[2 * inch, 3 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e94560')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.5 * inch))

        # Executive summary
        story.append(Paragraph("Executive Summary", self.styles['CustomHeading']))

        severity_counts = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}
        for finding in findings:
            if finding.severity in severity_counts:
                severity_counts[finding.severity] += 1

        summary_text = f"""
        This code review identified a total of {len(findings)} issues across {language} code.
        <br/>
        • Critical issues: {severity_counts['Critical']}
        <br/>
        • High issues: {severity_counts['High']}
        <br/>
        • Medium issues: {severity_counts['Medium']}
        <br/>
        • Low issues: {severity_counts['Low']}
        """
        story.append(Paragraph(summary_text, self.styles['CustomBody']))
        story.append(Spacer(1, 0.3 * inch))

        # Findings by severity
        story.append(Paragraph("Detailed Findings", self.styles['CustomHeading']))

        severity_order = ['Critical', 'High', 'Medium', 'Low']
        severity_colors = {
            'Critical': colors.red,
            'High': colors.orange,
            'Medium': colors.yellow,
            'Low': colors.green
        }

        for severity in severity_order:
            severity_findings = [f for f in findings if f.severity == severity]
            if severity_findings:
                story.append(Paragraph(f"{severity} Issues ({len(severity_findings)})", self.styles['CustomHeading']))

                for finding in severity_findings:
                    finding_data = [
                        ['Line', str(finding.line_no or 'N/A')],
                        ['Title', finding.title],
                        ['Description', finding.description],
                        ['Fix', finding.fix]
                    ]

                    if finding.ai_explanation:
                        finding_data.append(['AI Explanation', finding.ai_explanation])
                    if finding.fix_code:
                        finding_data.append(['Code Fix', finding.fix_code])

                    finding_table = Table(finding_data, colWidths=[1.5 * inch, 4 * inch])
                    finding_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (0, -1), severity_colors.get(severity, colors.grey)),
                        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                        ('LEFTPADDING', (0, 0), (-1, -1), 6),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
                    ]))
                    story.append(finding_table)
                    story.append(Spacer(1, 0.2 * inch))

        # Improvement suggestions
        story.append(PageBreak())
        story.append(Paragraph("Improvement Suggestions", self.styles['CustomHeading']))

        suggestions = self._generate_suggestions(severity_counts, language)
        for suggestion in suggestions:
            story.append(Paragraph(f"• {suggestion}", self.styles['CustomBody']))
            story.append(Spacer(1, 0.1 * inch))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _generate_suggestions(self, severity_counts: dict, language: str) -> List[str]:
        suggestions = []

        if severity_counts['Critical'] > 0:
            suggestions.append("Address Critical security issues immediately to prevent potential vulnerabilities.")

        if severity_counts['High'] > 0:
            suggestions.append("Prioritize High-severity issues to improve code quality and maintainability.")

        if severity_counts['Medium'] > 0:
            suggestions.append("Review Medium-severity issues to enhance code readability and performance.")

        if severity_counts['Low'] > 0:
            suggestions.append("Consider addressing Low-severity issues to follow best practices.")

        if language == "python":
            suggestions.append("Consider using type hints for better code documentation.")
            suggestions.append("Add comprehensive docstrings to all functions and classes.")
            suggestions.append("Run tests with pytest to ensure code correctness.")

        return suggestions
