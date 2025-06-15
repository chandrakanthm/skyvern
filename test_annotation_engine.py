#!/usr/bin/env python3

import sys
import os
import asyncio
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock
from PIL import Image, ImageDraw
import io

sys.path.append('/home/ubuntu/skyvern')

from skyvern.forge.sdk.brand_guidelines.config_manager import BrandGuidelinesConfigManager
from skyvern.forge.sdk.audit.compliance_engine import ComplianceEngine
from skyvern.webeye.audit.annotation_engine import AnnotationEngine

class MockPage:
    async def screenshot(self, full_page=False):
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        
        draw.rectangle([50, 50, 200, 100], fill='lightblue', outline='blue')
        draw.rectangle([300, 150, 500, 250], fill='lightgreen', outline='green')
        draw.rectangle([100, 300, 400, 400], fill='lightcoral', outline='red')
        
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        return img_buffer.getvalue()

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
        },
        {
            'element_id': 'content_1',
            'css_selector': '.content',
            'coordinates': (300, 150, 500, 250),
            'visual_properties': {
                'colors': {
                    'color': '#00ff00',
                    'background-color': '#f8f9fa'
                },
                'typography': {
                    'font-family': 'Times New Roman',
                    'font-size': '16px',
                    'font-weight': 'normal'
                },
                'spacing': {
                    'margin': '5px',
                    'padding': '12px'
                }
            }
        },
        {
            'element_id': 'button_1',
            'css_selector': '.btn',
            'coordinates': (100, 300, 400, 400),
            'visual_properties': {
                'colors': {
                    'color': '#ffffff',
                    'background-color': '#purple'
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
    
    compliance_engine = ComplianceEngine(guidelines)
    return await compliance_engine.audit_visual_segments(mock_visual_segments, "https://example.com")

async def test_annotation_engine():
    print("Testing Annotation Engine")
    print("=" * 40)
    
    annotation_engine = AnnotationEngine()
    mock_page = MockPage()
    
    print("\n1. Creating mock audit result...")
    try:
        audit_result = await create_mock_audit_result()
        print(f"✅ Mock audit result created")
        print(f"   - Violations: {len(audit_result.violations)}")
        print(f"   - Compliance: {audit_result.compliance_score:.1%}")
        
        violations_with_coords = [v for v in audit_result.violations if v.coordinates]
        print(f"   - Violations with coordinates: {len(violations_with_coords)}")
    except Exception as e:
        print(f"❌ Failed to create mock audit result: {e}")
        return False
    
    print("\n2. Testing annotated screenshot generation...")
    try:
        result = await annotation_engine.generate_annotated_screenshot(
            mock_page, 
            audit_result,
            output_path="/tmp/test_annotated_screenshot.png"
        )
        print(f"✅ Annotated screenshot generated")
        print(f"   - Screenshot path: {result['screenshot_path']}")
        print(f"   - Screenshot size: {result['image_size']}")
        print(f"   - Violations annotated: {result['violations_annotated']}")
        print(f"   - Annotation summary: {result['annotation_summary']}")
    except Exception as e:
        print(f"❌ Annotated screenshot generation failed: {e}")
        return False
    
    print("\n3. Testing annotation summary generation...")
    try:
        summary = annotation_engine._generate_annotation_summary(audit_result.violations)
        print(f"✅ Annotation summary generated")
        print(f"   - Total violations: {summary['total_violations']}")
        print(f"   - By severity: {summary['by_severity']}")
        print(f"   - By type: {summary['by_type']}")
        print(f"   - Annotated elements: {summary['annotated_elements']}")
    except Exception as e:
        print(f"❌ Annotation summary generation failed: {e}")
        return False
    
    print("\n4. Testing HTML audit report generation...")
    try:
        report_path = await annotation_engine.generate_audit_report(
            audit_result,
            "/tmp/test_annotated_screenshot.png",
            "/tmp/test_audit_report.html"
        )
        print(f"✅ HTML audit report generated")
        print(f"   - Report path: {report_path}")
        
        with open(report_path, 'r') as f:
            report_content = f.read()
        print(f"   - Report size: {len(report_content)} characters")
        print(f"   - Contains violations: {'violation-item' in report_content}")
        print(f"   - Contains screenshot: {'img src=' in report_content}")
    except Exception as e:
        print(f"❌ HTML audit report generation failed: {e}")
        return False
    
    print("\n5. Testing violation marker drawing...")
    try:
        test_image = Image.new('RGB', (400, 300), color='white')
        draw = ImageDraw.Draw(test_image)
        
        test_coordinates = (50, 50, 150, 100)
        annotation_engine._draw_violation_marker(draw, test_coordinates, '#FF0000', 'high')
        
        test_image.save("/tmp/test_violation_marker.png")
        print(f"✅ Violation marker drawing test completed")
        print(f"   - Test marker image saved to /tmp/test_violation_marker.png")
    except Exception as e:
        print(f"❌ Violation marker drawing failed: {e}")
        return False
    
    print("\n6. Testing annotation positioning...")
    try:
        from PIL import ImageFont
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 12)
        except (OSError, IOError):
            font = ImageFont.load_default()
        
        position = annotation_engine._find_annotation_position(
            (100, 100, 200, 150),
            "TEST ANNOTATION",
            font,
            (800, 600),
            {}
        )
        print(f"✅ Annotation positioning test completed")
        print(f"   - Calculated position: {position}")
    except Exception as e:
        print(f"❌ Annotation positioning failed: {e}")
        return False
    
    print("\n7. Testing violation color mapping...")
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
    
    print("\n" + "=" * 40)
    print("✅ All annotation engine tests passed!")
    print("\nGenerated files:")
    print("  - /tmp/test_annotated_screenshot.png")
    print("  - /tmp/test_audit_report.html")
    print("  - /tmp/test_violation_marker.png")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_annotation_engine())
    sys.exit(0 if success else 1)
