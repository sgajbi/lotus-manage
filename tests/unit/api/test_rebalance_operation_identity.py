from src.api.services.rebalance_operation_identity import (
    create_batch_analysis_id,
    resolve_rebalance_correlation_id,
)


def test_resolve_rebalance_correlation_id_preserves_caller_value() -> None:
    assert (
        resolve_rebalance_correlation_id(
            "corr-caller",
            entropy_provider=lambda: "unused",
        )
        == "corr-caller"
    )


def test_resolve_rebalance_correlation_id_generates_bounded_prefix() -> None:
    assert (
        resolve_rebalance_correlation_id(
            None,
            entropy_provider=lambda: "1234567890abcdef",
        )
        == "corr_1234567890ab"
    )


def test_create_batch_analysis_id_generates_bounded_prefix() -> None:
    assert create_batch_analysis_id(entropy_provider=lambda: "abcdef123456") == "batch_abcdef12"
