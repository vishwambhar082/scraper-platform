# src/agents/deepagent_repair_engine.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from src.agents.deepagent_selector_healer import SelectorPatch, propose_selector_patches
from src.agents.llm_patch_generator import generate_repair_patches
from src.agents.selector_patch_applier import (
    apply_patches,
    load_selectors,
    save_selectors,
)
from src.common.config_loader import load_source_config
from src.common.logging_utils import get_logger
from src.common.paths import REPLAY_SNAPSHOTS_DIR

log = get_logger("deepagent-repair-engine")


@dataclass
class PatchResult:
    source: str
    field: str
    applied: bool
    reason: str | None = None


def _load_latest_snapshots(source_dir: Path) -> Optional[Tuple[str, str]]:
    html_files = sorted(source_dir.glob("*.html"), key=lambda p: (p.stat().st_mtime, p.name))
    if len(html_files) < 2:
        return None
    old_html = html_files[-2].read_text(encoding="utf-8", errors="ignore")
    new_html = html_files[-1].read_text(encoding="utf-8", errors="ignore")
    return old_html, new_html


def run_repair_session(
    source: str,
    selectors_path: Optional[Path] = None,
    use_llm: bool = True,
) -> List[PatchResult]:
    """
    Attempt selector repair using stored replay snapshots.

    Now supports LLM-based patch generation if enabled in config.

    Args:
        source: Source name
        selectors_path: Optional path to selectors.json
        use_llm: Whether to use LLM for patch generation (if enabled in config)

    Returns:
        List of patch results
    """
    source_dir = REPLAY_SNAPSHOTS_DIR / source
    if not source_dir.exists():
        log.warning("No replay snapshots found for source=%s at %s", source, source_dir)
        return []

    snapshots = _load_latest_snapshots(source_dir)
    if not snapshots:
        log.warning("Not enough snapshots to compute patches for source=%s", source)
        return []

    selectors_path = selectors_path or Path(__file__).resolve().parents[1] / "scrapers" / source / "selectors.json"
    try:
        selectors = load_selectors(selectors_path)
    except FileNotFoundError:
        log.warning("selectors.json missing for %s at %s", source, selectors_path)
        return []

    old_html, new_html = snapshots
    results: List[PatchResult] = []

    # Try LLM-based repair if enabled
    if use_llm:
        try:
            source_config = load_source_config(source)
            llm_config = source_config.get("llm", {})

            if llm_config.get("enabled", False):
                failure_context = {
                    "html_old": old_html,
                    "html_new": new_html,
                    "old_selectors": selectors,
                    "error_message": "Selector mismatch detected",
                }

                llm_patches = generate_repair_patches(source, source_config, failure_context)

                if llm_patches:
                    log.info("Generated %d LLM patches for %s", len(llm_patches), source)
                    # Apply LLM-generated selector patches
                    for patch in llm_patches:
                        if "selectors.json" in patch.file_path:
                            try:
                                import json

                                new_selectors = json.loads(patch.new_code)
                                updated = apply_patches(
                                    selectors,
                                    [SelectorPatch(field=k, new_selector=v) for k, v in new_selectors.items()],
                                )
                                save_selectors(selectors_path, updated)
                                results.append(
                                    PatchResult(
                                        source=source,
                                        field="selectors",
                                        applied=True,
                                        reason=f"LLM patch: {patch.description}",
                                    )
                                )
                            except Exception as exc:
                                log.error("Failed to apply LLM patch", extra={"error": str(exc)})

                    if results:
                        return results
        except Exception as exc:
            log.warning("LLM repair failed, falling back to classic", extra={"error": str(exc)})

    # Fallback to classic selector repair
    patches: List[SelectorPatch] = propose_selector_patches(old_html, new_html, selectors)

    if not patches:
        log.info("No selector patches proposed for %s", source)
        return results

    updated = apply_patches(selectors, patches)
    save_selectors(selectors_path, updated)

    for p in patches:
        results.append(PatchResult(source=source, field=p.field, applied=True, reason="classic patch"))

    log.info("Repair session complete for %s (patches applied=%d)", source, len(results))
    return results
