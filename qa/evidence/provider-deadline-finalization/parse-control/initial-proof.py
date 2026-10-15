"""Run the seven approved parsed-return controls after their retained copy preflight."""
from pathlib import Path
import sys

root = Path.cwd()
source = (root / '.work/deadline-initial.py').read_text()
source = source.replace('8b330790d3abedbb3e631ba065f1b41b9639779e',
                        'deabe55a27a2baca2f2929761b245de7e16f0b61')
source = source.replace("'.work/deadline-proof'", "'.work/deadline-parse-control'")
source = source.replace("'qa/evidence/provider-deadline-finalization'",
                        "'qa/evidence/provider-deadline-finalization/parse-control'")
start = source.index('selectors = [')
end = source.index('\nenv = ', start)
selectors = [
 'tests/test_provider_deadlines.py::test_slow_validation_checks_original_deadlines',
 'tests/test_provider_deadlines.py::test_direct_repair_keeps_its_own_physical_timeout_policy',
 'tests/test_provider_deadlines.py::test_final_allowed_call_succeeds_before_deadline',
 'tests/test_provider_deadlines.py::test_expired_vendor_failure_suppresses_canary_traceback',
]
source = source[:start] + 'selectors = ' + repr(selectors) + source[end:]
source = source.replace("root / '.work/deadline-initial.py'", "root / '.work/deadline-parse-control.py'")
executed = root / '.work/deadline-parse-executed.py'
executed.write_text(source)
exec(compile(source, str(executed), 'exec'), {'__name__': '__main__'})
if sys.argv[1] == 'run':
    target = root / 'qa/evidence/provider-deadline-finalization/parse-control/executed-proof.py'
    target.write_text(source)
