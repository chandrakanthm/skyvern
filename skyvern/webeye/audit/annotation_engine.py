from __future__ import annotations

import asyncio
import base64
from typing import Dict, List, Optional, Tuple, Any
from PIL import Image, ImageDraw, ImageFont
import io
import structlog
from playwright.async_api import Page

from skyvern.forge.sdk.brand_guidelines.models import AuditResult, AuditViolation

LOG = structlog.get_logger()


class AnnotationEngine:
    def __init__(self):
        self.violation_colors = {
            'high': '#FF0000',      # Red for high severity
            'medium': '#FF8C00',    # Orange for medium severity
            'low': '#FFD700'        # Yellow for low severity
        }
        self.annotation_font_size = 12
        self.marker_thickness = 3
        self.annotation_padding = 5
    
    async def generate_annotated_screenshot(self, page: Page, audit_result: AuditResult, 
                                          output_path: Optional[str] = None) -> Dict[str, Any]:
        try:
            screenshot_bytes = await page.screenshot(full_page=True)
            
            annotated_image = self._annotate_screenshot(screenshot_bytes, audit_result.violations)
            
            if output_path:
                annotated_image.save(output_path, 'PNG')
                LOG.info("Annotated screenshot saved", path=output_path)
            
            img_buffer = io.BytesIO()
            annotated_image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return {
                'screenshot_path': output_path,
                'screenshot_bytes': img_buffer.getvalue(),
                'violations_annotated': len(audit_result.violations),
                'image_size': annotated_image.size,
                'annotation_summary': self._generate_annotation_summary(audit_result.violations)
            }
            
        except Exception as e:
            LOG.error("Failed to generate annotated screenshot", error=str(e))
            raise
    
    def _annotate_screenshot(self, screenshot_bytes: bytes, violations: List[AuditViolation]) -> Image.Image:
        image = Image.open(io.BytesIO(screenshot_bytes))
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", self.annotation_font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()
        
        violation_positions = {}
        
        for i, violation in enumerate(violations):
            if not violation.coordinates:
                continue
            
            x1, y1, x2, y2 = violation.coordinates
            color = self.violation_colors.get(violation.severity, '#FF0000')
            
            self._draw_violation_marker(draw, (x1, y1, x2, y2), color, violation.severity)
            
            annotation_text = f"{i+1}. {violation.violation_type.upper()}"
            text_position = self._find_annotation_position(
                (x1, y1, x2, y2), annotation_text, font, image.size, violation_positions
            )
            
            if text_position:
                self._draw_annotation_text(draw, text_position, annotation_text, font, color)
                violation_positions[i] = text_position
        
        self._draw_legend(draw, font, image.size, violations)
        
        return image
    
    def _draw_violation_marker(self, draw: ImageDraw.Draw, coordinates: Tuple[int, int, int, int], 
                             color: str, severity: str) -> None:
        x1, y1, x2, y2 = coordinates
        
        thickness = self.marker_thickness
        if severity == 'high':
            thickness = 4
        elif severity == 'medium':
            thickness = 3
        else:
            thickness = 2
        
        for i in range(thickness):
            draw.rectangle([x1-i, y1-i, x2+i, y2+i], outline=color, width=1)
        
        corner_size = 8
        draw.rectangle([x1-corner_size, y1-corner_size, x1, y1], fill=color)
        draw.rectangle([x2, y1-corner_size, x2+corner_size, y1], fill=color)
        draw.rectangle([x1-corner_size, y2, x1, y2+corner_size], fill=color)
        draw.rectangle([x2, y2, x2+corner_size, y2+corner_size], fill=color)
    
    def _find_annotation_position(self, element_coords: Tuple[int, int, int, int], 
                                text: str, font: ImageFont.ImageFont, image_size: Tuple[int, int],
                                existing_positions: Dict[int, Tuple[int, int]]) -> Optional[Tuple[int, int]]:
        x1, y1, x2, y2 = element_coords
        img_width, img_height = image_size
        
        try:
            text_bbox = font.getbbox(text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except AttributeError:
            text_width = len(text) * 8
            text_height = 12
        
        candidate_positions = [
            (x1, y1 - text_height - self.annotation_padding),  # Above
            (x1, y2 + self.annotation_padding),                # Below
            (x2 + self.annotation_padding, y1),               # Right
            (x1 - text_width - self.annotation_padding, y1),  # Left
        ]
        
        for pos_x, pos_y in candidate_positions:
            if (0 <= pos_x <= img_width - text_width and 
                0 <= pos_y <= img_height - text_height):
                
                overlaps = False
                for existing_pos in existing_positions.values():
                    ex_x, ex_y = existing_pos
                    if (abs(pos_x - ex_x) < text_width + 10 and 
                        abs(pos_y - ex_y) < text_height + 5):
                        overlaps = True
                        break
                
                if not overlaps:
                    return (pos_x, pos_y)
        
        return (x1, max(0, y1 - text_height - self.annotation_padding))
    
    def _draw_annotation_text(self, draw: ImageDraw.Draw, position: Tuple[int, int], 
                            text: str, font: ImageFont.ImageFont, color: str) -> None:
        x, y = position
        
        try:
            text_bbox = font.getbbox(text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except AttributeError:
            text_width = len(text) * 8
            text_height = 12
        
        padding = 2
        draw.rectangle([x-padding, y-padding, x+text_width+padding, y+text_height+padding], 
                      fill='white', outline=color, width=1)
        
        draw.text((x, y), text, fill=color, font=font)
    
    def _draw_legend(self, draw: ImageDraw.Draw, font: ImageFont.ImageFont, 
                   image_size: Tuple[int, int], violations: List[AuditViolation]) -> None:
        img_width, img_height = image_size
        
        violation_counts = {'high': 0, 'medium': 0, 'low': 0}
        for violation in violations:
            violation_counts[violation.severity] = violation_counts.get(violation.severity, 0) + 1
        
        legend_items = []
        for severity, count in violation_counts.items():
            if count > 0:
                legend_items.append(f"{severity.upper()}: {count}")
        
        if not legend_items:
            return
        
        legend_text = "VIOLATIONS - " + " | ".join(legend_items)
        
        try:
            text_bbox = font.getbbox(legend_text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except AttributeError:
            text_width = len(legend_text) * 8
            text_height = 12
        
        legend_x = img_width - text_width - 20
        legend_y = 20
        
        padding = 8
        draw.rectangle([legend_x-padding, legend_y-padding, 
                       legend_x+text_width+padding, legend_y+text_height+padding], 
                      fill='white', outline='black', width=2)
        
        draw.text((legend_x, legend_y), legend_text, fill='black', font=font)
    
    def _generate_annotation_summary(self, violations: List[AuditViolation]) -> Dict[str, Any]:
        summary = {
            'total_violations': len(violations),
            'by_severity': {'high': 0, 'medium': 0, 'low': 0},
            'by_type': {},
            'annotated_elements': set()
        }
        
        for violation in violations:
            summary['by_severity'][violation.severity] += 1
            
            if violation.violation_type not in summary['by_type']:
                summary['by_type'][violation.violation_type] = 0
            summary['by_type'][violation.violation_type] += 1
            
            if violation.coordinates:
                summary['annotated_elements'].add(violation.element_id)
        
        summary['annotated_elements'] = len(summary['annotated_elements'])
        
        return summary
    
    async def generate_audit_report(self, audit_result: AuditResult, 
                                  annotated_screenshot_path: str,
                                  report_output_path: str) -> str:
        try:
            report_content = self._build_html_report(audit_result, annotated_screenshot_path)
            
            with open(report_output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            LOG.info("Audit report generated", path=report_output_path)
            return report_output_path
            
        except Exception as e:
            LOG.error("Failed to generate audit report", error=str(e))
            raise
    
    def _build_html_report(self, audit_result: AuditResult, screenshot_path: str) -> str:
        compliance_percentage = audit_result.compliance_score * 100
        
        violations_by_type = {}
        violations_by_severity = {}
        
        for violation in audit_result.violations:
            violations_by_type[violation.violation_type] = violations_by_type.get(violation.violation_type, 0) + 1
            violations_by_severity[violation.severity] = violations_by_severity.get(violation.severity, 0) + 1
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Brand Compliance Audit Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .compliance-score {{ font-size: 2em; font-weight: bold; color: {'#28a745' if compliance_percentage >= 70 else '#dc3545' if compliance_percentage < 50 else '#ffc107'}; }}
        .violation-summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .violation-card {{ background: #f8f9fa; padding: 15px; border-radius: 5px; flex: 1; }}
        .violation-list {{ margin: 20px 0; }}
        .violation-item {{ background: white; padding: 10px; margin: 5px 0; border-left: 4px solid #ccc; }}
        .violation-high {{ border-left-color: #FF0000; }}
        .violation-medium {{ border-left-color: #FF8C00; }}
        .violation-low {{ border-left-color: #FFD700; }}
        .screenshot {{ text-align: center; margin: 20px 0; }}
        .screenshot img {{ max-width: 100%; border: 1px solid #ddd; }}
        .recommendations {{ background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Brand Compliance Audit Report</h1>
        <p><strong>URL:</strong> {audit_result.url}</p>
        <p><strong>Audit Date:</strong> {audit_result.timestamp}</p>
        <p><strong>Brand Guidelines:</strong> {audit_result.guidelines.name} (v{audit_result.guidelines.version})</p>
        <div class="compliance-score">{compliance_percentage:.1f}% Compliant</div>
    </div>
    
    <div class="violation-summary">
        <div class="violation-card">
            <h3>Elements Checked</h3>
            <div style="font-size: 1.5em; font-weight: bold;">{audit_result.total_elements_checked}</div>
        </div>
        <div class="violation-card">
            <h3>Violations Found</h3>
            <div style="font-size: 1.5em; font-weight: bold; color: #dc3545;">{len(audit_result.violations)}</div>
        </div>
        <div class="violation-card">
            <h3>High Priority</h3>
            <div style="font-size: 1.5em; font-weight: bold; color: #FF0000;">{violations_by_severity.get('high', 0)}</div>
        </div>
    </div>
    
    <div class="screenshot">
        <h2>Annotated Screenshot</h2>
        <img src="{screenshot_path}" alt="Annotated Screenshot showing brand violations">
        <p><em>Violations are highlighted with colored markers. Numbers correspond to the violation list below.</em></p>
    </div>
    
    <div class="violation-list">
        <h2>Detailed Violations</h2>
"""
        
        for i, violation in enumerate(audit_result.violations, 1):
            severity_class = f"violation-{violation.severity}"
            html_content += f"""
        <div class="violation-item {severity_class}">
            <h4>#{i} - {violation.violation_type.title()} Violation ({violation.severity.upper()})</h4>
            <p><strong>Element:</strong> {violation.element_id}</p>
            <p><strong>Issue:</strong> {violation.description}</p>
            {f'<p><strong>Expected:</strong> {violation.expected_value}</p>' if violation.expected_value else ''}
            {f'<p><strong>Actual:</strong> {violation.actual_value}</p>' if violation.actual_value else ''}
            {f'<p><strong>CSS Selector:</strong> {violation.css_selector}</p>' if violation.css_selector else ''}
        </div>
"""
        
        recommendations = []
        if violations_by_severity.get('high', 0) > 0:
            recommendations.append("🚨 Address high-priority violations immediately (colors, primary fonts)")
        if violations_by_severity.get('medium', 0) > 0:
            recommendations.append("⚠️ Review medium-priority issues (secondary fonts, borders)")
        if violations_by_severity.get('low', 0) > 0:
            recommendations.append("💡 Fine-tune low-priority spacing and layout issues")
        
        if compliance_percentage >= 90:
            recommendations.append("✅ Excellent compliance! Consider minor refinements for perfect brand consistency.")
        elif compliance_percentage >= 70:
            recommendations.append("👍 Good overall compliance. Focus on consistency across all elements.")
        else:
            recommendations.append("📋 Consider implementing a design system to enforce brand standards.")
        
        html_content += f"""
    </div>
    
    <div class="recommendations">
        <h2>Recommendations</h2>
        <ul>
            {''.join(f'<li>{rec}</li>' for rec in recommendations)}
        </ul>
    </div>
    
    <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;">
        <p>Generated by Skyvern Automated Brand Compliance Audit</p>
    </footer>
</body>
</html>
"""
        
        return html_content
