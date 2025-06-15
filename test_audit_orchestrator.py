#!/usr/bin/env python3

import sys
import os
import asyncio
from unittest.mock import Mock, AsyncMock

sys.path.append('/home/ubuntu/skyvern')

class MockScrapedPage:
    def __init__(self):
        self.elements = [
            {
                'id': 'header_1',
                'tagName': 'h1',
                'interactable': True,
                'attributes': {'class': 'header'}
            },
            {
                'id': 'content_1',
                'tagName': 'p',
                'interactable': True,
                'attributes': {'class': 'content'}
            }
        ]
        self.id_to_css_dict = {
            'header_1': '.header',
            'content_1': '.content'
        }

class MockPage:
    def __init__(self):
        self.current_url = "https://example.com"
    
    async def evaluate(self, script):
        if '.header' in script:
            return {
                'color': '#ff0000',
                'background-color': '#ffffff',
                'font-family': 'Comic Sans MS',
                'font-size': '24px',
                'font-weight': 'bold',
                'margin': '13px',
                'padding': '10px',
                '_width': '800px',
                '_height': '60px',
                '_x': '0px',
                '_y': '0px',
                '_text_content': 'Header Text'
            }
        elif '.content' in script:
            return {
                'color': '#007bff',
                'background-color': '#f8f9fa',
                'font-family': 'Arial, Helvetica, sans-serif',
                'font-size': '16px',
                'font-weight': 'normal',
                'margin': '16px',
                'padding': '12px',
                '_width': '600px',
                '_height': '100px',
                '_x': '100px',
                '_y': '80px',
                '_text_content': 'Content text'
            }
        return None
    
    async def goto(self, url):
        self.current_url = url
    
    async def wait_for_load_state(self, state):
        pass
    
    async def screenshot(self, path=None, full_page=False):
        return b"mock_screenshot_data"

async def mock_scrape_web_unsafe(page, url):
    return MockScrapedPage()

import skyvern.webeye.audit.audit_orchestrator as orchestrator_module
orchestrator_module.scrape_web_unsafe = mock_scrape_web_unsafe

from skyvern.webeye.audit.audit_orchestrator import AuditOrchestrator

async def test_audit_orchestrator():
    print("Testing Audit Orchestrator")
    print("=" * 40)
    
    orchestrator = AuditOrchestrator()
    mock_page = MockPage()
    
    print("\n1. Testing guidelines loading...")
    try:
        orchestrator.load_guidelines('/home/ubuntu/skyvern/examples/brand_guidelines_sample.json')
        print(f"✅ Guidelines loaded: {orchestrator.guidelines.name}")
    except Exception as e:
        print(f"❌ Failed to load guidelines: {e}")
        return False
    
    print("\n2. Testing single page audit...")
    try:
        audit_result = await orchestrator.audit_page(mock_page, "https://example.com")
        print(f"✅ Page audit completed")
        print(f"   - URL: {audit_result.url}")
        print(f"   - Elements checked: {audit_result.total_elements_checked}")
        print(f"   - Violations: {len(audit_result.violations)}")
        print(f"   - Compliance: {audit_result.compliance_score:.1%}")
    except Exception as e:
        print(f"❌ Page audit failed: {e}")
        return False
    
    print("\n3. Testing audit with screenshot...")
    try:
        result = await orchestrator.audit_page_with_screenshot(
            mock_page, 
            "https://example.com",
            screenshot_path="/tmp/test_screenshot.png"
        )
        print(f"✅ Audit with screenshot completed")
        print(f"   - Screenshot path: {result['screenshot_path']}")
        print(f"   - Screenshot data size: {len(result['screenshot_data'])} bytes")
        print(f"   - Summary report generated: {len(result['summary_report'])} chars")
    except Exception as e:
        print(f"❌ Audit with screenshot failed: {e}")
        return False
    
    print("\n4. Testing multiple page audit...")
    try:
        urls = ["https://example.com/page1", "https://example.com/page2"]
        results = await orchestrator.audit_multiple_pages(urls, mock_page)
        print(f"✅ Multiple page audit completed")
        print(f"   - Pages audited: {len(results)}")
        for i, result in enumerate(results):
            print(f"   - Page {i+1}: {result.compliance_score:.1%} compliance")
    except Exception as e:
        print(f"❌ Multiple page audit failed: {e}")
        return False
    
    print("\n5. Testing consolidated report...")
    try:
        consolidated_report = orchestrator.generate_consolidated_report(results)
        print(f"✅ Consolidated report generated")
        print(f"   - Report length: {len(consolidated_report)} characters")
        print("   - Report preview:")
        print("   " + consolidated_report.split('\n')[0])
        print("   " + consolidated_report.split('\n')[1])
    except Exception as e:
        print(f"❌ Consolidated report failed: {e}")
        return False
    
    print("\n6. Testing brand inconsistency detection...")
    try:
        inconsistencies = await orchestrator.detect_brand_inconsistencies(results)
        print(f"✅ Brand inconsistency detection completed")
        print(f"   - Inconsistencies found: {len(inconsistencies)}")
        for inconsistency in inconsistencies:
            print(f"   - {inconsistency}")
    except Exception as e:
        print(f"❌ Brand inconsistency detection failed: {e}")
        return False
    
    print("\n" + "=" * 40)
    print("✅ All audit orchestrator tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_audit_orchestrator())
    sys.exit(0 if success else 1)
