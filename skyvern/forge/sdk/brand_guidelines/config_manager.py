from __future__ import annotations

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

from .models import BrandGuidelines, ColorRule, FontRule, SpacingRule, ColorFormat

LOG = structlog.get_logger()


class BrandGuidelinesConfigManager:
    def __init__(self):
        self._guidelines_cache: Dict[str, BrandGuidelines] = {}
    
    def load_from_file(self, file_path: str | Path) -> BrandGuidelines:
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Brand guidelines file not found: {file_path}")
        
        cache_key = str(file_path.absolute())
        if cache_key in self._guidelines_cache:
            return self._guidelines_cache[cache_key]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif file_path.suffix.lower() == '.json':
                    data = json.load(f)
                else:
                    raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            guidelines = self._parse_guidelines_data(data)
            self._guidelines_cache[cache_key] = guidelines
            
            LOG.info("Loaded brand guidelines", file_path=str(file_path), name=guidelines.name)
            return guidelines
            
        except Exception as e:
            LOG.error("Failed to load brand guidelines", file_path=str(file_path), error=str(e))
            raise
    
    def load_from_dict(self, data: Dict[str, Any]) -> BrandGuidelines:
        return self._parse_guidelines_data(data)
    
    def _parse_guidelines_data(self, data: Dict[str, Any]) -> BrandGuidelines:
        name = data.get('name', 'Unnamed Guidelines')
        version = data.get('version', '1.0.0')
        
        colors = []
        for color_data in data.get('colors', []):
            color_rule = ColorRule(
                name=color_data['name'],
                value=color_data['value'],
                format=ColorFormat(color_data.get('format', 'hex')),
                tolerance=color_data.get('tolerance', 0.0)
            )
            colors.append(color_rule)
        
        fonts = []
        for font_data in data.get('fonts', []):
            font_rule = FontRule(
                name=font_data['name'],
                family=font_data['family'],
                allowed_sizes=font_data.get('allowed_sizes'),
                allowed_weights=font_data.get('allowed_weights')
            )
            fonts.append(font_rule)
        
        spacing = []
        for spacing_data in data.get('spacing', []):
            spacing_rule = SpacingRule(
                name=spacing_data['name'],
                property=spacing_data['property'],
                allowed_values=spacing_data['allowed_values']
            )
            spacing.append(spacing_rule)
        
        return BrandGuidelines(
            name=name,
            version=version,
            colors=colors,
            fonts=fonts,
            spacing=spacing,
            custom_rules=data.get('custom_rules')
        )
    
    def create_sample_guidelines(self) -> BrandGuidelines:
        return BrandGuidelines(
            name="Sample Brand Guidelines",
            version="1.0.0",
            colors=[
                ColorRule(name="primary", value="#007bff", format=ColorFormat.HEX, tolerance=0.1),
                ColorRule(name="secondary", value="#6c757d", format=ColorFormat.HEX, tolerance=0.1),
                ColorRule(name="success", value="#28a745", format=ColorFormat.HEX, tolerance=0.1),
                ColorRule(name="danger", value="#dc3545", format=ColorFormat.HEX, tolerance=0.1),
                ColorRule(name="warning", value="#ffc107", format=ColorFormat.HEX, tolerance=0.1),
                ColorRule(name="info", value="#17a2b8", format=ColorFormat.HEX, tolerance=0.1),
            ],
            fonts=[
                FontRule(
                    name="primary",
                    family="Arial, sans-serif",
                    allowed_sizes=["12px", "14px", "16px", "18px", "20px", "24px", "32px"],
                    allowed_weights=["normal", "bold", "400", "700"]
                ),
                FontRule(
                    name="heading",
                    family="Georgia, serif",
                    allowed_sizes=["18px", "20px", "24px", "28px", "32px", "36px", "48px"],
                    allowed_weights=["normal", "bold", "400", "700"]
                ),
            ],
            spacing=[
                SpacingRule(
                    name="margin",
                    property="margin",
                    allowed_values=["0", "4px", "8px", "12px", "16px", "20px", "24px", "32px", "48px"]
                ),
                SpacingRule(
                    name="padding",
                    property="padding",
                    allowed_values=["0", "4px", "8px", "12px", "16px", "20px", "24px", "32px", "48px"]
                ),
            ]
        )
    
    def save_guidelines_template(self, file_path: str | Path) -> None:
        file_path = Path(file_path)
        
        template = {
            "name": "Your Brand Guidelines",
            "version": "1.0.0",
            "colors": [
                {
                    "name": "primary",
                    "value": "#007bff",
                    "format": "hex",
                    "tolerance": 0.1
                },
                {
                    "name": "secondary",
                    "value": "rgb(108, 117, 125)",
                    "format": "rgb",
                    "tolerance": 0.05
                }
            ],
            "fonts": [
                {
                    "name": "primary",
                    "family": "Arial, sans-serif",
                    "allowed_sizes": ["12px", "14px", "16px", "18px", "20px", "24px"],
                    "allowed_weights": ["normal", "bold", "400", "700"]
                }
            ],
            "spacing": [
                {
                    "name": "margin",
                    "property": "margin",
                    "allowed_values": ["0", "8px", "16px", "24px", "32px"]
                }
            ],
            "custom_rules": {
                "border_radius": ["0", "4px", "8px", "50%"],
                "box_shadow": ["none", "0 2px 4px rgba(0,0,0,0.1)"]
            }
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(template, f, default_flow_style=False, indent=2)
                else:
                    json.dump(template, f, indent=2)
            
            LOG.info("Saved brand guidelines template", file_path=str(file_path))
            
        except Exception as e:
            LOG.error("Failed to save brand guidelines template", file_path=str(file_path), error=str(e))
            raise
    
    def clear_cache(self) -> None:
        self._guidelines_cache.clear()
        LOG.info("Cleared brand guidelines cache")
