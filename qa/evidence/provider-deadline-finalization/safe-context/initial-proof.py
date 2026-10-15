"""Prepare and run only the nine explicitly granted safe-context controls."""
from pathlib import Path
import sys

root = Path.cwd()
source = (root / '.work/deadline-initial.py').read_text()
source = source.replace('8b330790d3abedbb3e631ba065f1b41b9639779e',
                        '10abf59e03e8459064508d309072f1bf05a1e4be')
source = source.replace("'.work/deadline-proof'", "'.work/deadline-safe-context'")
source = source.replace("'qa/evidence/provider-deadline-finalization'",
                        "'qa/evidence/provider-deadline-finalization/safe-context'")
start = source.index('selectors = [')
end = source.index('\nenv = ', start)
selectors = [
 'tests/test_provider_deadlines.py::test_expired_vendor_failure_suppresses_canary_traceback',
 'tests/test_provider_deadlines.py::test_late_chain_response_preserves_usage_and_never_falls_back',
 'tests/test_provider_deadlines.py::test_direct_transport_deadline_is_anchored_before_response',
 'tests/test_provider_deadlines.py::test_final_allowed_call_succeeds_before_deadline',
 'tests/test_provider_deadline_consumers.py::test_gemini_sdk_response_checks_enclosing_deadline',
 'tests/test_provider_deadline_consumers.py::test_gemini_validated_media_is_checked_before_return',
 'tests/test_provider_deadline_consumers.py::test_probe_completion_clears_capability_if_evaluation_runs_late',
]
source = source[:start] + 'selectors = ' + repr(selectors) + source[end:]
source = source.replace("root / '.work/deadline-initial.py'", "root / '.work/deadline-safe-context.py'")
namespace = {'__name__': '__main__'}
if not (root / '.work/deadline-safe-context').exists():
    sys.argv[1:] = ['prepare']
    exec(compile(source, str(root / '.work/deadline-safe-context-executed.py'), 'exec'), namespace)
sys.argv[1:] = ['run']
exec(compile(source, str(root / '.work/deadline-safe-context-executed.py'), 'exec'), namespace)
(root / 'qa/evidence/provider-deadline-finalization/safe-context/executed-proof.py').write_text(source)
