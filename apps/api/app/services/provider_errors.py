"""Operational error fields only; never expose provider bodies or credentials."""
import json
import re
from urllib.error import HTTPError


def provider_error_metadata(exc: Exception) -> dict:
    metadata = {'error_type':type(exc).__name__}
    if isinstance(exc,HTTPError):
        metadata['http_status'] = exc.code
        try:
            code = json.loads(exc.read(16000)).get('error',{}).get('code')
            if isinstance(code,str) and re.fullmatch(r'[a-z_]{1,80}',code):
                metadata['provider_code'] = code
        except (ValueError,AttributeError,OSError):
            pass
    return metadata
