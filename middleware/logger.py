import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from utils.logger import get_logger

logger = get_logger("app.middleware.logging")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        # Log incoming request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - Started"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Status: {response.status_code} - Duration: {process_time:.3f}s"
        )
        
        # Add custom headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
