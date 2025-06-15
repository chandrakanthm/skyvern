#!/usr/bin/env python3

import sys
import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

sys.path.append('/home/ubuntu/skyvern')

from skyvern.forge.sdk.brand_guidelines.config_manager import BrandGuidelinesConfigManager
from skyvern.forge.sdk.audit.compliance_engine import ComplianceEngine
from skyvern.forge.sdk.brand_guidelines.models import AuditResult

class IsolatedAuditOrchestrator:
    def __init__(self, guidelines_config_path: Optional[str] = None):
        self.config_manager = BrandGuidelinesConfigManager()
        self.guidelines = None
        self.compliance_engine = None
        
        if guidelines_config_path:
            self.load_guidelines(guidelines_config_path)
    
    def load_guidelines(self, config_path: str) -> None:
        self.guidelines = self.config_manager.load_from_file(config_path)
        self.compliance_engine = ComplianceEngine(self.guidelines)
        print(f"Brand guidelines loaded: {self.guidelines.name} v{self.guidelines.version}")
    
    async def audit_mock_page(self, url: str) -> AuditResult:
        if not self.guidelines or not self.compliance_engine:
            raise ValueError("Brand guidelines must be loaded before running audit")
        
        mock_visual_segments = [
            {
                'element_id': 'header_1',
                'css_selector': '.header',
                'coordinates': (0, 0, 800, 60),
                'visual_properties': {
                    'colors': {
                        'color': '#ff0000',  # Should violate
                        'background-color': '#ffffff'  # Should violate
                    },
                    'typography': {
                        'font-family': 'Comic Sans MS',  # Should violate
                        'font-size': '24px',
                        'font-weight': 'bold'
                    },
                    'spacing': {
                        'margin': '13px',  # Should violate
                        'padding': '10px'
                    }
                }
            },
            {
                'element_id': 'content_1',
                'css_selector': '.content',
                'coordinates': (100, 80, 700, 180),
                'visual_properties': {
                    'colors': {
                        'color': '#007bff',  # Should be valid
                        'background-color': '#f8f9fa'  # Should be valid
                    },
                    'typography': {
                        'font-family': 'Arial, Helvetica, sans-serif',  # Should be valid
                        'font-size': '16px',
                        'font-weight': 'normal'
                    },
                    'spacing': {
                        'margin': '16px',  # Should be valid
                        'padding': '12px'  # Should be valid
                    }
                }
            }
        ]
        
        audit_result = await self.compliance_engine.audit_visual_segments(
            mock_visual_segments, url
        )
        
        return audit_result
    
    async def audit_multiple_mock_pages(self, page_urls: List[str]) -> List[AuditResult]:
        results = []
        
        for url in page_urls:
            audit_result = await self.audit_mock_page(url)
            results.append(audit_result)
        
        return results
    
    def generate_consolidated_report(self, audit_results: List[AuditResult]) -> str:
        if not audit_results:
            return "No audit results to report."
        
        total_elements = sum(result.total_elements_checked for result in audit_results)
        total_violations = sum(len(result.violations) for result in audit_results)
        avg_compliance = sum(result.compliance_score for result in audit_results) / len(audit_results)
        
        report = f"""
Consolidated Brand Compliance Report
===================================

Pages Audited: {len(audit_results)}
Total Elements Checked: {total_elements}
Total Violations Found: {total_violations}
Average Compliance Score: {avg_compliance:.1%}

Individual Page Results:
"""
        
        for i, result in enumerate(audit_results, 1):
            report += f"""
{i}. {result.url}
   - Elements: {result.total_elements_checked}
   - Violations: {len(result.violations)}
   - Compliance: {result.compliance_score:.1%}
"""
        
        return report

async def test_isolated_audit_orchestrator():
    print("Testing Isolated Audit Orchestrator")
    print("=" * 50)
    
    orchestrator = IsolatedAuditOrchestrator()
    
    print("\n1. Testing guidelines loading...")
    try:
        orchestrator.load_guidelines('/home/ubuntu/skyvern/examples/brand_guidelines_sample.json')
        print(f"✅ Guidelines loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load guidelines: {e}")
        return False
    
    print("\n2. Testing single page audit...")
    try:
        audit_result = await orchestrator.audit_mock_page("https://example.com")
        print(f"✅ Page audit completed")
        print(f"   - URL: {audit_result.url}")
        print(f"   - Elements checked: {audit_result.total_elements_checked}")
        print(f"   - Violations: {len(audit_result.violations)}")
        print(f"   - Compliance: {audit_result.compliance_score:.1%}")
        
        if len(audit_result.violations) > 0:
            print("   - Sample violations:")
            for violation in audit_result.violations[:3]:
                print(f"     * {violation.element_id}: {violation.violation_type}")
    except Exception as e:
        print(f"❌ Page audit failed: {e}")
        return False
    
    print("\n3. Testing multiple page audit...")
    try:
        urls = ["https://example.com/page1", "https://example.com/page2", "https://example.com/page3"]
        results = await orchestrator.audit_multiple_mock_pages(urls)
        print(f"✅ Multiple page audit completed")
        print(f"   - Pages audited: {len(results)}")
        for i, result in enumerate(results):
            print(f"   - Page {i+1}: {result.compliance_score:.1%} compliance, {len(result.violations)} violations")
    except Exception as e:
        print(f"❌ Multiple page audit failed: {e}")
        return False
    
    print("\n4. Testing consolidated report...")
    try:
        consolidated_report = orchestrator.generate_consolidated_report(results)
        print(f"✅ Consolidated report generated")
        print(f"   - Report length: {len(consolidated_report)} characters")
        print("   - Report preview:")
        lines = consolidated_report.strip().split('\n')
        for line in lines[:8]:
            print(f"     {line}")
        print("     ...")
    except Exception as e:
        print(f"❌ Consolidated report failed: {e}")
        return False
    
    print("\n5. Testing individual summary reports...")
    try:
        for i, result in enumerate(results[:2]):
            summary = orchestrator.compliance_engine.generate_summary_report(result)
            print(f"✅ Summary report {i+1} generated ({len(summary)} chars)")
    except Exception as e:
        print(f"❌ Summary report generation failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All isolated audit orchestrator tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_isolated_audit_orchestrator())
    sys.exit(0 if success else 1)
