"""The declarations a runner hands to the oracles that need one (T-217 CORE-REQUEST, MP27, MP28).

One job: `OracleDeclarations` -- the typed, validated declarations of the oracles that cannot work
without one (the credential policy and the paid paths), carried on `OracleContext.declarations`.
Before this existed those two oracles read `<run_dir>/credential_policy.json` and
`<run_dir>/payment_paths.json`; a runner can now build the declaration once and pass it in. A
declaration is validated when the context is built, and a validation error never echoes the
offending input (`hide_input_in_errors`), because a declaration may hold a `{{SECRET:KEY}}`
placeholder or a canary. The shapes themselves live in `schema/credential_policy.py` and
`schema/payment_path.py`; they are imported, never redefined here.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from autotester.schema.credential_policy import CredentialPolicy
from autotester.schema.payment_path import PaymentDeclaration


class OracleDeclarations(BaseModel):
    """Per-oracle declarations; an oracle whose field is `None` falls back to its run-dir file."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    credential_policy: CredentialPolicy | None = None
    payment_paths: PaymentDeclaration | None = None
