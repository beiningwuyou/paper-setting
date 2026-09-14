from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from paper_setting_core.errors import RulePackInvalidError
from paper_setting_core.rulepacks.models import RulePack


def canonical_rule_pack_json(rule_pack: RulePack) -> str:
    return json.dumps(
        rule_pack.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def rule_pack_hash(rule_pack: RulePack) -> str:
    return hashlib.sha256(canonical_rule_pack_json(rule_pack).encode("utf-8")).hexdigest()


def load_rule_pack(path: Path) -> RulePack:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return RulePack.model_validate(payload)
    except (OSError, json.JSONDecodeError, PydanticValidationError) as exc:
        raise RulePackInvalidError(str(exc)) from exc


def parse_rule_pack(payload: bytes) -> RulePack:
    try:
        return RulePack.model_validate_json(payload)
    except PydanticValidationError as exc:
        raise RulePackInvalidError(str(exc)) from exc

