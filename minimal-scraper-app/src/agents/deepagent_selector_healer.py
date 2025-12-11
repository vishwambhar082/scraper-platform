# src/agents/deepagent_selector_healer.py

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup
from soupsieve import SelectorSyntaxError

from src.common.logging_utils import get_logger

log = get_logger("deepagent-selector-healer")


@dataclass
class SelectorPatch:
    field: str
    old_selector: str
    new_selector: str
    confidence: float


def propose_selector_patches(
    old_snapshot_html: str,
    new_snapshot_html: str,
    selectors: Dict[str, Any],
) -> List[SelectorPatch]:
    """Compare snapshots and propose simple selector fixes."""

    old_soup = BeautifulSoup(old_snapshot_html, "html.parser")
    new_soup = BeautifulSoup(new_snapshot_html, "html.parser")

    patches: List[SelectorPatch] = []
    for field, data in selectors.items():
        selector: Optional[str] = None
        if isinstance(data, dict):
            selector = data.get("css") or data.get("xpath")
        if not selector:
            continue

        try:
            new_matches = new_soup.select(selector)
        except SelectorSyntaxError as exc:
            log.warning("Invalid selector for %s: %s", field, exc)
            new_matches = []
        except Exception as exc:
            log.warning("Unexpected error selecting %s: %s", field, exc)
            new_matches = []

        if new_matches:
            continue

        try:
            old_matches = old_soup.select(selector)
        except SelectorSyntaxError as exc:
            log.warning("Invalid historical selector for %s: %s", field, exc)
            old_matches = []
        except Exception as exc:
            log.warning("Unexpected error selecting historical %s: %s", field, exc)
            old_matches = []

        if not old_matches:
            continue

        ref_el = old_matches[0]
        tag = ref_el.name or "div"
        candidate = None
        confidence = 0.4

        # Prefer id match if the same id shows up in the new snapshot
        if ref_el.has_attr("id"):
            candidate_id = ref_el.get("id")
            if candidate_id and new_soup.find(id=candidate_id):
                candidate = f"#{candidate_id}"
                confidence = 0.8

        # Next, fall back to a class-based selector
        if not candidate and ref_el.has_attr("class"):
            classes = ref_el.get("class") or []
            for cls in classes:
                if new_soup.find(tag, class_=cls) or new_soup.find(class_=cls):
                    candidate = f"{tag}.{cls}"
                    confidence = 0.6
                    break

        # Finally, try matching by contained text.
        # NOTE: :contains() is not a valid CSS selector for BeautifulSoup,
        # so we have to search by text manually.
        if not candidate:
            text_val = ref_el.get_text(strip=True)
            if text_val:
                snippet = text_val[:25].lower()
                # Find the first element of the same tag whose text contains the snippet.
                for el in new_soup.find_all(tag):
                    new_text = el.get_text(strip=True).lower()
                    if snippet and snippet in new_text:
                        base_selector = tag
                        if el.has_attr("id"):
                            base_selector = f"#{el.get('id')}"
                        elif el.has_attr("class"):
                            cls = (el.get("class") or [None])[0]
                            if cls:
                                base_selector = f"{tag}.{cls}"
                        candidate = f"{base_selector}:contains('{text_val}')"
                        confidence = max(confidence, 0.5)
                        break

        if candidate and candidate != selector:
            patches.append(
                SelectorPatch(
                    field=field,
                    old_selector=selector,
                    new_selector=candidate,
                    confidence=confidence,
                )
            )

    if patches:
        log.info("Proposed %d selector patches", len(patches))
    else:
        log.info("No selector changes detected between snapshots")
    return patches
