class DomainError(Exception):
    """Error de negocio. Se traduce a HTTP en un solo lugar (app/main.py)."""

    status_code = 400
    default_code = "domain_error"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code


class ValidationFailed(DomainError):
    status_code = 400
    default_code = "validation_failed"


class NotFound(DomainError):
    status_code = 404
    default_code = "not_found"


class Conflict(DomainError):
    status_code = 409
    default_code = "conflict"
