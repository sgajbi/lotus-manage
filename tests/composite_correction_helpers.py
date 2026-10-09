"""Controlled three-member history; supplied decisions do not qualify population."""

from copy import deepcopy


def definition_body():
    return {
        "display_name": "Synthetic correction-window composite",
        "strategy_code": "SYNTHETIC_BALANCED",
        "reporting_currency": "USD",
        "inception_date": "2026-01-01",
        "eligibility_policy_version": "synthetic-policy",
        "source_authority": {"policy_version": "synthetic-authority"},
        "correlation_id": "synthetic-definition",
    }


def decision(member, first="2026-01-01", last=None, *, excluded=False):
    return {
        "portfolio_id": member,
        "effective_from": first,
        "effective_to": last,
        "status": "EXCLUDED" if excluded else "INCLUDED",
        "reason_code": "SYNTHETIC_POLICY_EXCLUSION" if excluded else None,
        "discretionary": True,
        "approval_ref": "synthetic-decision-approval",
        "source_snapshot_id": "synthetic-observation",
    }


def original_body():
    return {
        "policy_version": "synthetic-policy",
        "source_cut_id": "synthetic-cut-original",
        "correlation_id": "synthetic-membership-original",
        "decisions": [
            decision("A"),
            decision("B", last="2026-01-31"),
            decision("B", first="2026-02-01", excluded=True),
            decision("C", last="2026-01-15"),
        ],
    }


def correction_body():
    original = deepcopy(original_body())
    return original | {
        "source_cut_id": "synthetic-cut-corrected",
        "correlation_id": "synthetic-membership-corrected",
        "supersedes_membership_revision": "m1",
        "affected_from": "2026-01-05",
        "affected_to": "2026-01-05",
        "decisions": [
            decision("A", last="2026-01-04"),
            decision("A", first="2026-01-05", last="2026-01-05", excluded=True),
            decision("A", first="2026-01-06"),
            *original["decisions"][1:],
        ],
    }
