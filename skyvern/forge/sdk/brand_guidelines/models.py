from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum
import re


class ColorFormat(Enum):
    HEX = "hex"
    RGB = "rgb"
    RGBA = "rgba"
    HSL = "hsl"


@dataclass
class ColorRule:
    name: str
    value: str
    format: ColorFormat
    tolerance: float = 0.0
    
    def matches_color(self, color_value: str) -> bool:
        normalized_brand = self._normalize_color(self.value)
        normalized_test = self._normalize_color(color_value)
        
        if not normalized_brand or not normalized_test:
            return False
            
        return self._colors_match(normalized_brand, normalized_test)
    
    def _normalize_color(self, color: str) -> Optional[tuple[int, int, int]]:
        color = color.strip().lower()
        
        if color.startswith('#'):
            return self._hex_to_rgb(color)
        elif color.startswith('rgb'):
            return self._parse_rgb(color)
        elif color.startswith('hsl'):
            return self._hsl_to_rgb(color)
        
        return None
    
    def _hex_to_rgb(self, hex_color: str) -> Optional[tuple[int, int, int]]:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        
        try:
            rgb_values = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return (rgb_values[0], rgb_values[1], rgb_values[2])
        except ValueError:
            return None
    
    def _parse_rgb(self, rgb_color: str) -> Optional[tuple[int, int, int]]:
        match = re.search(r'rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', rgb_color)
        if match:
            rgb_values = tuple(int(x) for x in match.groups())
            return (rgb_values[0], rgb_values[1], rgb_values[2])
        return None
    
    def _hsl_to_rgb(self, hsl_color: str) -> Optional[tuple[int, int, int]]:
        match = re.search(r'hsl\s*\(\s*(\d+)\s*,\s*(\d+)%\s*,\s*(\d+)%\s*\)', hsl_color)
        if not match:
            return None
            
        h, s, l = int(match.group(1)), int(match.group(2)) / 100, int(match.group(3)) / 100
        
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = l - c / 2
        
        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
            
        return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))
    
    def _colors_match(self, color1: tuple[int, int, int], color2: tuple[int, int, int]) -> bool:
        if self.tolerance == 0:
            return color1 == color2
            
        distance = sum((a - b) ** 2 for a, b in zip(color1, color2)) ** 0.5
        max_distance = self.tolerance * (255 * 3) ** 0.5
        return distance <= max_distance


@dataclass
class FontRule:
    name: str
    family: str
    allowed_sizes: Optional[List[str]] = None
    allowed_weights: Optional[List[str]] = None
    
    def matches_font(self, font_family: str, font_size: Optional[str] = None, font_weight: Optional[str] = None) -> bool:
        if not self._font_family_matches(font_family):
            return False
            
        if self.allowed_sizes and font_size and font_size not in self.allowed_sizes:
            return False
            
        if self.allowed_weights and font_weight and font_weight not in self.allowed_weights:
            return False
            
        return True
    
    def _font_family_matches(self, font_family: str) -> bool:
        normalized_brand = self.family.lower().replace('"', '').replace("'", "")
        normalized_test = font_family.lower().replace('"', '').replace("'", "")
        
        return normalized_brand in normalized_test or normalized_test in normalized_brand


@dataclass
class SpacingRule:
    name: str
    property: str
    allowed_values: List[str]
    
    def matches_spacing(self, value: str) -> bool:
        return value in self.allowed_values


@dataclass
class BrandGuidelines:
    name: str
    version: str
    colors: List[ColorRule]
    fonts: List[FontRule]
    spacing: List[SpacingRule]
    custom_rules: Optional[Dict[str, Any]] = None
    
    def get_color_rule(self, name: str) -> Optional[ColorRule]:
        return next((rule for rule in self.colors if rule.name == name), None)
    
    def get_font_rule(self, name: str) -> Optional[FontRule]:
        return next((rule for rule in self.fonts if rule.name == name), None)
    
    def get_spacing_rule(self, name: str) -> Optional[SpacingRule]:
        return next((rule for rule in self.spacing if rule.name == name), None)
    
    def validate_color(self, color_value: str) -> List[str]:
        violations = []
        matched = False
        
        for rule in self.colors:
            if rule.matches_color(color_value):
                matched = True
                break
                
        if not matched:
            violations.append(f"Color '{color_value}' does not match any brand guidelines")
            
        return violations
    
    def validate_font(self, font_family: str, font_size: Optional[str] = None, font_weight: Optional[str] = None) -> List[str]:
        violations = []
        matched = False
        
        for rule in self.fonts:
            if rule.matches_font(font_family, font_size, font_weight):
                matched = True
                break
                
        if not matched:
            violations.append(f"Font '{font_family}' does not match any brand guidelines")
            
        return violations
    
    def validate_spacing(self, property_name: str, value: str) -> List[str]:
        violations = []
        
        for rule in self.spacing:
            if rule.property == property_name and not rule.matches_spacing(value):
                violations.append(f"Spacing value '{value}' for property '{property_name}' violates brand guidelines")
                
        return violations


@dataclass
class AuditViolation:
    element_id: str
    violation_type: str
    description: str
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    severity: str = "medium"
    css_selector: Optional[str] = None
    coordinates: Optional[tuple[int, int, int, int]] = None


@dataclass
class AuditResult:
    url: str
    guidelines: BrandGuidelines
    violations: List[AuditViolation]
    total_elements_checked: int
    compliance_score: float
    timestamp: str
    
    def get_violations_by_type(self, violation_type: str) -> List[AuditViolation]:
        return [v for v in self.violations if v.violation_type == violation_type]
    
    def get_violations_by_severity(self, severity: str) -> List[AuditViolation]:
        return [v for v in self.violations if v.severity == severity]
