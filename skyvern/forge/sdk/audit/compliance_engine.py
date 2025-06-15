from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Any
import structlog
from datetime import datetime

from skyvern.forge.sdk.brand_guidelines.models import (
    BrandGuidelines, 
    AuditViolation, 
    AuditResult
)

LOG = structlog.get_logger()


class ComplianceEngine:
    def __init__(self, guidelines: BrandGuidelines):
        self.guidelines = guidelines
    
    async def audit_visual_segments(self, visual_segments: List[Dict[str, Any]], url: str) -> AuditResult:
        violations = []
        total_elements = len(visual_segments)
        
        for segment in visual_segments:
            element_violations = await self._audit_element(segment)
            violations.extend(element_violations)
        
        compliance_score = self._calculate_compliance_score(violations, total_elements)
        
        return AuditResult(
            url=url,
            guidelines=self.guidelines,
            violations=violations,
            total_elements_checked=total_elements,
            compliance_score=compliance_score,
            timestamp=datetime.now().isoformat()
        )
    
    async def _audit_element(self, segment: Dict[str, Any]) -> List[AuditViolation]:
        violations = []
        element_id = segment['element_id']
        css_selector = segment.get('css_selector', '')
        coordinates = segment.get('coordinates')
        visual_props = segment.get('visual_properties', {})
        
        color_violations = self._audit_colors(element_id, visual_props.get('colors', {}), css_selector, coordinates)
        violations.extend(color_violations)
        
        typography_violations = self._audit_typography(element_id, visual_props.get('typography', {}), css_selector, coordinates)
        violations.extend(typography_violations)
        
        spacing_violations = self._audit_spacing(element_id, visual_props.get('spacing', {}), css_selector, coordinates)
        violations.extend(spacing_violations)
        
        return violations
    
    def _audit_colors(self, element_id: str, colors: Dict[str, str], css_selector: str, coordinates: Optional[tuple]) -> List[AuditViolation]:
        violations = []
        
        for color_property, color_value in colors.items():
            if not color_value or color_value in ['transparent', 'inherit', 'initial', 'unset']:
                continue
            
            color_violations = self.guidelines.validate_color(color_value)
            
            for violation_msg in color_violations:
                violations.append(AuditViolation(
                    element_id=element_id,
                    violation_type="color",
                    description=f"{color_property}: {violation_msg}",
                    expected_value=self._get_expected_color_values(),
                    actual_value=color_value,
                    severity=self._get_color_violation_severity(color_property),
                    css_selector=css_selector,
                    coordinates=coordinates
                ))
        
        return violations
    
    def _audit_typography(self, element_id: str, typography: Dict[str, str], css_selector: str, coordinates: Optional[tuple]) -> List[AuditViolation]:
        violations = []
        
        font_family = typography.get('font-family')
        font_size = typography.get('font-size')
        font_weight = typography.get('font-weight')
        
        if font_family:
            font_violations = self.guidelines.validate_font(font_family, font_size, font_weight)
            
            for violation_msg in font_violations:
                violations.append(AuditViolation(
                    element_id=element_id,
                    violation_type="typography",
                    description=violation_msg,
                    expected_value=self._get_expected_font_values(),
                    actual_value=f"font-family: {font_family}, font-size: {font_size}, font-weight: {font_weight}",
                    severity="medium",
                    css_selector=css_selector,
                    coordinates=coordinates
                ))
        
        return violations
    
    def _audit_spacing(self, element_id: str, spacing: Dict[str, str], css_selector: str, coordinates: Optional[tuple]) -> List[AuditViolation]:
        violations = []
        
        for spacing_property, spacing_value in spacing.items():
            if not spacing_value or spacing_value in ['0', 'auto', 'inherit', 'initial', 'unset']:
                continue
            
            spacing_violations = self.guidelines.validate_spacing(spacing_property, spacing_value)
            
            for violation_msg in spacing_violations:
                violations.append(AuditViolation(
                    element_id=element_id,
                    violation_type="spacing",
                    description=violation_msg,
                    expected_value=self._get_expected_spacing_values(spacing_property),
                    actual_value=spacing_value,
                    severity="low",
                    css_selector=css_selector,
                    coordinates=coordinates
                ))
        
        return violations
    
    def _calculate_compliance_score(self, violations: List[AuditViolation], total_elements: int) -> float:
        if total_elements == 0:
            return 1.0
        
        severity_weights = {
            'high': 1.0,
            'medium': 0.6,
            'low': 0.3
        }
        
        total_violation_weight = sum(
            severity_weights.get(violation.severity, 0.5) 
            for violation in violations
        )
        
        max_possible_violations = total_elements * 1.0  # Assuming worst case is 1 high severity violation per element
        compliance_score = max(0.0, 1.0 - (total_violation_weight / max_possible_violations))
        
        return round(compliance_score, 3)
    
    def _get_expected_color_values(self) -> str:
        color_names = [rule.name for rule in self.guidelines.colors]
        return f"Expected colors: {', '.join(color_names)}"
    
    def _get_expected_font_values(self) -> str:
        font_names = [rule.name for rule in self.guidelines.fonts]
        return f"Expected fonts: {', '.join(font_names)}"
    
    def _get_expected_spacing_values(self, property_name: str) -> str:
        for rule in self.guidelines.spacing:
            if rule.property == property_name:
                return f"Allowed values: {', '.join(rule.allowed_values)}"
        return "No specific spacing rules defined"
    
    def _get_color_violation_severity(self, color_property: str) -> str:
        if color_property in ['color', 'background-color']:
            return 'high'
        elif color_property in ['border-color']:
            return 'medium'
        else:
            return 'low'
    
    def generate_summary_report(self, audit_result: AuditResult) -> str:
        total_violations = len(audit_result.violations)
        compliance_percentage = audit_result.compliance_score * 100
        
        summary = f"""
Brand Compliance Audit Report
=============================

URL: {audit_result.url}
Audit Date: {audit_result.timestamp}
Brand Guidelines: {audit_result.guidelines.name} (v{audit_result.guidelines.version})

Overall Compliance Score: {compliance_percentage:.1f}%
Total Elements Checked: {audit_result.total_elements_checked}
Total Violations Found: {total_violations}

Violation Breakdown:
"""
        
        violations_by_type = {}
        violations_by_severity = {}
        
        for violation in audit_result.violations:
            if violation.violation_type not in violations_by_type:
                violations_by_type[violation.violation_type] = 0
            violations_by_type[violation.violation_type] += 1
            
            if violation.severity not in violations_by_severity:
                violations_by_severity[violation.severity] = 0
            violations_by_severity[violation.severity] += 1
        
        summary += "\nBy Type:\n"
        for violation_type, count in violations_by_type.items():
            summary += f"  - {violation_type.title()}: {count}\n"
        
        summary += "\nBy Severity:\n"
        for severity, count in violations_by_severity.items():
            summary += f"  - {severity.title()}: {count}\n"
        
        summary += "\nRecommendations:\n"
        if compliance_percentage >= 90:
            summary += "  - Excellent compliance! Minor adjustments may further improve brand consistency.\n"
        elif compliance_percentage >= 70:
            summary += "  - Good compliance overall. Focus on addressing high-severity violations first.\n"
        elif compliance_percentage >= 50:
            summary += "  - Moderate compliance. Consider reviewing brand guidelines implementation.\n"
        else:
            summary += "  - Low compliance detected. Comprehensive brand guidelines review recommended.\n"
        
        return summary
