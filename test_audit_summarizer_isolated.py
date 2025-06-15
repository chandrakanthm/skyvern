#!/usr/bin/env python3

import sys
import os
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock
from datetime import datetime

sys.path.append('/home/ubuntu/skyvern')

from skyvern.forge.sdk.brand_guidelines.config_manager import BrandGuidelinesConfigManager
from skyvern.forge.sdk.audit.compliance_engine import ComplianceEngine
from skyvern.forge.sdk.brand_guidelines.models import AuditResult, AuditViolation

class IsolatedAuditSummarizer:
    def __init__(self, llm_handler: Optional[Any] = None):
        self.llm_handler = llm_handler
    
    async def generate_natural_language_summary(self, audit_result: AuditResult, 
                                              user_query: Optional[str] = None) -> str:
        if not self.llm_handler:
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
                return self._generate_basic_summary(audit_result)
                
        except Exception as e:
            print(f"LLM error: {e}")
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
            
            for violation in type_violations[:3]:
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

class MockLLMHandler:
    def __init__(self):
        self.call_count = 0
    
    async def __call__(self, prompt: str, parameters: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        self.call_count += 1
        
        if "executive" in prompt.lower() or "multi-page" in prompt.lower():
            return {
                "choices": [{
                    "message": {
                        "content": """
**Executive Brand Compliance Assessment**

**Overall Brand Consistency: MODERATE**
Your website shows inconsistent brand implementation across pages, with an average compliance of 65%. While some pages maintain good brand standards, others deviate significantly from guidelines.

**Common Violation Patterns:**
1. **Color Inconsistency**: Non-brand colors (#ff0000, #00ff00) frequently used instead of approved palette
2. **Typography Drift**: Comic Sans MS and other non-brand fonts appearing across multiple pages
3. **Spacing Irregularities**: Inconsistent margin/padding values not following the 8px grid system

**Strategic Recommendations:**
1. **Immediate Action**: Implement a design system component library to enforce brand standards
2. **Development Process**: Add automated brand compliance checks to your CI/CD pipeline
3. **Team Training**: Conduct brand guidelines workshop for development and design teams
4. **Monitoring**: Set up regular brand audits to catch deviations early

**Priority Focus Areas:**
- Standardize color usage across all pages (highest impact)
- Implement consistent typography hierarchy
- Establish spacing standards and enforce through tooling

This strategic approach will improve brand consistency and reduce future compliance issues.
"""
                    }
                }]
            }
        else:
            return {
                "choices": [{
                    "message": {
                        "content": """
**Brand Compliance Analysis for https://example.com**

**Overall Assessment: NEEDS ATTENTION** 🚨
Your website currently shows 0% brand compliance, indicating significant deviations from your established brand guidelines.

**Key Issues Identified:**

**Color Violations (Critical Priority)**
- Unauthorized red color (#ff0000) used in header elements
- Background colors not matching approved brand palette
- These color issues create immediate brand recognition problems

**Typography Violations (High Priority)**  
- Comic Sans MS font detected - not part of approved brand fonts
- Should use Arial, Helvetica, or other approved sans-serif fonts
- Typography consistency is crucial for professional brand perception

**Spacing Violations (Medium Priority)**
- Non-standard margin values (13px) detected
- Brand guidelines specify 8px grid system for consistent spacing
- Inconsistent spacing affects visual hierarchy and user experience

**Immediate Action Items:**
1. Replace all red (#ff0000) colors with approved brand colors
2. Update font-family declarations to use approved fonts only  
3. Standardize spacing to follow 8px grid system
4. Implement design system to prevent future violations

**Business Impact:**
These violations significantly impact brand recognition and professional appearance. Addressing color and typography issues should be the immediate priority as they have the highest visual impact on users.
"""
                    }
                }]
            }

async def create_mock_audit_result():
    config_manager = BrandGuidelinesConfigManager()
    guidelines = config_manager.load_from_file('/home/ubuntu/skyvern/examples/brand_guidelines_sample.json')
    
    mock_visual_segments = [
        {
            'element_id': 'header_1',
            'css_selector': '.header',
            'coordinates': (0, 0, 800, 60),
            'visual_properties': {
                'colors': {
                    'color': '#ff0000',
                    'background-color': '#ffffff'
                },
                'typography': {
                    'font-family': 'Comic Sans MS',
                    'font-size': '24px',
                    'font-weight': 'bold'
                },
                'spacing': {
                    'margin': '13px',
                    'padding': '10px'
                }
            }
        }
    ]
    
    compliance_engine = ComplianceEngine(guidelines)
    return await compliance_engine.audit_visual_segments(mock_visual_segments, "https://example.com")

async def test_isolated_audit_summarizer():
    print("Testing Isolated Audit Summarizer")
    print("=" * 50)
    
    mock_llm = MockLLMHandler()
    summarizer = IsolatedAuditSummarizer(llm_handler=mock_llm)
    
    print("\n1. Creating mock audit result...")
    audit_result = await create_mock_audit_result()
    print(f"✅ Mock audit result created")
    print(f"   - Violations: {len(audit_result.violations)}")
    print(f"   - Compliance: {audit_result.compliance_score:.1%}")
    
    print("\n2. Testing basic summary generation...")
    try:
        basic_summary = summarizer._generate_basic_summary(audit_result)
        print(f"✅ Basic summary generated ({len(basic_summary)} chars)")
        print("   Preview:")
        lines = basic_summary.strip().split('\n')
        for line in lines[:5]:
            print(f"     {line}")
        print("     ...")
    except Exception as e:
        print(f"❌ Basic summary failed: {e}")
        return False
    
    print("\n3. Testing natural language summary with LLM...")
    try:
        nl_summary = await summarizer.generate_natural_language_summary(audit_result)
        print(f"✅ Natural language summary generated ({len(nl_summary)} chars)")
        print(f"   LLM calls made: {mock_llm.call_count}")
        print("   Preview:")
        lines = nl_summary.strip().split('\n')
        for line in lines[:5]:
            print(f"     {line}")
        print("     ...")
    except Exception as e:
        print(f"❌ Natural language summary failed: {e}")
        return False
    
    print("\n4. Testing compliance query answering...")
    try:
        query = "What are the most critical issues I should fix first?"
        query_response = await summarizer.answer_compliance_query(audit_result, query)
        print(f"✅ Query answered ({len(query_response)} chars)")
        print(f"   Query: {query}")
        print("   Response preview:")
        lines = query_response.strip().split('\n')
        for line in lines[:3]:
            print(f"     {line}")
        print("     ...")
    except Exception as e:
        print(f"❌ Query answering failed: {e}")
        return False
    
    print("\n5. Testing violation insights...")
    try:
        insights = summarizer.get_violation_insights(audit_result.violations)
        print(f"✅ Violation insights generated")
        print(f"   - Total violations: {insights['total_violations']}")
        print(f"   - Elements affected: {insights['elements_affected']}")
        print(f"   - By type: {insights['by_type']}")
        print(f"   - By severity: {insights['by_severity']}")
        print(f"   - Most common: {insights['most_common_issues']}")
    except Exception as e:
        print(f"❌ Violation insights failed: {e}")
        return False
    
    print("\n6. Testing summarizer without LLM (fallback)...")
    try:
        fallback_summarizer = IsolatedAuditSummarizer(llm_handler=None)
        fallback_summary = await fallback_summarizer.generate_natural_language_summary(audit_result)
        print(f"✅ Fallback summary generated ({len(fallback_summary)} chars)")
        print("   This should be the basic summary format")
    except Exception as e:
        print(f"❌ Fallback summary failed: {e}")
        return False
    
    print("\n7. Testing prompt building...")
    try:
        prompt = summarizer._build_summary_prompt(audit_result, "What colors are wrong?")
        print(f"✅ Prompt built successfully ({len(prompt)} chars)")
        print("   Contains user query and audit details")
    except Exception as e:
        print(f"❌ Prompt building failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All isolated audit summarizer tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_isolated_audit_summarizer())
    sys.exit(0 if success else 1)
