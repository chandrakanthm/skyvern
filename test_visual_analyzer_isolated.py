#!/usr/bin/env python3

import sys
import os
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from unittest.mock import Mock, AsyncMock

class MockScrapedPage:
    def __init__(self):
        self.elements = [
            {
                'id': 'element_1',
                'tagName': 'div',
                'interactable': True,
                'attributes': {'class': 'header'}
            },
            {
                'id': 'element_2', 
                'tagName': 'p',
                'interactable': True,
                'attributes': {'class': 'content'}
            }
        ]
        self.id_to_css_dict = {
            'element_1': '.header',
            'element_2': '.content'
        }

class MockPage:
    async def evaluate(self, script):
        if '.header' in script:
            return {
                'color': '#333333',
                'background-color': '#ffffff',
                'font-family': 'Arial, sans-serif',
                'font-size': '24px',
                'font-weight': 'bold',
                'margin': '20px',
                'padding': '10px',
                '_width': '800px',
                '_height': '60px',
                '_x': '0px',
                '_y': '0px',
                '_text_content': 'Header Text'
            }
        elif '.content' in script:
            return {
                'color': '#666666',
                'background-color': '#f9f9f9',
                'font-family': 'Georgia, serif',
                'font-size': '16px',
                'font-weight': 'normal',
                'margin': '10px',
                'padding': '15px',
                '_width': '600px',
                '_height': '100px',
                '_x': '100px',
                '_y': '80px',
                '_text_content': 'Content paragraph text'
            }
        return None

class IsolatedVisualAnalyzer:
    def __init__(self):
        self.css_properties_to_extract = [
            'color', 'background-color', 'font-family', 'font-size', 'font-weight',
            'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
            'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
            'border-color', 'border-width', 'border-radius', 'box-shadow',
            'text-align', 'line-height', 'letter-spacing'
        ]
    
    async def analyze_page_styles(self, scraped_page, page) -> Dict[str, Dict[str, Any]]:
        element_styles = {}
        
        for element in scraped_page.elements:
            if not element.get('interactable', False):
                continue
                
            element_id = element['id']
            css_selector = scraped_page.id_to_css_dict.get(element_id)
            
            if not css_selector:
                continue
            
            try:
                styles = await self._extract_element_styles(page, css_selector)
                if styles:
                    element_styles[element_id] = {
                        'element': element,
                        'styles': styles,
                        'css_selector': css_selector
                    }
            except Exception as e:
                print(f"Failed to extract styles for element {element_id}: {e}")
                continue
        
        return element_styles
    
    async def _extract_element_styles(self, page, css_selector: str) -> Optional[Dict[str, str]]:
        try:
            result = await page.evaluate(f"mock_script_for_{css_selector}")
            return result
        except Exception as e:
            print(f"Failed to execute style extraction script for {css_selector}: {e}")
            return None
    
    def _extract_coordinates(self, styles: Dict[str, str]) -> Optional[Tuple[int, int, int, int]]:
        try:
            x = int(float(styles.get('_x', '0').replace('px', '')))
            y = int(float(styles.get('_y', '0').replace('px', '')))
            width = int(float(styles.get('_width', '0').replace('px', '')))
            height = int(float(styles.get('_height', '0').replace('px', '')))
            
            return (x, y, x + width, y + height)
        except (ValueError, TypeError):
            return None
    
    def _categorize_visual_properties(self, styles: Dict[str, str]) -> Dict[str, Dict[str, str]]:
        categories = {
            'colors': {},
            'typography': {},
            'spacing': {},
            'layout': {}
        }
        
        color_props = ['color', 'background-color', 'border-color']
        for prop in color_props:
            if prop in styles:
                categories['colors'][prop] = styles[prop]
        
        typography_props = ['font-family', 'font-size', 'font-weight', 'line-height', 'letter-spacing', 'text-align']
        for prop in typography_props:
            if prop in styles:
                categories['typography'][prop] = styles[prop]
        
        spacing_props = ['margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
                        'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left']
        for prop in spacing_props:
            if prop in styles:
                categories['spacing'][prop] = styles[prop]
        
        layout_props = ['border-width', 'border-radius', 'box-shadow', '_width', '_height']
        for prop in layout_props:
            if prop in styles:
                categories['layout'][prop] = styles[prop]
        
        return categories
    
    async def map_visual_segments_to_dom(self, scraped_page, page) -> List[Dict[str, Any]]:
        visual_segments = []
        
        element_styles = await self.analyze_page_styles(scraped_page, page)
        
        for element_id, element_data in element_styles.items():
            element = element_data['element']
            styles = element_data['styles']
            
            segment = {
                'element_id': element_id,
                'tag_name': element.get('tagName', '') if isinstance(element, dict) else '',
                'css_selector': element_data['css_selector'],
                'styles': styles,
                'attributes': element.get('attributes', {}) if isinstance(element, dict) else {},
                'text_content': styles.get('_text_content', ''),
                'coordinates': self._extract_coordinates(styles),
                'visual_properties': self._categorize_visual_properties(styles)
            }
            
            visual_segments.append(segment)
        
        return visual_segments

async def test_isolated_visual_analyzer():
    print("Testing Isolated Visual Analyzer")
    print("=" * 40)
    
    analyzer = IsolatedVisualAnalyzer()
    mock_page = MockPage()
    mock_scraped_page = MockScrapedPage()
    
    print("\n1. Testing style analysis...")
    element_styles = await analyzer.analyze_page_styles(mock_scraped_page, mock_page)
    
    if len(element_styles) == 2:
        print(f"✅ Successfully analyzed {len(element_styles)} elements")
        for element_id, data in element_styles.items():
            print(f"   - {element_id}: {len(data['styles'])} CSS properties")
    else:
        print(f"❌ Expected 2 elements, got {len(element_styles)}")
        return False
    
    print("\n2. Testing coordinate extraction...")
    test_styles = {'_x': '100px', '_y': '200px', '_width': '300px', '_height': '150px'}
    coords = analyzer._extract_coordinates(test_styles)
    expected = (100, 200, 400, 350)
    
    if coords == expected:
        print(f"✅ Coordinates extracted correctly: {coords}")
    else:
        print(f"❌ Coordinate extraction failed. Expected {expected}, got {coords}")
        return False
    
    print("\n3. Testing visual property categorization...")
    test_styles = {
        'color': '#333333',
        'background-color': '#ffffff',
        'font-family': 'Arial, sans-serif',
        'font-size': '16px',
        'margin': '10px',
        'padding': '5px'
    }
    
    categories = analyzer._categorize_visual_properties(test_styles)
    
    if ('color' in categories['colors'] and 
        'font-family' in categories['typography'] and 
        'margin' in categories['spacing']):
        print("✅ Visual properties correctly categorized")
    else:
        print("❌ Visual property categorization failed")
        return False
    
    print("\n4. Testing DOM mapping...")
    visual_segments = await analyzer.map_visual_segments_to_dom(mock_scraped_page, mock_page)
    
    if len(visual_segments) == 2:
        print(f"✅ Successfully mapped {len(visual_segments)} visual segments to DOM")
        for segment in visual_segments:
            print(f"   - {segment['element_id']}: {segment['tag_name']} with {len(segment['visual_properties']['colors'])} colors")
    else:
        print(f"❌ Expected 2 visual segments, got {len(visual_segments)}")
        return False
    
    print("\n" + "=" * 40)
    print("✅ All isolated visual analyzer tests passed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_isolated_visual_analyzer())
    sys.exit(0 if success else 1)
