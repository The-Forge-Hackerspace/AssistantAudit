"""
Health check endpoints for service monitoring and orchestration.

Provides three endpoints:
- /health - Basic health check (always responds if app is running)
- /ready - Readiness check (includes database connectivity)
- /liveness - Kubernetes liveness probe (same as /health)

These endpoints are typically used by:
- Prometheus for service monitoring
- Kubernetes for pod health management
- Load balancers for traffic routing decisions
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .database import SessionLocal


logger = logging.getLogger(__name__)


class HealthCheckService:
    """Service for health and readiness checks."""

    @staticmethod
    def get_health_status() -> Dict[str, Any]:
        """
        Get basic health status of the application.
        
        Returns:
            dict with status, timestamp, and version
        """
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def check_database_connectivity() -> Dict[str, Any]:
        """
        Check database connectivity and responsiveness.
        
        Returns:
            dict with database status and response time
        """
        start_time = time.time()
        
        try:
            db: Session = SessionLocal()
            try:
                # Simple query to verify connection
                result = db.execute(text("SELECT 1"))
                result.fetchone()
                
                response_time = time.time() - start_time
                
                return {
                    "status": "connected",
                    "response_time_ms": round(response_time * 1000, 2),
                }
            finally:
                db.close()
        except Exception as exc:
            logger.error(f"Database connectivity check failed: {exc}", exc_info=True)
            response_time = time.time() - start_time
            
            return {
                "status": "disconnected",
                "response_time_ms": round(response_time * 1000, 2),
                "error": str(exc),
            }

    @staticmethod
    def get_ready_status() -> Dict[str, Any]:
        """
        Get detailed readiness status including all dependencies.
        
        Returns:
            dict with overall ready status and component status
        """
        health = HealthCheckService.get_health_status()
        db_check = HealthCheckService.check_database_connectivity()
        
        # Determine if ready based on components
        db_ready = db_check.get("status") == "connected"
        overall_ready = db_ready
        
        return {
            "ready": overall_ready,
            "timestamp": health["timestamp"],
            "components": {
                "application": {
                    "status": "ready",
                    "description": "Application is running",
                },
                "database": {
                    "status": "ready" if db_ready else "not_ready",
                    "response_time_ms": db_check.get("response_time_ms"),
                    "description": db_check.get("error") if not db_ready else "Database connection OK",
                },
            },
        }

    @staticmethod
    def get_liveness_status() -> Dict[str, Any]:
        """
        Get liveness status for Kubernetes.
        
        Returns:
            dict with liveness status (same as health status)
        """
        return HealthCheckService.get_health_status()
