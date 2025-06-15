from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Any
import structlog
from playwright.async_api import Page

from skyvern.webeye.scraper.scraper import ScrapedPage, scrape_web_unsafe
from skyvern.webeye.audit.visual_analyzer import VisualAnalyzer
from skyvern.forge.sdk.brand_guidelines.config_manager import BrandGuidelinesConfigManager
from skyvern.forge.sdk.brand_guidelines.models import BrandGuidelines, AuditResult
from skyvern.forge.sdk.audit.compliance_engine import ComplianceEngine

LOG = structlog.get_logger()


class AuditOrchestrator:
    def __init__(self, guidelines_config_path: Optional[str] = None):
        self.visual_analyzer = VisualAnalyzer()
        self.config_manager = BrandGuidelinesConfigManager()
        self.guidelines = None
        self.compliance_engine = None
        
        if guidelines_config_path:
            self.load_guidelines(guidelines_config_path)
    
    def load_guidelines(self, config_path: str) -> None:
        try:
            self.guidelines = self.config_manager.load_from_file(config_path)
            self.compliance_engine = ComplianceEngine(self.guidelines)
            LOG.info("Brand guidelines loaded successfully", 
                    name=self.guidelines.name, 
                    version=self.guidelines.version)
        except Exception as e:
            LOG.error("Failed to load brand guidelines", config_path=config_path, error=str(e))
            raise
    
    async def audit_page(self, page: Page, url: str, 
                        guidelines_config_path: Optional[str] = None) -> AuditResult:
        if guidelines_config_path:
            self.load_guidelines(guidelines_config_path)
        
        if not self.guidelines or not self.compliance_engine:
            raise ValueError("Brand guidelines must be loaded before running audit")
        
        LOG.info("Starting page audit", url=url)
        
        try:
            scraped_page = await scrape_web_unsafe(page, url)
            LOG.info("Page scraped successfully", 
                    elements_found=len(scraped_page.elements))
            
            visual_segments = await self.visual_analyzer.map_visual_segments_to_dom(
                scraped_page, page
            )
            LOG.info("Visual segments mapped to DOM", 
                    segments_count=len(visual_segments))
            
            audit_result = await self.compliance_engine.audit_visual_segments(
                visual_segments, url
            )
            LOG.info("Audit completed", 
                    violations_found=len(audit_result.violations),
                    compliance_score=audit_result.compliance_score)
            
            return audit_result
            
        except Exception as e:
            LOG.error("Audit failed", url=url, error=str(e))
            raise
    
    async def audit_page_with_screenshot(self, page: Page, url: str,
                                       guidelines_config_path: Optional[str] = None,
                                       screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        audit_result = await self.audit_page(page, url, guidelines_config_path)
        
        screenshot_data = None
        if screenshot_path:
            try:
                screenshot_data = await page.screenshot(path=screenshot_path, full_page=True)
                LOG.info("Screenshot captured", path=screenshot_path)
            except Exception as e:
                LOG.warning("Failed to capture screenshot", error=str(e))
        
        return {
            'audit_result': audit_result,
            'screenshot_path': screenshot_path,
            'screenshot_data': screenshot_data,
            'summary_report': self.compliance_engine.generate_summary_report(audit_result)
        }
    
    async def audit_multiple_pages(self, page_urls: List[str], page: Page,
                                 guidelines_config_path: Optional[str] = None) -> List[AuditResult]:
        if guidelines_config_path:
            self.load_guidelines(guidelines_config_path)
        
        if not self.guidelines or not self.compliance_engine:
            raise ValueError("Brand guidelines must be loaded before running audit")
        
        results = []
        
        for url in page_urls:
            try:
                LOG.info("Auditing page", url=url)
                await page.goto(url)
                await page.wait_for_load_state('networkidle')
                
                audit_result = await self.audit_page(page, url)
                results.append(audit_result)
                
            except Exception as e:
                LOG.error("Failed to audit page", url=url, error=str(e))
                continue
        
        return results
    
    def generate_consolidated_report(self, audit_results: List[AuditResult]) -> str:
        if not audit_results:
            return "No audit results to report."
        
        total_elements = sum(result.total_elements_checked for result in audit_results)
        total_violations = sum(len(result.violations) for result in audit_results)
        avg_compliance = sum(result.compliance_score for result in audit_results) / len(audit_results)
        
        report = f"""
Consolidated Brand Compliance Report
===================================

Pages Audited: {len(audit_results)}
Total Elements Checked: {total_elements}
Total Violations Found: {total_violations}
Average Compliance Score: {avg_compliance:.1%}

Individual Page Results:
"""
        
        for i, result in enumerate(audit_results, 1):
            report += f"""
{i}. {result.url}
   - Elements: {result.total_elements_checked}
   - Violations: {len(result.violations)}
   - Compliance: {result.compliance_score:.1%}
"""
        
        violation_types = {}
        for result in audit_results:
            for violation in result.violations:
                if violation.violation_type not in violation_types:
                    violation_types[violation.violation_type] = 0
                violation_types[violation.violation_type] += 1
        
        if violation_types:
            report += "\nViolation Summary Across All Pages:\n"
            for vtype, count in sorted(violation_types.items()):
                report += f"  - {vtype.title()}: {count}\n"
        
        report += "\nRecommendations:\n"
        if avg_compliance >= 0.9:
            report += "  - Excellent overall compliance across all pages!\n"
        elif avg_compliance >= 0.7:
            report += "  - Good compliance overall. Focus on consistency across pages.\n"
        elif avg_compliance >= 0.5:
            report += "  - Moderate compliance. Consider standardizing brand implementation.\n"
        else:
            report += "  - Low compliance detected. Comprehensive brand review needed.\n"
        
        return report
    
    async def detect_brand_inconsistencies(self, audit_results: List[AuditResult]) -> List[str]:
        inconsistencies = []
        
        if len(audit_results) < 2:
            return inconsistencies
        
        page_colors = {}
        page_fonts = {}
        
        for result in audit_results:
            url = result.url
            colors = set()
            fonts = set()
            
            for violation in result.violations:
                if violation.violation_type == 'color' and violation.actual_value:
                    colors.add(violation.actual_value)
                elif violation.violation_type == 'typography' and violation.actual_value:
                    fonts.add(violation.actual_value)
            
            page_colors[url] = colors
            page_fonts[url] = fonts
        
        all_colors = set()
        all_fonts = set()
        for colors in page_colors.values():
            all_colors.update(colors)
        for fonts in page_fonts.values():
            all_fonts.update(fonts)
        
        if len(all_colors) > 10:
            inconsistencies.append(f"High color variation across pages ({len(all_colors)} unique colors)")
        
        if len(all_fonts) > 5:
            inconsistencies.append(f"High font variation across pages ({len(all_fonts)} unique fonts)")
        
        return inconsistencies
