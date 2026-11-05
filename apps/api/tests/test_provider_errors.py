from io import BytesIO
import json
from urllib.error import HTTPError
from app.services.provider_errors import provider_error_metadata


def test_provider_diagnostics_exclude_secret_body_and_message():
    error = HTTPError('https://api.openai.com/v1/responses',429,'SECRET',{},BytesIO(json.dumps({'error':{'code':'rate_limit_exceeded','message':'SECRET KEY AND REQUEST'}}).encode()))
    metadata = provider_error_metadata(error)
    assert metadata == {'error_type':'HTTPError','http_status':429,'provider_code':'rate_limit_exceeded'}
    assert 'SECRET' not in json.dumps(metadata)


def test_untrusted_provider_code_and_non_json_body_are_ignored():
    error = HTTPError('https://api.openai.com',500,'secret',{},BytesIO(b'not json secret'))
    assert provider_error_metadata(error) == {'error_type':'HTTPError','http_status':500}
