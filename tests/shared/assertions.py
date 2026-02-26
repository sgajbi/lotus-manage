from src.core.models import FxSpotIntent, SecurityTradeIntent


def assert_status(result, expected_status: str) -> None:
    assert result.status == expected_status


def assert_dq_contains(result, bucket: str, value: str) -> None:
    assert value in result.diagnostics.data_quality[bucket]


def find_excluded(result, instrument_id: str):
    return next((e for e in result.universe.excluded if e.instrument_id == instrument_id), None)


def security_intents(result):
    return [i for i in result.intents if isinstance(i, SecurityTradeIntent)]


def fx_intents(result):
    return [i for i in result.intents if isinstance(i, FxSpotIntent)]
