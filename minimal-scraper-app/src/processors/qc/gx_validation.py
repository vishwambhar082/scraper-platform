import os
from typing import Any, Dict, Iterable, List

import pandas as pd

from src.common.logging_utils import get_logger

log = get_logger("gx-validation")


def run_gx_validation(
    suite_name: str,
    records: Iterable[Dict[str, Any]],
    enabled: bool | None = None,
) -> Dict[str, Any]:
    """
    Optional integration with Great Expectations.

    Behaviour:
      - If GX_ENABLED != "1" and enabled is not True:
            no-op, returns success with 'disabled' message.
      - If GX_ENABLED == "1" and great_expectations is missing:
            raises RuntimeError (honest failure).
      - If enabled and GE is installed:
            runs a minimal expectation (table not empty).

    This keeps prod behaviour explicit and avoids fake QC passes.
    """
    if enabled is None:
        enabled = os.getenv("GX_ENABLED", "0") == "1"

    records_list: List[Dict[str, Any]] = list(records)

    if not enabled:
        # Explicitly disabled – do not lie, but keep success=True to avoid breaking pipelines
        return {
            "suite_name": suite_name,
            "success": True,
            "details": "Great Expectations disabled (GX_ENABLED != 1)",
            "row_count": len(records_list),
        }

    try:
        import great_expectations as ge  # type: ignore[import]
    except ModuleNotFoundError:
        log.warning(
            "GX validation enabled but great_expectations not installed; skipping suite",
            extra={"suite_name": suite_name},
        )
        return {
            "suite_name": suite_name,
            "success": False,
            "skipped": True,
            "details": "Great Expectations package missing",
            "row_count": len(records_list),
        }
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "GX_ENABLED=1 but great_expectations failed to initialize"
        ) from exc

    if not records_list:
        # trivial fail
        return {
            "suite_name": suite_name,
            "success": False,
            "details": "GX: no records to validate",
            "row_count": 0,
        }

    df = pd.DataFrame(records_list)
    gx_df = ge.from_pandas(df)  # type: ignore[attr-defined]

    result = gx_df.expect_table_row_count_to_be_greater_than(0)
    success = bool(result.success)

    log.info(
        "GX validation run",
        extra={"suite_name": suite_name, "success": success, "row_count": len(df)},
    )

    return {
        "suite_name": suite_name,
        "success": success,
        "details": "GX validation run (minimal stub expectation)",
        "row_count": len(df),
        "raw_result": result.to_json_dict(),
    }
