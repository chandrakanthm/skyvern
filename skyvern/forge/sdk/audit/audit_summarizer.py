from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Any
import structlog
import json

from skyvern.forge.sdk.brand_guidelines.models import AuditResult, AuditViolation
from skyvern.forge.sdk.api.llm.models import LLMAPIHandler
from skyvern.forge.sdk.settings_manager import SettingsManager

LOG = structlog.get_logger()


class AuditSummarizer:
    def __init__(self, llm_handler: Optional[LLMAPIHandler] = None):
        self.llm_handler = llm_handler
        self.settings = SettingsManager.get_settings()
    
    async def generate_natural_language_summary(self, audit_result: AuditResult, 
                                              user_query: Optional[str] = None) -> str:
        if not self.llm_handler:
            LOG.warning("No LLM handler provided, falling back to basic summary")
            return self._generate_basic_summary(audit_result)
        
        try:
            prompt = self._build_summary_prompt(audit_result, user_query)
            
            response = await self.llm_handler(
                prompt=prompt,
                parameters={
                    "temperature": 0.3,
                    "max_tokens": 1000
                }
            )
            
            if response and "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0]["message"]["content"].strip()
            else:
                LOG.warning("Invalid LLM response format, falling back to basic summary")
                return self._generate_basic_summary(audit_result)
                
        except Exception as e:
            LOG.error("Failed to generate natural language summary", error=str(e))
            return self._generate_basic_summary(audit_result)
    
    def _build_summary_prompt(self, audit_result: AuditResult, user_query: Optional[str] = None) -> str:
        violations_summary = self._format_violations_for_prompt(audit_result.violations)
        
        base_prompt = f"""
You are a brand compliance expert analyzing a website audit. Please provide a clear, professional summary of the audit findings.

AUDIT DETAILS:
- Website: {audit_result.url}
- Brand Guidelines: {audit_result.guidelines.name} (v{audit_result.guidelines.version})
- Elements Checked: {audit_result.total_elements_checked}
- Compliance Score: {audit_result.compliance_score:.1%}
- Total Violations: {len(audit_result.violations)}

VIOLATIONS FOUND:
{violations_summary}

BRAND GUIDELINES CONTEXT:
- Colors: {len(audit_result.guidelines.colors)} defined color rules
- Fonts: {len(audit_result.guidelines.fonts)} defined font rules  
- Spacing: {len(audit_result.guidelines.spacing)} defined spacing rules
"""

        if user_query:
            base_prompt += f"""
USER QUESTION: {user_query}

Please answer the user's specific question about this audit while providing relevant context from the findings above.
"""
        else:
            base_prompt += """
Please provide:
1. An executive summary of the overall compliance status
2. Key areas of concern that need attention
3. Specific actionable recommendations for improvement
4. Priority level for addressing the violations

Keep the summary professional, clear, and actionable for web developers and brand managers.
"""
        
        return base_prompt
    
    def _format_violations_for_prompt(self, violations: List[AuditViolation]) -> str:
        if not violations:
            return "No violations found - excellent compliance!"
        
        violations_by_type = {}
        for violation in violations:
            if violation.violation_type not in violations_by_type:
                violations_by_type[violation.violation_type] = []
            violations_by_type[violation.violation_type].append(violation)
        
        formatted_violations = []
        for violation_type, type_violations in violations_by_type.items():
            formatted_violations.append(f"\n{violation_type.upper()} VIOLATIONS ({len(type_violations)}):")
            
            for violation in type_violations[:3]:  # Show first 3 examples
                formatted_violations.append(f"  - Element: {violation.element_id}")
                formatted_violations.append(f"    Issue: {violation.description}")
                if violation.expected_value:
                    formatted_violations.append(f"    Expected: {violation.expected_value}")
                if violation.actual_value:
                    formatted_violations.append(f"    Actual: {violation.actual_value}")
                formatted_violations.append(f"    Severity: {violation.severity}")
                formatted_violations.append("")
            
            if len(type_violations) > 3:
                formatted_violations.append(f"  ... and {len(type_violations) - 3} more {violation_type} violations")
        
        return "\n".join(formatted_violations)
    
    def _generate_basic_summary(self, audit_result: AuditResult) -> str:
        compliance_percentage = audit_result.compliance_score * 100
        total_violations = len(audit_result.violations)
        
        summary = f"""
Brand Compliance Summary for {audit_result.url}

Overall Status: {compliance_percentage:.1f}% Compliant
Elements Analyzed: {audit_result.total_elements_checked}
Violations Found: {total_violations}

"""
        
        if compliance_percentage >= 90:
            summary += "✅ EXCELLENT: Your website shows strong brand compliance with only minor issues to address.\n\n"
        elif compliance_percentage >= 70:
            summary += "⚠️  GOOD: Your website has good brand compliance but some areas need attention.\n\n"
        elif compliance_percentage >= 50:
            summary += "🔶 MODERATE: Your website has moderate compliance issues that should be addressed.\n\n"
        else:
            summary += "🚨 NEEDS ATTENTION: Your website has significant brand compliance issues requiring immediate attention.\n\n"
        
        if total_violations > 0:
            violations_by_type = {}
            violations_by_severity = {}
            
            for violation in audit_result.violations:
                violations_by_type[violation.violation_type] = violations_by_type.get(violation.violation_type, 0) + 1
                violations_by_severity[violation.severity] = violations_by_severity.get(violation.severity, 0) + 1
            
            summary += "Issue Breakdown:\n"
            for violation_type, count in violations_by_type.items():
                summary += f"  • {violation_type.title()}: {count} issues\n"
            
            summary += "\nPriority Levels:\n"
            for severity in ['high', 'medium', 'low']:
                if severity in violations_by_severity:
                    summary += f"  • {severity.title()}: {violations_by_severity[severity]} issues\n"
            
            summary += "\nRecommendations:\n"
            if 'high' in violations_by_severity:
                summary += "  1. Address high-priority violations first (colors, primary fonts)\n"
            if 'medium' in violations_by_severity:
                summary += "  2. Review medium-priority issues (secondary fonts, borders)\n"
            if 'low' in violations_by_severity:
                summary += "  3. Fine-tune low-priority spacing and layout issues\n"
        
        return summary
    
    async def answer_compliance_query(self, audit_result: AuditResult, query: str) -> str:
        return await self.generate_natural_language_summary(audit_result, query)
    
    async def generate_executive_summary(self, audit_results: List[AuditResult]) -> str:
        if not audit_results:
            return "No audit results available for summary."
        
        if len(audit_results) == 1:
            return await self.generate_natural_language_summary(audit_results[0])
        
        total_elements = sum(result.total_elements_checked for result in audit_results)
        total_violations = sum(len(result.violations) for result in audit_results)
        avg_compliance = sum(result.compliance_score for result in audit_results) / len(audit_results)
        
        multi_page_summary = f"""
Multi-Page Brand Compliance Executive Summary

Pages Audited: {len(audit_results)}
Total Elements: {total_elements}
Average Compliance: {avg_compliance:.1%}
Total Violations: {total_violations}

Page-by-Page Results:
"""
        
        for i, result in enumerate(audit_results, 1):
            multi_page_summary += f"{i}. {result.url}: {result.compliance_score:.1%} compliant ({len(result.violations)} violations)\n"
        
        if self.llm_handler:
            try:
                prompt = f"""
As a brand compliance expert, analyze this multi-page audit summary and provide strategic insights:

{multi_page_summary}

Please provide:
1. Overall brand consistency assessment across all pages
2. Common patterns in violations across pages
3. Strategic recommendations for improving brand compliance
4. Priority areas for the development team to focus on

Keep the response executive-level, focusing on business impact and strategic actions.
"""
                
                response = await self.llm_handler(
                    prompt=prompt,
                    parameters={
                        "temperature": 0.3,
                        "max_tokens": 800
                    }
                )
                
                if response and "choices" in response and len(response["choices"]) > 0:
                    return response["choices"][0]["message"]["content"].strip()
                    
            except Exception as e:
                LOG.error("Failed to generate executive summary with LLM", error=str(e))
        
        return multi_page_summary
    
    def get_violation_insights(self, violations: List[AuditViolation]) -> Dict[str, Any]:
        if not violations:
            return {
                "total_violations": 0,
                "by_type": {},
                "by_severity": {},
                "most_common_issues": [],
                "elements_affected": 0
            }
        
        by_type = {}
        by_severity = {}
        elements_affected = set()
        
        for violation in violations:
            by_type[violation.violation_type] = by_type.get(violation.violation_type, 0) + 1
            by_severity[violation.severity] = by_severity.get(violation.severity, 0) + 1
            elements_affected.add(violation.element_id)
        
        most_common_issues = sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "total_violations": len(violations),
            "by_type": by_type,
            "by_severity": by_severity,
            "most_common_issues": most_common_issues,
            "elements_affected": len(elements_affected)
        }
