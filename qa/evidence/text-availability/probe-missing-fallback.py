"""No configured Gemini key: stop unavailable after two failed Ollama requests."""
import os
from pathlib import Path
import sys
import tempfile

import pytest

sys.path.insert(0, str(Path.cwd() / 'tests'))
from litellm_fake import install
from autotester.providers.base import ProviderError
from autotester.providers.model_chain import DEFAULT_ORDER, ModelChainProvider
from pydantic import BaseModel, ConfigDict

class MissingFallbackAnswer(BaseModel):
    model_config = ConfigDict(extra='forbid')
    ok: bool

with pytest.MonkeyPatch.context() as patch, tempfile.TemporaryDirectory(dir='.work') as temporary:
    fake = install(patch, [TimeoutError(), TimeoutError()])
    patch.setenv('AUTOTESTER_ROOT', temporary)
    patch.setenv('OLLAMA_API_KEY', 'fake-ollama-value')
    patch.delenv('GOOGLE_API_KEY', raising=False)
    patch.delenv('AUTOTESTER_MODEL_ORDER', raising=False)
    patch.delenv('AUTOTESTER_TEXT_FALLBACK_MODEL', raising=False)
    fake.validate_environment = lambda model=None, **kw: {
        'keys_in_environment': not model.startswith('gemini/'),
        'missing_keys': ['GEMINI_API_KEY']}
    chain = ModelChainProvider()
    try:
        chain.act('prompt', MissingFallbackAnswer)
    except ProviderError as exc:
        assert 'every tier failed' in str(exc)
    else:
        raise AssertionError('missing fallback credentials must remain unavailable')
    assert [c['model'] for c in fake.calls] == list(DEFAULT_ORDER)
    assert chain.served is None
    assert any('credentials_unavailable' in reason for reason in chain.fallback_reasons)
print('missing-fallback: unavailable; requests=2; Gemini requests=0; actual provider unknown')
