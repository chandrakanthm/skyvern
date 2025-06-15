import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime

import structlog
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
from playwright.async_api import async_playwright

from skyvern.forge.sdk.core.security import generate_skyvern_signature
from skyvern.forge.sdk.core.permissions.permission_checker_factory import PermissionCheckerFactory
from skyvern.forge.sdk.models import Organization
from skyvern.forge.sdk.services import org_auth_service
from skyvern.webeye.audit.audit_orchestrator import AuditOrchestrator
from skyvern.forge.sdk.audit.audit_summarizer import AuditSummarizer
from skyvern.webeye.audit.annotation_engine import AnnotationEngine
from skyvern.forge.sdk.brand_guidelines.config_manager import BrandGuidelinesConfigManager

LOG = structlog.get_logger()

audit_router = APIRouter()


class AuditRequest(BaseModel):
    url: str = Field(..., description="URL to audit for brand compliance")
    guidelines_config: Optional[Dict[str, Any]] = Field(None, description="Brand guidelines configuration")
    guidelines_file_path: Optional[str] = Field(None, description="Path to brand guidelines file")
    include_screenshot: bool = Field(True, description="Whether to include annotated screenshot")
    generate_report: bool = Field(True, description="Whether to generate HTML report")


class MultiPageAuditRequest(BaseModel):
    urls: List[str] = Field(..., description="List of URLs to audit")
    guidelines_config: Optional[Dict[str, Any]] = Field(None, description="Brand guidelines configuration")
    guidelines_file_path: Optional[str] = Field(None, description="Path to brand guidelines file")
    include_screenshots: bool = Field(True, description="Whether to include annotated screenshots")
    generate_consolidated_report: bool = Field(True, description="Whether to generate consolidated report")


class AuditResponse(BaseModel):
    audit_id: str
    url: str
    compliance_score: float
    total_elements_checked: int
    violations_found: int
    violations: List[Dict[str, Any]]
    timestamp: str
    screenshot_url: Optional[str] = None
    report_url: Optional[str] = None
    summary: Optional[str] = None


class MultiPageAuditResponse(BaseModel):
    audit_id: str
    urls: List[str]
    average_compliance_score: float
    total_elements_checked: int
    total_violations_found: int
    individual_results: List[AuditResponse]
    consolidated_report_url: Optional[str] = None
    executive_summary: Optional[str] = None
    timestamp: str


class AuditQueryRequest(BaseModel):
    audit_id: str
    query: str = Field(..., description="Natural language query about the audit results")


class AuditQueryResponse(BaseModel):
    audit_id: str
    query: str
    response: str
    timestamp: str


@audit_router.post("/audit/single", response_model=AuditResponse)
async def audit_single_page(
    request: AuditRequest,
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> AuditResponse:
    """
    Audit a single webpage for brand compliance.
    """
    LOG.info("Starting single page audit", url=request.url, org_id=current_org.organization_id)
    
    try:
        audit_id = str(uuid.uuid4())
        orchestrator = AuditOrchestrator()
        
        if request.guidelines_file_path:
            orchestrator.load_guidelines(request.guidelines_file_path)
        elif request.guidelines_config:
            config_manager = BrandGuidelinesConfigManager()
            guidelines = config_manager.load_from_dict(request.guidelines_config)
            orchestrator.guidelines = guidelines
        else:
            raise HTTPException(
                status_code=400,
                detail="Either guidelines_file_path or guidelines_config must be provided"
            )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                audit_result = await orchestrator.audit_page(page, request.url)
                
                screenshot_url = None
                report_url = None
                
                if request.include_screenshot:
                    annotation_engine = AnnotationEngine()
                    screenshot_path = f"/tmp/audit_{audit_id}_screenshot.png"
                    await annotation_engine.generate_annotated_screenshot(
                        page, audit_result, screenshot_path
                    )
                    screenshot_url = f"/api/v1/audit/screenshot/{audit_id}"
                
                if request.generate_report:
                    annotation_engine = AnnotationEngine()
                    report_path = f"/tmp/audit_{audit_id}_report.html"
                    await annotation_engine.generate_audit_report(
                        audit_result, 
                        f"/tmp/audit_{audit_id}_screenshot.png" if request.include_screenshot else None,
                        report_path
                    )
                    report_url = f"/api/v1/audit/report/{audit_id}"
                
                summarizer = AuditSummarizer()
                summary = await summarizer.generate_natural_language_summary(audit_result)
                
                return AuditResponse(
                    audit_id=audit_id,
                    url=audit_result.url,
                    compliance_score=audit_result.compliance_score,
                    total_elements_checked=audit_result.total_elements_checked,
                    violations_found=len(audit_result.violations),
                    violations=[
                        {
                            "element_id": v.element_id,
                            "violation_type": v.violation_type,
                            "severity": v.severity,
                            "description": v.description,
                            "expected_value": v.expected_value,
                            "actual_value": v.actual_value,
                            "css_selector": v.css_selector,
                            "coordinates": v.coordinates
                        }
                        for v in audit_result.violations
                    ],
                    timestamp=audit_result.timestamp,
                    screenshot_url=screenshot_url,
                    report_url=report_url,
                    summary=summary
                )
                
            finally:
                await browser.close()
                
    except Exception as e:
        LOG.error("Single page audit failed", error=str(e), url=request.url)
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


@audit_router.post("/audit/multiple", response_model=MultiPageAuditResponse)
async def audit_multiple_pages(
    request: MultiPageAuditRequest,
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> MultiPageAuditResponse:
    """
    Audit multiple webpages for brand compliance.
    """
    LOG.info("Starting multiple page audit", urls=request.urls, org_id=current_org.organization_id)
    
    try:
        audit_id = str(uuid.uuid4())
        orchestrator = AuditOrchestrator()
        
        if request.guidelines_file_path:
            orchestrator.load_guidelines(request.guidelines_file_path)
        elif request.guidelines_config:
            config_manager = BrandGuidelinesConfigManager()
            guidelines = config_manager.load_from_dict(request.guidelines_config)
            orchestrator.guidelines = guidelines
        else:
            raise HTTPException(
                status_code=400,
                detail="Either guidelines_file_path or guidelines_config must be provided"
            )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                audit_results = await orchestrator.audit_multiple_pages(request.urls, page)
                
                individual_responses = []
                total_elements = 0
                total_violations = 0
                
                for i, result in enumerate(audit_results):
                    individual_audit_id = f"{audit_id}_{i}"
                    
                    screenshot_url = None
                    if request.include_screenshots:
                        annotation_engine = AnnotationEngine()
                        screenshot_path = f"/tmp/audit_{individual_audit_id}_screenshot.png"
                        await page.goto(result.url)
                        await annotation_engine.generate_annotated_screenshot(
                            page, result, screenshot_path
                        )
                        screenshot_url = f"/api/v1/audit/screenshot/{individual_audit_id}"
                    
                    individual_responses.append(AuditResponse(
                        audit_id=individual_audit_id,
                        url=result.url,
                        compliance_score=result.compliance_score,
                        total_elements_checked=result.total_elements_checked,
                        violations_found=len(result.violations),
                        violations=[
                            {
                                "element_id": v.element_id,
                                "violation_type": v.violation_type,
                                "severity": v.severity,
                                "description": v.description,
                                "expected_value": v.expected_value,
                                "actual_value": v.actual_value,
                                "css_selector": v.css_selector,
                                "coordinates": v.coordinates
                            }
                            for v in result.violations
                        ],
                        timestamp=result.timestamp,
                        screenshot_url=screenshot_url
                    ))
                    
                    total_elements += result.total_elements_checked
                    total_violations += len(result.violations)
                
                avg_compliance = sum(r.compliance_score for r in audit_results) / len(audit_results)
                
                consolidated_report_url = None
                if request.generate_consolidated_report:
                    consolidated_report = orchestrator.generate_consolidated_report(audit_results)
                    report_path = f"/tmp/audit_{audit_id}_consolidated_report.html"
                    with open(report_path, 'w') as f:
                        f.write(f"""
<!DOCTYPE html>
<html>
<head><title>Consolidated Brand Audit Report</title></head>
<body>
<h1>Consolidated Brand Compliance Report</h1>
<pre>{consolidated_report}</pre>
</body>
</html>
""")
                    consolidated_report_url = f"/api/v1/audit/report/{audit_id}_consolidated"
                
                summarizer = AuditSummarizer()
                executive_summary = await summarizer.generate_executive_summary(audit_results)
                
                return MultiPageAuditResponse(
                    audit_id=audit_id,
                    urls=request.urls,
                    average_compliance_score=avg_compliance,
                    total_elements_checked=total_elements,
                    total_violations_found=total_violations,
                    individual_results=individual_responses,
                    consolidated_report_url=consolidated_report_url,
                    executive_summary=executive_summary,
                    timestamp=datetime.now().isoformat()
                )
                
            finally:
                await browser.close()
                
    except Exception as e:
        LOG.error("Multiple page audit failed", error=str(e), urls=request.urls)
        raise HTTPException(status_code=500, detail=f"Multi-page audit failed: {str(e)}")


@audit_router.post("/audit/query", response_model=AuditQueryResponse)
async def query_audit_results(
    request: AuditQueryRequest,
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> AuditQueryResponse:
    """
    Query audit results using natural language.
    """
    LOG.info("Processing audit query", audit_id=request.audit_id, query=request.query)
    
    try:
        return AuditQueryResponse(
            audit_id=request.audit_id,
            query=request.query,
            response="This feature requires stored audit results. Please implement audit result storage first.",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        LOG.error("Audit query failed", error=str(e), audit_id=request.audit_id)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@audit_router.get("/audit/screenshot/{audit_id}")
async def get_audit_screenshot(
    audit_id: str,
    current_org: Organization = Depends(org_auth_service.get_current_org),
):
    """
    Retrieve annotated screenshot for an audit.
    """
    try:
        screenshot_path = f"/tmp/audit_{audit_id}_screenshot.png"
        return FileResponse(
            screenshot_path,
            media_type="image/png",
            filename=f"audit_{audit_id}_screenshot.png"
        )
    except Exception as e:
        LOG.error("Failed to retrieve screenshot", error=str(e), audit_id=audit_id)
        raise HTTPException(status_code=404, detail="Screenshot not found")


@audit_router.get("/audit/report/{audit_id}")
async def get_audit_report(
    audit_id: str,
    current_org: Organization = Depends(org_auth_service.get_current_org),
):
    """
    Retrieve HTML audit report.
    """
    try:
        if "_consolidated" in audit_id:
            report_path = f"/tmp/audit_{audit_id}_report.html"
        else:
            report_path = f"/tmp/audit_{audit_id}_report.html"
        
        return FileResponse(
            report_path,
            media_type="text/html",
            filename=f"audit_{audit_id}_report.html"
        )
    except Exception as e:
        LOG.error("Failed to retrieve report", error=str(e), audit_id=audit_id)
        raise HTTPException(status_code=404, detail="Report not found")


@audit_router.post("/audit/guidelines/upload")
async def upload_brand_guidelines(
    file: UploadFile = File(...),
    current_org: Organization = Depends(org_auth_service.get_current_org),
) -> Dict[str, str]:
    """
    Upload brand guidelines configuration file.
    """
    try:
        if not file.filename.endswith(('.json', '.yaml', '.yml')):
            raise HTTPException(
                status_code=400,
                detail="Only JSON and YAML files are supported"
            )
        
        guidelines_id = str(uuid.uuid4())
        file_path = f"/tmp/guidelines_{guidelines_id}_{file.filename}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        config_manager = BrandGuidelinesConfigManager()
        guidelines = config_manager.load_from_file(file_path)
        
        LOG.info("Brand guidelines uploaded", 
                guidelines_id=guidelines_id, 
                name=guidelines.name,
                org_id=current_org.organization_id)
        
        return {
            "guidelines_id": guidelines_id,
            "file_path": file_path,
            "name": guidelines.name,
            "version": guidelines.version,
            "message": "Brand guidelines uploaded successfully"
        }
        
    except Exception as e:
        LOG.error("Failed to upload brand guidelines", error=str(e))
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@audit_router.get("/audit/health")
async def audit_health_check() -> Dict[str, str]:
    """
    Health check endpoint for audit service.
    """
    return {
        "status": "healthy",
        "service": "brand_compliance_audit",
        "timestamp": datetime.now().isoformat()
    }
