import google.generativeai as genai
from typing import List, Dict
from .reviewers import Finding
from .config import settings


class Explainer:
    def __init__(self):
        self.client = None
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.client = genai.GenerativeModel('gemini-1.5-flash')
        self.cache: Dict[str, Dict[str, str]] = {}

    def explain_findings(self, findings: List[Finding], language: str) -> List[Finding]:
        if not self.client:
            return findings

        for finding in findings:
            cache_key = f"{finding.rule_id}_{language}"
            if cache_key in self.cache:
                finding.ai_explanation = self.cache[cache_key]['explanation']
                finding.fix_code = self.cache[cache_key]['fix_code']
            else:
                explanation = self._get_explanation(finding, language)
                finding.ai_explanation = explanation.get('explanation', '')
                finding.fix_code = explanation.get('fix_code', '')
                self.cache[cache_key] = explanation

        return findings

    def _get_explanation(self, finding: Finding, language: str) -> Dict[str, str]:
        try:
            prompt = f"""You are a code review assistant for {language} programmers. Explain this code issue in 3 simple sentences for a beginner student, then provide a corrected code snippet.

Issue:
Category: {finding.category}
Severity: {finding.severity}
Title: {finding.title}
Description: {finding.description}
Suggested fix: {finding.fix}

Respond in this exact JSON format:
{{
  "explanation": "3-sentence beginner-friendly explanation",
  "fix_code": "corrected code snippet"
}}"""

            response = self.client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=500,
                    temperature=0.7,
                )
            )

            import json
            response_text = response.text
            try:
                result = json.loads(response_text)
                return {
                    'explanation': result.get('explanation', ''),
                    'fix_code': result.get('fix_code', '')
                }
            except json.JSONDecodeError:
                return {
                    'explanation': response_text[:200],
                    'fix_code': ''
                }
        except Exception as e:
            return {
                'explanation': '',
                'fix_code': ''
            }
