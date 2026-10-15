"""Failed physical attempts retain null usage and the actual final winner."""
import sys
from pathlib import Path
import pytest

root = Path.cwd()
sys.path.insert(0, str(root / 'tests'))
from litellm_fake import install, reply
from autotester.providers.model_chain import ModelChainProvider, TEXT_FALLBACK
from pydantic import BaseModel

class Answer(BaseModel):
    ok: bool

with pytest.MonkeyPatch.context() as patch:
    patch.setenv('AUTOTESTER_ROOT', str(root / '.work/checker-text-cycle2'))
    patch.setenv('OLLAMA_API_KEY', 'checker-dummy-ollama')
    patch.setenv('GEMINI_API_KEY', 'checker-dummy-gemini')
    patch.delenv('AUTOTESTER_MODEL_ORDER', raising=False)
    patch.delenv('AUTOTESTER_TEXT_FALLBACK_MODEL', raising=False)
    install(patch, [TimeoutError(), TimeoutError(), reply('{"ok":true}')])
    chain = ModelChainProvider()
    assert chain.act('synthetic', Answer).ok
    assert len(chain.usage) == 3
    assert all(u.failed_calls == 1 and u.input_tokens is None and u.output_tokens is None
               for u in chain.usage[:2])
    assert chain.served == 'litellm:' + TEXT_FALLBACK
    assert len(chain.fallback_reasons) == 2
print('Failed usage null, two safe reasons and actual Gemini winner: passed')
