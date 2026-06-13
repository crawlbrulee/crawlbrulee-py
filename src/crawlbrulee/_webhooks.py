"""Webhook signature verification (pure crypto, no network).

The crawlbrulee API signs every webhook delivery with HMAC-SHA256 over the
``{timestamp}.{raw_body}`` payload, sending the result in an
``X-Cwbl-Signature`` header. During a signing-secret rotation grace window a
second ``X-Cwbl-Signature-Rotated`` header (signed with the *previous* secret)
is sent alongside it, so callers can verify with their current secret no matter
which side of the rotation they're on.

:func:`verify_webhook_signature` checks both headers against the caller's secret
and **returns** a result rather than raising -- a failed verification is normal
control flow (an attacker probing your endpoint, a stale secret, a replay), not
an exceptional condition.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

#: Header carrying the signature made with the current signing secret. Always sent.
PRIMARY_HEADER = "X-Cwbl-Signature"
#: Header carrying the signature made with the *previous* secret, present only
#: during a rotation grace window.
ROTATED_HEADER = "X-Cwbl-Signature-Rotated"

#: Default replay-protection window in seconds. Reject deliveries whose timestamp
#: is further than this from "now". Pass ``tolerance_seconds=0`` to disable.
DEFAULT_TOLERANCE_SECONDS = 300

#: Strict header grammar: ``t=<unix_seconds>,v1=<64 lowercase hex>``.
_SIGNATURE_RE = re.compile(r"^t=(\d+),v1=([0-9a-f]{64})$")

#: Reason codes set on a failed verification.
WebhookVerificationReason = Literal[
    "missing_signature",
    "malformed_signature",
    "timestamp_out_of_tolerance",
    "signature_mismatch",
]


@dataclass
class WebhookVerificationResult:
    """Outcome of :func:`verify_webhook_signature`.

    On success ``verified`` is ``True`` and ``signed_with`` records which header
    matched (``"primary"`` for the current secret, ``"rotated"`` for the previous
    one during a rotation window). On failure ``verified`` is ``False`` and
    ``reason`` carries a stable code describing why.
    """

    #: Whether a valid signature was found for the given secret.
    verified: bool
    #: Which header matched, set only when ``verified`` is ``True``.
    signed_with: Literal["primary", "rotated"] | None = None
    #: Why verification failed, set only when ``verified`` is ``False``.
    reason: WebhookVerificationReason | None = None


def _header(headers: Mapping[str, str], name: str) -> str | None:
    """Case-insensitive header lookup (frameworks lower/title-case header keys)."""
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None


def _expected_signature(secret: str, timestamp: str, body: bytes) -> str:
    """Compute the lowercase-hex HMAC-SHA256 over ``{timestamp}.{body}``."""
    signed_payload = timestamp.encode("utf-8") + b"." + body
    mac = hmac.new(secret.encode("utf-8"), msg=signed_payload, digestmod=hashlib.sha256)
    return mac.hexdigest()


def verify_webhook_signature(
    *,
    payload: str | bytes,
    headers: Mapping[str, str],
    secret: str,
    tolerance_seconds: int = DEFAULT_TOLERANCE_SECONDS,
) -> WebhookVerificationResult:
    """Verify a crawlbrulee webhook signature against ``secret``.

    Pass the **raw** request body (the exact bytes the server signed -- not
    re-serialized JSON), the request headers, and your current signing secret.

    The primary header is checked first, then -- during a rotation grace window
    -- the rotated header. Returns a :class:`WebhookVerificationResult`; this
    function never raises on a verification failure.

    Replay protection: the delivery is rejected with ``timestamp_out_of_tolerance``
    when its timestamp differs from "now" by more than ``tolerance_seconds``. Pass
    ``tolerance_seconds=0`` to disable the timestamp check (e.g. in tests).
    """
    body = payload.encode("utf-8") if isinstance(payload, str) else bytes(payload)

    primary = _header(headers, PRIMARY_HEADER)
    rotated = _header(headers, ROTATED_HEADER)
    if primary is None and rotated is None:
        return WebhookVerificationResult(verified=False, reason="missing_signature")

    now = int(time.time())
    saw_malformed = False
    saw_out_of_tolerance = False

    candidates: list[tuple[Literal["primary", "rotated"], str]] = []
    if primary is not None:
        candidates.append(("primary", primary))
    if rotated is not None:
        candidates.append(("rotated", rotated))

    for label, raw in candidates:
        match = _SIGNATURE_RE.match(raw)
        if match is None:
            saw_malformed = True
            continue

        timestamp, signature = match.group(1), match.group(2)

        if tolerance_seconds and abs(now - int(timestamp)) > tolerance_seconds:
            saw_out_of_tolerance = True
            continue

        expected = _expected_signature(secret, timestamp, body)
        if hmac.compare_digest(expected, signature):
            return WebhookVerificationResult(verified=True, signed_with=label)

    # No header verified. Report the most specific reason observed, preferring a
    # concrete mismatch over a structural problem on the *other* header.
    if saw_out_of_tolerance and not saw_malformed:
        reason: WebhookVerificationReason = "timestamp_out_of_tolerance"
    elif saw_malformed and not saw_out_of_tolerance:
        reason = "malformed_signature"
    else:
        reason = "signature_mismatch"
    return WebhookVerificationResult(verified=False, reason=reason)
