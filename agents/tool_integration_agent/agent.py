"""
Main Tool Integration Agent implementation.
Provides secure interface to Google Drive, Gmail, and database systems.
"""

from pydantic_ai import Agent, RunContext
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid

from .providers import get_llm_model
from .prompts import SYSTEM_PROMPT
from .dependencies import ToolIntegrationDependencies
from .models import ToolRequest, ToolResponse, GoogleDriveQuery, GmailQuery, DatabaseQuery
from .tools import (
    google_drive_search_impl,
    gmail_extract_content_impl,
    database_query_impl,
    ToolIntegrationError,
    AuthenticationError,
    RateLimitError,
    ValidationError
)
from .settings import load_settings

logger = logging.getLogger(__name__)

# Initialize the agent
settings = load_settings()
model = get_llm_model(settings)

tool_integration_agent = Agent(
    model,
    deps_type=ToolIntegrationDependencies,
    system_prompt=SYSTEM_PROMPT,
)


@tool_integration_agent.tool
async def google_drive_search(
    ctx: RunContext[ToolIntegrationDependencies],
    query: str,
    file_types: List[str] = ["docs", "sheets", "pdf"],
    max_results: int = 10
) -> Dict[str, Any]:
    """
    Search Google Drive documents by query with file type and date filters.

    Args:
        ctx: Agent context with dependencies
        query: Search query for document titles and content
        file_types: File types to search (docs, sheets, pdf, slides)
        max_results: Maximum documents to return (1-50)

    Returns:
        Dict containing search results, metadata, and quality metrics
    """
    try:
        logger.info(f"Starting Google Drive search: query='{query}', file_types={file_types}")

        # Validate inputs
        if not query.strip():
            raise ValidationError("Search query cannot be empty")

        if max_results < 1 or max_results > 50:
            raise ValidationError("max_results must be between 1 and 50")

        # Execute search
        result = await google_drive_search_impl(
            deps=ctx.deps,
            query=query,
            file_types=file_types,
            max_results=max_results
        )

        logger.info(f"Google Drive search completed: {len(result.get('results', []))} documents found")
        return result

    except (AuthenticationError, RateLimitError, ValidationError) as e:
        logger.error(f"Google Drive search failed: {e}")
        return {
            "success": False,
            "error": {
                "type": type(e).__name__.lower().replace('error', ''),
                "message": str(e),
                "code": f"GDRIVE_{type(e).__name__.upper()}",
                "retry_after": 60 if isinstance(e, RateLimitError) else None
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": ctx.deps.request_id
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in Google Drive search: {e}")
        return {
            "success": False,
            "error": {
                "type": "internal",
                "message": f"Internal error during Google Drive search: {str(e)}",
                "code": "GDRIVE_INTERNAL_ERROR"
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": ctx.deps.request_id
            }
        }


@tool_integration_agent.tool
async def gmail_extract_content(
    ctx: RunContext[ToolIntegrationDependencies],
    search_query: str,
    date_range: Optional[Dict[str, str]] = None,
    max_messages: int = 20
) -> Dict[str, Any]:
    """
    Extract relevant information from Gmail messages with threading support.

    Args:
        ctx: Agent context with dependencies
        search_query: Gmail search query (supports Gmail search operators)
        date_range: Optional date range with 'start' and 'end' keys (YYYY-MM-DD)
        max_messages: Maximum messages to analyze (1-100)

    Returns:
        Dict containing extracted messages, metadata, and privacy flags
    """
    try:
        logger.info(f"Starting Gmail content extraction: query='{search_query}', max_messages={max_messages}")

        # Validate inputs
        if not search_query.strip():
            raise ValidationError("Search query cannot be empty")

        if max_messages < 1 or max_messages > 100:
            raise ValidationError("max_messages must be between 1 and 100")

        if date_range:
            if not isinstance(date_range, dict) or not all(k in date_range for k in ['start', 'end']):
                raise ValidationError("date_range must contain 'start' and 'end' keys")

        # Execute extraction
        result = await gmail_extract_content_impl(
            deps=ctx.deps,
            search_query=search_query,
            date_range=date_range,
            max_messages=max_messages
        )

        logger.info(f"Gmail extraction completed: {len(result.get('results', []))} messages extracted")
        return result

    except (AuthenticationError, RateLimitError, ValidationError) as e:
        logger.error(f"Gmail extraction failed: {e}")
        return {
            "success": False,
            "error": {
                "type": type(e).__name__.lower().replace('error', ''),
                "message": str(e),
                "code": f"GMAIL_{type(e).__name__.upper()}",
                "retry_after": 60 if isinstance(e, RateLimitError) else None
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": ctx.deps.request_id
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in Gmail extraction: {e}")
        return {
            "success": False,
            "error": {
                "type": "internal",
                "message": f"Internal error during Gmail extraction: {str(e)}",
                "code": "GMAIL_INTERNAL_ERROR"
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": ctx.deps.request_id
            }
        }


@tool_integration_agent.tool
async def database_query(
    ctx: RunContext[ToolIntegrationDependencies],
    query: str,
    database_type: str,
    result_format: str = "json"
) -> Dict[str, Any]:
    """
    Execute safe SELECT queries against configured databases.

    Args:
        ctx: Agent context with dependencies
        query: SELECT SQL query to execute
        database_type: Type of database ('postgresql' or 'sqlite')
        result_format: Format for results ('json' or 'csv')

    Returns:
        Dict containing query results, metadata, and execution info
    """
    try:
        logger.info(f"Starting database query: type={database_type}, format={result_format}")

        # Validate inputs
        if not query.strip():
            raise ValidationError("Query cannot be empty")

        if database_type not in ["postgresql", "sqlite"]:
            raise ValidationError("database_type must be 'postgresql' or 'sqlite'")

        if result_format not in ["json", "csv"]:
            raise ValidationError("result_format must be 'json' or 'csv'")

        # Execute query
        result = await database_query_impl(
            deps=ctx.deps,
            query=query,
            database_type=database_type,
            result_format=result_format
        )

        logger.info(f"Database query completed: {len(result.get('results', []))} rows returned")
        return result

    except (ValidationError) as e:
        logger.error(f"Database query validation failed: {e}")
        return {
            "success": False,
            "error": {
                "type": "validation",
                "message": str(e),
                "code": "DB_VALIDATION_ERROR"
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": ctx.deps.request_id
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error in database query: {e}")
        return {
            "success": False,
            "error": {
                "type": "internal",
                "message": f"Internal error during database query: {str(e)}",
                "code": "DB_INTERNAL_ERROR"
            },
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": ctx.deps.request_id
            }
        }


async def run_tool_integration_agent(
    request: ToolRequest,
    user_id: str = None,
    session_id: str = None
) -> ToolResponse:
    """
    Main entry point for running the Tool Integration Agent.

    Args:
        request: Tool request with parameters
        user_id: Optional user identifier
        session_id: Optional session identifier

    Returns:
        ToolResponse with results or error information
    """
    start_time = datetime.utcnow()

    try:
        # Create dependencies with context
        deps = ToolIntegrationDependencies(
            settings=settings,
            session_id=session_id or str(uuid.uuid4()),
            user_id=user_id,
            request_id=request.request_id
        )

        logger.info(f"Processing tool request: {request.tool_type} - {request.operation}")

        # Route request to appropriate tool
        if request.tool_type == "google_drive":
            # Convert parameters to GoogleDriveQuery for validation
            drive_query = GoogleDriveQuery(**request.parameters)
            result = await google_drive_search(
                RunContext(deps=deps),
                query=drive_query.query,
                file_types=drive_query.file_types,
                max_results=drive_query.max_results
            )

        elif request.tool_type == "gmail":
            # Convert parameters to GmailQuery for validation
            gmail_query = GmailQuery(**request.parameters)
            result = await gmail_extract_content(
                RunContext(deps=deps),
                search_query=gmail_query.search_query,
                date_range=gmail_query.date_range,
                max_messages=gmail_query.max_messages
            )

        elif request.tool_type == "database":
            # Convert parameters to DatabaseQuery for validation
            db_query = DatabaseQuery(**request.parameters)
            result = await database_query(
                RunContext(deps=deps),
                query=db_query.query,
                database_type=db_query.database_type,
                result_format=db_query.result_format
            )

        else:
            raise ValidationError(f"Unsupported tool type: {request.tool_type}")

        # Convert result to ToolResponse
        execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        response = ToolResponse(
            request_id=request.request_id,
            tool_type=request.tool_type,
            success=result.get("success", False),
            results=result.get("results", []),
            metadata=result.get("metadata", {}),
            extraction_quality=result.get("metadata", {}).get("extraction_quality", 1.0),
            timestamp=datetime.utcnow(),
            execution_time_ms=execution_time,
            errors=result.get("error", {}).get("message", "").split("\n") if not result.get("success", True) else []
        )

        # Cleanup dependencies
        await deps.cleanup()

        logger.info(f"Tool request completed: {request.tool_type} - success={response.success}")
        return response

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return ToolResponse(
            request_id=request.request_id,
            tool_type=request.tool_type,
            success=False,
            results=[],
            metadata={"error_type": "validation"},
            extraction_quality=0.0,
            timestamp=datetime.utcnow(),
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            errors=[str(e)]
        )

    except Exception as e:
        logger.error(f"Unexpected error processing request: {e}")
        return ToolResponse(
            request_id=request.request_id,
            tool_type=request.tool_type,
            success=False,
            results=[],
            metadata={"error_type": "internal"},
            extraction_quality=0.0,
            timestamp=datetime.utcnow(),
            execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000),
            errors=[f"Internal error: {str(e)}"]
        )


# Health check function for monitoring
async def health_check() -> Dict[str, Any]:
    """
    Check the health status of the Tool Integration Agent.

    Returns:
        Dict with health status information
    """
    try:
        # Create minimal dependencies for health check
        deps = ToolIntegrationDependencies(
            settings=settings,
            session_id="health_check",
            request_id="health_check"
        )

        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_type": "tool_integration",
            "version": "1.0.0",
            "services": {
                "google_drive": "unknown",
                "gmail": "unknown",
                "database": "unknown"
            }
        }

        # Test Google Drive service (if not mocked)
        try:
            if not settings.use_mock_google_apis:
                await deps.get_google_drive_service()
            health_status["services"]["google_drive"] = "healthy"
        except Exception as e:
            health_status["services"]["google_drive"] = f"unhealthy: {str(e)}"

        # Test Gmail service (if not mocked)
        try:
            if not settings.use_mock_google_apis:
                await deps.get_gmail_service()
            health_status["services"]["gmail"] = "healthy"
        except Exception as e:
            health_status["services"]["gmail"] = f"unhealthy: {str(e)}"

        # Test database connection (if not mocked)
        try:
            if not settings.use_mock_database:
                await deps.get_database_connection()
            health_status["services"]["database"] = "healthy"
        except Exception as e:
            health_status["services"]["database"] = f"unhealthy: {str(e)}"

        # Determine overall status
        unhealthy_services = [k for k, v in health_status["services"].items() if "unhealthy" in str(v)]
        if unhealthy_services:
            health_status["status"] = "degraded"
            health_status["issues"] = unhealthy_services

        await deps.cleanup()
        return health_status

    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_type": "tool_integration",
            "error": str(e)
        }