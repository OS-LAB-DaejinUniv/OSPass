from fastapi import status
from fastapi.responses import RedirectResponse
from typing import Optional
from urllib.parse import urlencode
from custom_log import LoggerSetup

logger_setup = LoggerSetup()
logger = logger_setup.logger

OAUTH2_ERROR_TYPES = {
    400: "invalid_request",
    401: "invalid_client",
    403: "access_denied",
    404: "invalid_request",
    500: "server_error",
    503: "temporarily_unavailable"
}

def redirect_with_oauth2_error(redirect_uri: str, status_code: int, detail: str, state: Optional[str] = None) -> RedirectResponse:
    """
    OAuth 2.0 오류 응답 형식으로 redirect_uri로 리다이렉트합니다.
    """
    error_code = OAUTH2_ERROR_TYPES.get(status_code, "server_error")
    error_description = detail # TODO: Sanitize/generalize detail for production

    query_params = {"error": error_code, "error_description": error_description}
    if state is not None:
        query_params["state"] = state

    encoded_params = urlencode({k: v for k, v in query_params.items() if v is not None})
    redirect_url = f"{redirect_uri}?{encoded_params}"
    logger.error(f"Redirecting to {redirect_uri} with OAuth2 error: {error_code} (Status {status_code}), Detail: {detail}")
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)