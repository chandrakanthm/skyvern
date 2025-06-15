#!/usr/bin/env python3

import sys
import os
import asyncio
from typing import Dict, List, Any
from datetime import datetime

sys.path.append('/home/ubuntu/skyvern')

from skyvern.forge.sdk.brand_guidelines.config_manager import BrandGuidelinesConfigManager
from skyvern.forge.sdk.audit.compliance_engine import ComplianceEngine

class MockVisualSegment:
    def __init__(self, element_id: str, visual_props: Dict[str, Any]):
        self.element_id = element_id
        self.visual_properties = visual_props
        self.css_selector = f".element-{element_id}"
        self.coordinates = (100, 100, 200, 150)

def create_mock_visual_segments() -> List[Dict[str, Any]]:
    """Create mock visual segments that would come from the visual analyzer"""
    return [
        {
            'element_id': 'header_1',
            'css_selector': '.header',
            'coordinates': (0, 0, 800, 60),
            'visual_properties': {
                'colors': {
                    'color': '#ff0000',  # This should violate brand guidelines
                    'background-color': '#ffffff'
                },
                'typography': {
                    'font-family': 'Comic Sans MS',  # This should violate brand guidelines
                    'font-size': '24px',
                    'font-weight': 'bold'
                },
                'spacing': {
                    'margin': '13px',  # This should violate spacing guidelines
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
                    'color': '#007bff',  # This should be valid
                    'background-color': '#f8f9fa'  # This should be valid
                },
                'typography': {
                    'font-family': 'Arial, Helvetica, sans-serif',  # This should be valid
                    'font-size': '16px',
                    'font-weight': 'normal'
                },
                'spacing': {
                    'margin': '16px',  # This should be valid
                    'padding': '12px'  # This should be valid
                }
            }
        },
        {
            'element_id': 'button_1',
            'css_selector': '.btn-primary',
            'coordinates': (200, 200, 300, 240),
            'visual_properties': {
                'colors': {
                    'color': '#ffffff',
                    'background-color': '#28a745'  # This should be valid (success-green)
                },
                'typography': {
                    'font-family': 'Arial, Helvetica, sans-serif',
                    'font-size': '14px',
                    'font-weight': '600'
                },
                'spacing': {
                    'margin': '8px',
                    'padding': '8px'
                }
            }
        }
    ]

async def test_full_audit_integration():
    print("Testing Full Audit Integration")
    print("=" * 50)
    
    print("\n1. Loading brand guidelines...")
    config_manager = BrandGuidelinesConfigManager()
    try:
        guidelines = config_manager.load_from_file('/home/ubuntu/skyvern/examples/brand_guidelines_sample.json')
        print(f"✅ Loaded guidelines: {guidelines.name} v{guidelines.version}")
        print(f"   - {len(guidelines.colors)} color rules")
        print(f"   - {len(guidelines.fonts)} font rules") 
        print(f"   - {len(guidelines.spacing)} spacing rules")
    except Exception as e:
        print(f"❌ Failed to load guidelines: {e}")
        return False
    
    print("\n2. Initializing compliance engine...")
    try:
        compliance_engine = ComplianceEngine(guidelines)
        print("✅ Compliance engine initialized")
    except Exception as e:
        print(f"❌ Failed to initialize compliance engine: {e}")
        return False
    
    print("\n3. Creating mock visual segments...")
    visual_segments = create_mock_visual_segments()
    print(f"✅ Created {len(visual_segments)} visual segments for testing")
    
    print("\n4. Running compliance audit...")
    try:
        audit_result = await compliance_engine.audit_visual_segments(
            visual_segments, 
            "https://example.com"
        )
        print(f"✅ Audit completed successfully")
        print(f"   - URL: {audit_result.url}")
        print(f"   - Elements checked: {audit_result.total_elements_checked}")
        print(f"   - Violations found: {len(audit_result.violations)}")
        print(f"   - Compliance score: {audit_result.compliance_score:.1%}")
    except Exception as e:
        print(f"❌ Audit failed: {e}")
        return False
    
    print("\n5. Analyzing violations...")
    if len(audit_result.violations) > 0:
        print("   Violations found:")
        violation_types = {}
        for violation in audit_result.violations:
            if violation.violation_type not in violation_types:
                violation_types[violation.violation_type] = 0
            violation_types[violation.violation_type] += 1
            print(f"   - {violation.element_id}: {violation.violation_type} - {violation.description}")
        
        print(f"\n   Violation summary:")
        for vtype, count in violation_types.items():
            print(f"   - {vtype}: {count}")
        
        expected_violations = ['color', 'typography', 'spacing']
        detected_types = set(violation_types.keys())
        
        if all(vtype in detected_types for vtype in expected_violations):
            print("✅ All expected violation types detected")
        else:
            missing = set(expected_violations) - detected_types
            print(f"❌ Missing expected violations: {missing}")
            return False
    else:
        print("❌ No violations detected - this is unexpected given our test data")
        return False
    
    print("\n6. Generating summary report...")
    try:
        summary = compliance_engine.generate_summary_report(audit_result)
        print("✅ Summary report generated")
        print("\n" + "="*30 + " AUDIT REPORT " + "="*30)
        print(summary)
        print("="*73)
    except Exception as e:
        print(f"❌ Failed to generate summary: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ Full audit integration test completed successfully!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_full_audit_integration())
    sys.exit(0 if success else 1)
