#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/ubuntu/skyvern')

import asyncio
from unittest.mock import Mock, AsyncMock
from skyvern.webeye.audit.visual_analyzer import VisualAnalyzer
from skyvern.webeye.scraper.scraper import ScrapedPage

def test_visual_analyzer_initialization():
    print("Testing Visual Analyzer Initialization")
    print("=" * 40)
    
    analyzer = VisualAnalyzer()
    
    expected_props = [
        'color', 'background-color', 'font-family', 'font-size', 'font-weight',
        'margin', 'padding', 'border-color', 'border-radius', 'box-shadow'
    ]
    
    for prop in expected_props:
        if prop not in analyzer.css_properties_to_extract:
            print(f"❌ Missing CSS property: {prop}")
            return False
    
    print(f"✅ Visual analyzer initialized with {len(analyzer.css_properties_to_extract)} CSS properties")
    return True

def test_coordinate_extraction():
    print("\nTesting Coordinate Extraction")
    print("=" * 30)
    
    analyzer = VisualAnalyzer()
    
    styles = {
        '_x': '100px',
        '_y': '200px', 
        '_width': '300px',
        '_height': '150px'
    }
    
    coords = analyzer._extract_coordinates(styles)
    expected = (100, 200, 400, 350)  # x, y, x+width, y+height
    
    if coords == expected:
        print(f"✅ Coordinate extraction working: {coords}")
    else:
        print(f"❌ Coordinate extraction failed. Expected {expected}, got {coords}")
        return False
    
    invalid_styles = {'_x': 'invalid', '_y': '200px'}
    coords = analyzer._extract_coordinates(invalid_styles)
    
    if coords is None:
        print("✅ Invalid coordinates correctly handled")
    else:
        print(f"❌ Invalid coordinates should return None, got {coords}")
        return False
    
    return True

def test_visual_property_categorization():
    print("\nTesting Visual Property Categorization")
    print("=" * 35)
    
    analyzer = VisualAnalyzer()
    
    styles = {
        'color': '#333333',
        'background-color': '#ffffff',
        'font-family': 'Arial, sans-serif',
        'font-size': '16px',
        'margin': '10px',
        'padding': '5px',
        'border-radius': '4px',
        'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'
    }
    
    categories = analyzer._categorize_visual_properties(styles)
    
    if 'color' in categories['colors'] and 'background-color' in categories['colors']:
        print("✅ Color properties correctly categorized")
    else:
        print("❌ Color properties not correctly categorized")
        return False
    
    if 'font-family' in categories['typography'] and 'font-size' in categories['typography']:
        print("✅ Typography properties correctly categorized")
    else:
        print("❌ Typography properties not correctly categorized")
        return False
    
    if 'margin' in categories['spacing'] and 'padding' in categories['spacing']:
        print("✅ Spacing properties correctly categorized")
    else:
        print("❌ Spacing properties not correctly categorized")
        return False
    
    if 'border-radius' in categories['layout'] and 'box-shadow' in categories['layout']:
        print("✅ Layout properties correctly categorized")
    else:
        print("❌ Layout properties not correctly categorized")
        return False
    
    return True

async def test_visual_anomaly_detection():
    print("\nTesting Visual Anomaly Detection")
    print("=" * 30)
    
    analyzer = VisualAnalyzer()
    
    visual_segments = []
    font_families = [
        'Arial, sans-serif',
        'Georgia, serif', 
        'Times New Roman, serif',
        'Helvetica, sans-serif',
        'Courier New, monospace',
        'Comic Sans MS, cursive',  # This should trigger the anomaly
        'Impact, sans-serif'
    ]
    
    for i, font in enumerate(font_families):
        segment = {
            'element_id': f'element_{i}',
            'visual_properties': {
                'typography': {'font-family': font},
                'colors': {'color': f'#00000{i}'}
            }
        }
        visual_segments.append(segment)
    
    violations = await analyzer.detect_visual_anomalies(visual_segments)
    
    font_violations = [v for v in violations if v.violation_type == 'typography']
    if font_violations:
        print(f"✅ Font anomaly detected: {font_violations[0].description}")
    else:
        print("❌ Font anomaly not detected")
        return False
    
    return True

async def run_all_tests():
    print("Visual Analyzer Test Suite")
    print("=" * 50)
    
    tests = [
        test_visual_analyzer_initialization(),
        test_coordinate_extraction(),
        test_visual_property_categorization(),
        await test_visual_anomaly_detection()
    ]
    
    passed = sum(tests)
    total = len(tests)
    
    print(f"\n" + "=" * 50)
    if passed == total:
        print(f"✅ All {total} visual analyzer tests passed!")
        return True
    else:
        print(f"❌ {passed}/{total} tests passed")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
