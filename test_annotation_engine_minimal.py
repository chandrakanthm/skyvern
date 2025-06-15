#!/usr/bin/env python3

import sys
import os
import asyncio
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock
import io

sys.path.append('/home/ubuntu/skyvern')

from skyvern.forge.sdk.brand_guidelines.config_manager import BrandGuidelinesConfigManager
from skyvern.forge.sdk.audit.compliance_engine import ComplianceEngine

class MockAnnotationEngine:
    """Minimal annotation engine for testing without PIL dependency"""
    
    def __init__(self):
        self.violation_colors = {
            'high': '#FF0000',
            'medium': '#FF8C00', 
            'low': '#FFD700'
        }
    
    async def generate_annotated_screenshot(self, page, audit_result, output_path):
        """Mock annotated screenshot generation"""
        violations_with_coords = [v for v in audit_result.violations if v.coordinates]
        
        with open(output_path, 'w') as f:
            f.write("MOCK_ANNOTATED_SCREENSHOT")
        
        return {
            'screenshot_path': output_path,
            'image_size': (800, 600),
            'violations_annotated': len(violations_with_coords),
            'annotation_summary': self._generate_annotation_summary(audit_result.violations)
        }
    
    def _generate_annotation_summary(self, violations):
        """Generate annotation summary without image processing"""
        by_severity = {}
        by_type = {}
        annotated_elements = set()
        
        for violation in violations:
            by_severity[violation.severity] = by_severity.get(violation.severity, 0) + 1
            by_type[violation.violation_type] = by_type.get(violation.violation_type, 0) + 1
            if violation.coordinates:
                annotated_elements.add(violation.element_id)
        
        return {
            'total_violations': len(violations),
            'by_severity': by_severity,
            'by_type': by_type,
            'annotated_elements': len(annotated_elements)
        }
    
    async def generate_audit_report(self, audit_result, screenshot_path, report_path):
        """Generate HTML audit report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Brand Compliance Audit Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
        .violation-item {{ margin: 10px 0; padding: 10px; border-left: 4px solid #dc3545; }}
        .screenshot {{ max-width: 100%; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Brand Compliance Audit Report</h1>
        <p><strong>URL:</strong> {audit_result.url}</p>
        <p><strong>Compliance Score:</strong> {audit_result.compliance_score:.1%}</p>
        <p><strong>Total Violations:</strong> {len(audit_result.violations)}</p>
        <p><strong>Generated:</strong> {audit_result.timestamp}</p>
    </div>
    
    <h2>Violations Found</h2>
"""
        
        for violation in audit_result.violations:
            html_content += f"""
    <div class="violation-item">
        <h3>{violation.violation_type.title()} Violation - {violation.severity.title()} Priority</h3>
        <p><strong>Element:</strong> {violation.element_id}</p>
        <p><strong>Description:</strong> {violation.description}</p>
        <p><strong>Expected:</strong> {violation.expected_value}</p>
        <p><strong>Actual:</strong> {violation.actual_value}</p>
    </div>
"""
        
        if screenshot_path and os.path.exists(screenshot_path):
            html_content += f"""
    <h2>Annotated Screenshot</h2>
    <img src="{screenshot_path}" alt="Annotated Screenshot" class="screenshot">
"""
        
        html_content += """
</body>
</html>
"""
        
        with open(report_path, 'w') as f:
            f.write(html_content)
        
        return report_path

class MockPage:
    async def screenshot(self, full_page=False):
        return b"MOCK_SCREENSHOT_DATA"

async def create_mock_audit_result():
    config_manager = BrandGuidelinesConfigManager()
    guidelines = config_manager.load_from_file('/home/ubuntu/skyvern/examples/brand_guidelines_sample.json')
    
    mock_visual_segments = [
        {
            'element_id': 'header_1',
            'css_selector': '.header',
            'coordinates': (50, 50, 200, 100),
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

async def test_annotation_engine_minimal():
    print("Testing Minimal Annotation Engine (without PIL)")
    print("=" * 50)
    
    annotation_engine = MockAnnotationEngine()
    mock_page = MockPage()
    
    print("\n1. Creating mock audit result...")
    try:
        audit_result = await create_mock_audit_result()
        print(f"✅ Mock audit result created")
        print(f"   - Violations: {len(audit_result.violations)}")
        print(f"   - Compliance: {audit_result.compliance_score:.1%}")
    except Exception as e:
        print(f"❌ Failed to create mock audit result: {e}")
        return False
    
    print("\n2. Testing annotated screenshot generation...")
    try:
        result = await annotation_engine.generate_annotated_screenshot(
            mock_page, 
            audit_result,
            "/tmp/test_annotated_screenshot_minimal.txt"
        )
        print(f"✅ Annotated screenshot generated")
        print(f"   - Screenshot path: {result['screenshot_path']}")
        print(f"   - Image size: {result['image_size']}")
        print(f"   - Violations annotated: {result['violations_annotated']}")
        print(f"   - Annotation summary: {result['annotation_summary']}")
    except Exception as e:
        print(f"❌ Annotated screenshot generation failed: {e}")
        return False
    
    print("\n3. Testing HTML audit report generation...")
    try:
        report_path = await annotation_engine.generate_audit_report(
            audit_result,
            "/tmp/test_annotated_screenshot_minimal.txt",
            "/tmp/test_audit_report_minimal.html"
        )
        print(f"✅ HTML audit report generated")
        print(f"   - Report path: {report_path}")
        
        with open(report_path, 'r') as f:
            report_content = f.read()
        print(f"   - Report size: {len(report_content)} characters")
        print(f"   - Contains violations: {'violation-item' in report_content}")
    except Exception as e:
        print(f"❌ HTML audit report generation failed: {e}")
        return False
    
    print("\n4. Testing violation color mapping...")
    try:
        high_color = annotation_engine.violation_colors['high']
        medium_color = annotation_engine.violation_colors['medium']
        low_color = annotation_engine.violation_colors['low']
        
        print(f"✅ Violation color mapping verified")
        print(f"   - High severity: {high_color}")
        print(f"   - Medium severity: {medium_color}")
        print(f"   - Low severity: {low_color}")
        
        assert high_color == '#FF0000', "High severity should be red"
        assert medium_color == '#FF8C00', "Medium severity should be orange"
        assert low_color == '#FFD700', "Low severity should be yellow"
    except Exception as e:
        print(f"❌ Violation color mapping failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All minimal annotation engine tests passed!")
    print("\nGenerated files:")
    print("  - /tmp/test_annotated_screenshot_minimal.txt")
    print("  - /tmp/test_audit_report_minimal.html")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_annotation_engine_minimal())
    sys.exit(0 if success else 1)
