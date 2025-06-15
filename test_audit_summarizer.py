#!/usr/bin/env python3

import sys
import os
import asyncio
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock

sys.path.append('/home/ubuntu/skyvern')

from skyvern.forge.sdk.brand_guidelines.config_manager import BrandGuidelinesConfigManager
from skyvern.forge.sdk.audit.compliance_engine import ComplianceEngine
from skyvern.forge.sdk.audit.audit_summarizer import AuditSummarizer

class MockLLMHandler:
    def __init__(self):
        self.call_count = 0
    
    async def __call__(self, prompt: str, parameters: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
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

def create_mock_audit_result():
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
    return asyncio.run(compliance_engine.audit_visual_segments(mock_visual_segments, "https://example.com"))

async def test_audit_summarizer():
    print("Testing Audit Summarizer")
    print("=" * 40)
    
    mock_llm = MockLLMHandler()
    summarizer = AuditSummarizer(llm_handler=mock_llm)
    
    print("\n1. Creating mock audit result...")
    audit_result = create_mock_audit_result()
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
    
    print("\n6. Testing executive summary for multiple pages...")
    try:
        audit_results = [audit_result, audit_result, audit_result]  # Simulate 3 pages
        exec_summary = await summarizer.generate_executive_summary(audit_results)
        print(f"✅ Executive summary generated ({len(exec_summary)} chars)")
        print("   Preview:")
        lines = exec_summary.strip().split('\n')
        for line in lines[:5]:
            print(f"     {line}")
        print("     ...")
    except Exception as e:
        print(f"❌ Executive summary failed: {e}")
        return False
    
    print("\n7. Testing summarizer without LLM (fallback)...")
    try:
        fallback_summarizer = AuditSummarizer(llm_handler=None)
        fallback_summary = await fallback_summarizer.generate_natural_language_summary(audit_result)
        print(f"✅ Fallback summary generated ({len(fallback_summary)} chars)")
        print("   This should be the basic summary format")
    except Exception as e:
        print(f"❌ Fallback summary failed: {e}")
        return False
    
    print("\n" + "=" * 40)
    print("✅ All audit summarizer tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_audit_summarizer())
    sys.exit(0 if success else 1)
