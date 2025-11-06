"""
FastAPI Web Interface for Browsint
Provides a modern web interface for all CLI functionalities
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli.scraper_cli import ScraperCLI
from scraper.utils.validators import validate_domain
from scraper.utils.formatters import format_domain_osint_report, format_page_analysis_report

app = FastAPI(title="Browsint Web Interface", version="2.1.0")

# Setup static files and templates
app.mount("/static", StaticFiles(directory="dist/assets"), name="static")

# Global CLI instance
cli_instance: Optional[ScraperCLI] = None
active_tasks: Dict[str, Dict[str, Any]] = {}

def get_cli_instance():
    """Get or create CLI instance"""
    global cli_instance
    if cli_instance is None:
        cli_instance = ScraperCLI()
    return cli_instance

@app.on_event("startup")
async def startup_event():
    """Initialize CLI on startup"""
    get_cli_instance()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve React app"""
    try:
        with open("dist/index.html", "r", encoding="utf-8") as f:  # FIXED PATH
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback if React app not built
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head><title>Browsint - Building...</title></head>
        <body>
            <h1>Browsint Web Interface</h1>
            <p>React app is being built. Please run: npm run build</p>
        </body>
        </html>
        """)

@app.get("/api/status")
async def get_status():
    """Get application status and API keys"""
    cli = get_cli_instance()
    return {
        "status": "running",
        "version": "2.1.0",
        "api_keys_configured": list(cli.api_keys.keys()),
        "databases_initialized": True
    }

# === CRAWLING AND DOWNLOADING ENDPOINTS ===

@app.post("/api/download/single")
async def download_single_page(url: str = Form(...)):
    """Download a single page"""
    cli = get_cli_instance()
    try:
        content = cli.web_fetcher.fetch(url)
        if content:
            return {"success": True, "content_length": len(content), "url": url}
        else:
            return {"success": False, "error": "Failed to download content"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/crawl/basic")
async def start_basic_crawl(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    depth: int = Form(2)
):
    """Start basic crawling (download mode)"""
    task_id = f"crawl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def run_crawl():
        cli = get_cli_instance()
        try:
            active_tasks[task_id] = {"status": "running", "type": "basic_crawl", "url": url}
            
            stats = cli.crawler.start_crawl(
                start_url=url,
                depth_limit=depth,
                perform_osint_on_pages=False,
                save_to_disk=True
            )
            
            active_tasks[task_id] = {
                "status": "completed",
                "type": "basic_crawl",
                "url": url,
                "stats": stats
            }
        except Exception as e:
            active_tasks[task_id] = {
                "status": "error",
                "type": "basic_crawl",
                "url": url,
                "error": str(e)
            }
    
    background_tasks.add_task(run_crawl)
    return {"task_id": task_id, "status": "started"}

@app.post("/api/crawl/osint")
async def start_osint_crawl(
    background_tasks: BackgroundTasks,
    url: str = Form(...),
    depth: int = Form(1)
):
    """Start OSINT crawling"""
    task_id = f"osint_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def run_osint_crawl():
        cli = get_cli_instance()
        try:
            active_tasks[task_id] = {"status": "running", "type": "osint_crawl", "url": url}
            
            stats = cli.crawler.start_crawl(
                start_url=url,
                depth_limit=depth,
                perform_osint_on_pages=True,
                save_to_disk=False
            )
            
            active_tasks[task_id] = {
                "status": "completed",
                "type": "osint_crawl",
                "url": url,
                "stats": stats
            }
        except Exception as e:
            active_tasks[task_id] = {
                "status": "error",
                "type": "osint_crawl",
                "url": url,
                "error": str(e)
            }
    
    background_tasks.add_task(run_osint_crawl)
    return {"task_id": task_id, "status": "started"}

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status"""
    if task_id not in active_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return active_tasks[task_id]

# === OSINT ANALYSIS ENDPOINTS ===

@app.post("/api/osint/domain")
async def analyze_domain(
    background_tasks: BackgroundTasks,
    domain: str = Form(...)
):
    """Analyze domain with OSINT"""
    task_id = f"domain_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def run_domain_analysis():
        cli = get_cli_instance()
        try:
            active_tasks[task_id] = {"status": "running", "type": "domain_analysis", "domain": domain}
            
            profile = cli.osint_extractor.profile_domain(domain)
            
            active_tasks[task_id] = {
                "status": "completed",
                "type": "domain_analysis",
                "domain": domain,
                "profile": profile
            }
        except Exception as e:
            active_tasks[task_id] = {
                "status": "error",
                "type": "domain_analysis",
                "domain": domain,
                "error": str(e)
            }
    
    background_tasks.add_task(run_domain_analysis)
    return {"task_id": task_id, "status": "started"}

@app.post("/api/osint/email")
async def analyze_email(
    background_tasks: BackgroundTasks,
    email: str = Form(...)
):
    """Analyze email with OSINT"""
    task_id = f"email_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def run_email_analysis():
        cli = get_cli_instance()
        try:
            active_tasks[task_id] = {"status": "running", "type": "email_analysis", "email": email}
            
            profile = cli.osint_extractor.profile_email(email)
            
            active_tasks[task_id] = {
                "status": "completed",
                "type": "email_analysis",
                "email": email,
                "profile": profile
            }
        except Exception as e:
            active_tasks[task_id] = {
                "status": "error",
                "type": "email_analysis",
                "email": email,
                "error": str(e)
            }
    
    background_tasks.add_task(run_email_analysis)
    return {"task_id": task_id, "status": "started"}

@app.post("/api/osint/username")
async def analyze_username(
    background_tasks: BackgroundTasks,
    username: str = Form(...)
):
    """Analyze username with OSINT"""
    task_id = f"username_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def run_username_analysis():
        cli = get_cli_instance()
        try:
            active_tasks[task_id] = {"status": "running", "type": "username_analysis", "username": username}
            
            profile = cli.osint_extractor.profile_username(username)
            
            active_tasks[task_id] = {
                "status": "completed",
                "type": "username_analysis",
                "username": username,
                "profile": profile
            }
        except Exception as e:
            active_tasks[task_id] = {
                "status": "error",
                "type": "username_analysis",
                "username": username,
                "error": str(e)
            }
    
    background_tasks.add_task(run_username_analysis)
    return {"task_id": task_id, "status": "started"}

@app.post("/api/analyze/page")
async def analyze_page(url: str = Form(...)):
    """Analyze single page structure"""
    cli = get_cli_instance()
    try:
        response = cli.web_fetcher.fetch_full_response(url)
        if not response or not response.content:
            return {"success": False, "error": "Failed to fetch page"}
        
        content = response.content.decode(response.encoding if response.encoding else 'utf-8', errors='replace')
        parsed_data = cli.web_parser.parse(content, url)
        
        # Extract OSINT data
        osint_data = {}
        if cli.osint_extractor:
            from scraper.utils.extractors import extract_emails, extract_phone_numbers
            from scraper.utils.web_analysis import detect_technologies
            from urllib.parse import urlparse
            
            page_emails = extract_emails(content)
            page_phones = extract_phone_numbers(content)
            osint_data["emails"] = list(page_emails)
            osint_data["phone_numbers"] = list(page_phones)
            
            domain_for_tech = urlparse(url).netloc
            if domain_for_tech:
                tech_data = detect_technologies(domain_for_tech, cli.osint_extractor.logger)
                if tech_data and not tech_data.get("error"):
                    osint_data["page_technologies"] = tech_data
        
        return {
            "success": True,
            "url": url,
            "parsed_data": parsed_data,
            "osint_data": osint_data
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# === DATABASE AND PROFILES ENDPOINTS ===

@app.get("/api/profiles/osint")
async def get_osint_profiles():
    """Get all OSINT profiles"""
    cli = get_cli_instance()
    try:
        profiles = cli.osint_extractor.get_all_osint_profiles_summary()
        return {"success": True, "profiles": profiles}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/profiles/osint/{profile_id}")
async def get_osint_profile(profile_id: int):
    """Get specific OSINT profile"""
    cli = get_cli_instance()
    try:
        profile = cli.osint_extractor.get_osint_profile_by_id(profile_id)
        if profile:
            return {"success": True, "profile": profile}
        else:
            return {"success": False, "error": "Profile not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/database/info")
async def get_database_info():
    """Get database information"""
    cli = get_cli_instance()
    try:
        info = {}
        for db_name in ["websites", "osint"]:
            size = cli.db_manager.get_database_size(db_name)
            tables = cli.db_manager.get_all_table_names(db_name)
            table_info = []
            for table in tables:
                row_count = cli.db_manager.fetch_one(f"SELECT COUNT(*) as count FROM {table}", db_name=db_name)
                count = row_count['count'] if row_count else 0
                table_info.append({"name": table, "rows": count})
            
            info[db_name] = {
                "size_mb": size,
                "tables": table_info
            }
        
        return {"success": True, "databases": info}
    except Exception as e:
        return {"success": False, "error": str(e)}

# === API KEYS MANAGEMENT ===

@app.get("/api/keys")
async def get_api_keys():
    """Get configured API keys (masked)"""
    cli = get_cli_instance()
    masked_keys = {}
    for service, key_value in cli.api_keys.items():
        masked_key = key_value[:4] + "****" + key_value[-4:] if len(key_value) > 8 else "****"
        masked_keys[service] = masked_key
    return {"api_keys": masked_keys}

@app.post("/api/keys")
async def update_api_key(service: str = Form(...), api_key: str = Form(...)):
    """Update API key"""
    cli = get_cli_instance()
    try:
        from dotenv import set_key
        import os
        
        service_mapping = {
            "hunterio": "HUNTER_IO_API_KEY",
            "hibp": "HIBP_API_KEY",
            "shodan": "SHODAN_API_KEY",
            "whoisxml": "WHOISXML_API_KEY",
            "virustotal": "VIRUSTOTAL_API_KEY",
            "securitytrails": "SECURITYTRAILS_API_KEY"
        }
        
        if service not in service_mapping:
            return {"success": False, "error": "Invalid service"}
        
        env_var = service_mapping[service]
        set_key(cli.env_file, env_var, api_key)
        os.environ[env_var] = api_key
        cli.api_keys[service] = api_key
        cli.osint_extractor.api_keys = cli.api_keys
        
        return {"success": True, "message": f"API key for {service} updated"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# === EXPORT ENDPOINTS ===

@app.get("/api/export/profile/{profile_id}/{format}")
async def export_profile(profile_id: int, format: str):
    """Export OSINT profile in specified format"""
    cli = get_cli_instance()
    try:
        profile = cli.osint_extractor.get_osint_profile_by_id(profile_id)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_id = profile.get("entity", {}).get("name", "unknown")
        
        if format == "json":
            filename = f"osint_profile_{target_id}_{timestamp}.json"
            filepath = cli.dirs["osint_exports"] / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=4, ensure_ascii=False, default=str)
            
            return FileResponse(
                path=str(filepath),
                filename=filename,
                media_type='application/json'
            )
        
        elif format == "html":
            from scraper.utils.formatters import formal_html_report_domain
            
            filename = f"osint_profile_{target_id}_{timestamp}.html"
            filepath = cli.dirs["osint_exports"] / filename
            
            profiles = profile.get('profiles', {})
            data = profiles.get('domain', {}).get('raw', {})
            domain_analyzed = profile.get('entity', {}).get('name', target_id)
            target_input = profile.get('target_input', domain_analyzed)
            shodan_skipped = 'shodan' not in data
            
            html_report = formal_html_report_domain(data, target_input, domain_analyzed, shodan_skipped)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_report)
            
            return FileResponse(
                path=str(filepath),
                filename=filename,
                media_type='text/html'
            )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid format")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Catch-all route for React Router
@app.get("/{full_path:path}")
async def catch_all(request: Request, full_path: str):
    """Serve React app for all other routes"""
    try:
        with open("dist/index.html", "r", encoding="utf-8") as f:  # FIXED PATH
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Browsint - Please build the React app first</h1>")

if __name__ == "__main__":
    # Only use reload if running with uvicorn CLI, not directly
    uvicorn.run(app, host="127.0.0.1", port=8000)