class SumoSearchError(Exception):
    pass


class AuthError(SumoSearchError):
    pass


class ValidationError(SumoSearchError):
    pass


class APIError(SumoSearchError):
    pass


class RateLimitError(APIError):
    pass


class JobCancelledError(APIError):
    pass


class JobTimeoutError(SumoSearchError):
    pass


class ConfigError(SumoSearchError):
    pass
