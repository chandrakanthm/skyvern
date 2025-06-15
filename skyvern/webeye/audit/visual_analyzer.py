from __future__ import annotations

import asyncio
import json
from typing import Dict, List, Optional, Tuple, Any
import structlog
from playwright.async_api import Page, Frame

from skyvern.webeye.scraper.scraper import ScrapedPage
from skyvern.forge.sdk.brand_guidelines.models import AuditViolation

LOG = structlog.get_logger()


class VisualAnalyzer:
    def __init__(self):
        self.css_properties_to_extract = [
            'color',
            'background-color',
            'font-family',
            'font-size',
            'font-weight',
            'margin',
            'margin-top',
            'margin-right',
            'margin-bottom',
            'margin-left',
            'padding',
            'padding-top',
            'padding-right',
            'padding-bottom',
            'padding-left',
            'border-color',
            'border-width',
            'border-radius',
            'box-shadow',
            'text-align',
            'line-height',
            'letter-spacing',
        ]
    
    async def analyze_page_styles(self, scraped_page: ScrapedPage, page: Page) -> Dict[str, Dict[str, Any]]:
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
                LOG.warning("Failed to extract styles for element", element_id=element_id, error=str(e))
                continue
        
        return element_styles
    
    async def _extract_element_styles(self, page: Page, css_selector: str) -> Optional[Dict[str, str]]:
        js_script = f"""
        () => {{
            const element = document.querySelector('{css_selector}');
            if (!element) return null;
            
            const computedStyle = window.getComputedStyle(element);
            const styles = {{}};
            
            const properties = {json.dumps(self.css_properties_to_extract)};
            
            properties.forEach(prop => {{
                const value = computedStyle.getPropertyValue(prop);
                if (value && value !== 'initial' && value !== 'inherit') {{
                    styles[prop] = value.trim();
                }}
            }});
            
            // Get element dimensions and position
            const rect = element.getBoundingClientRect();
            styles['_width'] = rect.width + 'px';
            styles['_height'] = rect.height + 'px';
            styles['_x'] = rect.x + 'px';
            styles['_y'] = rect.y + 'px';
            
            // Get text content for analysis
            styles['_text_content'] = element.textContent ? element.textContent.trim() : '';
            
            return styles;
        }}
        """
        
        try:
            result = await page.evaluate(js_script)
            return result
        except Exception as e:
            LOG.error("Failed to execute style extraction script", css_selector=css_selector, error=str(e))
            return None
    
    async def map_visual_segments_to_dom(self, scraped_page: ScrapedPage, page: Page) -> List[Dict[str, Any]]:
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
    
    async def detect_visual_anomalies(self, visual_segments: List[Dict[str, Any]]) -> List[AuditViolation]:
        violations = []
        
        font_families = {}
        for segment in visual_segments:
            font_family = segment['visual_properties']['typography'].get('font-family')
            if font_family:
                if font_family not in font_families:
                    font_families[font_family] = []
                font_families[font_family].append(segment)
        
        if len(font_families) > 5:
            violations.append(AuditViolation(
                element_id="page",
                violation_type="typography",
                description=f"Too many different font families detected ({len(font_families)}). Consider consolidating fonts for better brand consistency.",
                severity="medium"
            ))
        
        colors_used = set()
        for segment in visual_segments:
            colors = segment['visual_properties']['colors']
            for color_prop, color_value in colors.items():
                if color_value and color_value not in ['transparent', 'inherit', 'initial']:
                    colors_used.add(color_value)
        
        if len(colors_used) > 15:
            violations.append(AuditViolation(
                element_id="page",
                violation_type="colors",
                description=f"Large number of different colors detected ({len(colors_used)}). Consider using a more consistent color palette.",
                severity="low"
            ))
        
        return violations
