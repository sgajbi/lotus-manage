from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


def dump_model_json(model: BaseModel) -> str:
    return json.dumps(
        model.model_dump(mode="json"),
        separators=(",", ":"),
        sort_keys=True,
    )


def load_model_json(model_type: type[ModelT], payload: str | dict[str, Any]) -> ModelT:
    if isinstance(payload, str):
        return model_type.model_validate(json.loads(payload))
    return model_type.model_validate(payload)
