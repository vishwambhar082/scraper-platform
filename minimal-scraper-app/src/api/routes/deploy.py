"""
API routes for scraper deployment.

Allows frontend to trigger scraper scaffolding via the add_scraper_advanced tool.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.common.logging_utils import get_logger

log = get_logger("deploy-api")

router = APIRouter(prefix="/api/deploy", tags=["deploy"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRAPER_TOOL = PROJECT_ROOT / "tools" / "add_scraper_advanced.py"


class DeployRequest(BaseModel):
    source: str
    engine: str = "selenium"
    requires_login: bool = False


@router.post("/scraper")
def deploy_scraper(request: DeployRequest) -> Dict[str, Any]:
    """
    Deploy a new scraper by running the scaffolding tool.

    This calls the add_scraper_advanced.py tool with the provided parameters.
    """
    source = request.source.strip()

    # Validate source name
    if not source or not source.replace("_", "").isalnum() or not source[0].isalpha():
        raise HTTPException(
            status_code=400,
            detail="Source name must be a valid Python identifier (letters, numbers, underscores, starting with letter)",
        )

    # Validate engine
    valid_engines = {"selenium", "playwright", "http", "scrapy"}
    if request.engine not in valid_engines:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid engine. Must be one of: {', '.join(valid_engines)}",
        )

    try:
        # Build command
        cmd = [
            sys.executable,
            "-m",
            "tools.add_scraper_advanced",
            source,
            "--engine",
            request.engine,
        ]

        if request.requires_login:
            cmd.append("--requires-login")

        log.info(
            "Deploying scraper",
            extra={
                "source": source,
                "engine": request.engine,
                "requires_login": request.requires_login,
            },
        )

        # Run the tool
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            log.error("Scraper deployment failed", extra={"error": error_msg, "source": source})
            raise HTTPException(
                status_code=500,
                detail=f"Deployment failed: {error_msg}",
            )

        # Parse output to extract created files (simplified)
        output = result.stdout
        files_created = []
        if "Created" in output:
            # Extract file paths from output
            for line in output.split("\n"):
                if "[OK] Created" in line:
                    # Extract file path
                    if ":" in line:
                        file_path = line.split(":", 1)[1].strip()
                        files_created.append(file_path)

        log.info("Scraper deployed successfully", extra={"source": source, "files_count": len(files_created)})

        return {
            "success": True,
            "message": f"Scraper '{source}' deployed successfully",
            "files_created": files_created,
            "source": source,
        }

    except subprocess.TimeoutExpired:
        log.error("Deployment timeout", extra={"source": source})
        raise HTTPException(status_code=500, detail="Deployment timed out")
    except Exception as exc:
        log.error("Deployment error", extra={"error": str(exc), "source": source}, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Deployment error: {exc}")

