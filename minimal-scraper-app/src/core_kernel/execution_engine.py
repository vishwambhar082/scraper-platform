from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any, Dict, List, Optional, Set

from src.common.logging_utils import get_logger
from src.core_kernel.pipeline_compiler import CompiledPipeline
from src.core_kernel.registry import ComponentRegistry

log = get_logger("execution-engine")


class ExecutionEngine:
    """Simple execution engine that runs compiled pipelines."""

    def __init__(self, registry: ComponentRegistry, max_workers: Optional[int] = None):
        self.registry = registry
        self.max_workers = max_workers

    def execute(self, pipeline: CompiledPipeline, runtime_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run a compiled pipeline sequentially.

        Args:
            pipeline: Compiled pipeline with resolved components.
            runtime_params: Optional parameters merged into each step call.

        Returns:
            Dictionary mapping step IDs to their results.
        """

        results: Dict[str, Any] = {}
        runtime_params = runtime_params or {}

        order_index = {step.id: idx for idx, step in enumerate(pipeline.steps)}
        step_lookup = {step.id: step for step in pipeline.steps}
        remaining_deps: Dict[str, Set[str]] = {
            step.id: set(step.depends_on) for step in pipeline.steps
        }
        side_effect_order: List[str] = [
            step.id
            for step in pipeline.steps
            if (step.step_type or "").lower() in {"qc", "export"}
            or (step.component.type or "").lower() in {"qc", "export"}
        ]
        next_side_effect_idx = 0
        dependents: Dict[str, List[str]] = defaultdict(list)

        for step in pipeline.steps:
            for dep in step.depends_on:
                if dep not in step_lookup:
                    raise ValueError(f"Step '{step.id}' depends on unknown step '{dep}'")
                dependents[dep].append(step.id)

        ready: List[str] = [sid for sid, deps in remaining_deps.items() if not deps]
        ready.sort(key=lambda sid: order_index[sid])

        scheduled: Set[str] = set()

        def add_ready(step_id: str) -> None:
            if step_id in scheduled or step_id in ready:
                return
            ready.append(step_id)
            ready.sort(key=lambda sid: order_index[sid])

        def mark_complete(step_id: str, result: Any) -> None:
            results[step_id] = result
            scheduled.add(step_id)
            for child in dependents.get(step_id, []):
                remaining_deps[child].discard(step_id)
                if not remaining_deps[child]:
                    add_ready(child)

        def run_step(step_id: str) -> Any:
            step = step_lookup[step_id]
            params = {**step.params}
            params.update(runtime_params)

            func = self.registry.resolve_callable(step.component.name)
            log.info(
                "Executing step %s using component %s (type=%s)",
                step.id,
                step.component.name,
                step.component.type,
            )
            return func(**params) if params else func()

        def is_side_effecting(step_id: str) -> bool:
            step = step_lookup[step_id]
            step_type = (step.step_type or "").lower()
            component_type = (step.component.type or "").lower()
            return step_type in {"qc", "export"} or component_type in {"qc", "export"}

        with ThreadPoolExecutor(max_workers=self.max_workers or len(pipeline.steps)) as executor:
            futures: Dict[Any, str] = {}

            while len(results) < len(pipeline.steps):
                progress_made = False

                # Schedule all ready steps that are not side-effecting
                normal_ready: List[str] = []
                side_effect_ready: List[str] = []
                blocked_side_effects: List[str] = []

                for step_id in list(ready):
                    ready.remove(step_id)
                    if is_side_effecting(step_id):
                        if (
                            next_side_effect_idx < len(side_effect_order)
                            and side_effect_order[next_side_effect_idx] == step_id
                        ):
                            side_effect_ready.append(step_id)
                        else:
                            # Keep later side-effect steps pending until their turn
                            blocked_side_effects.append(step_id)
                    else:
                        normal_ready.append(step_id)

                for step_id in normal_ready:
                    if step_id in scheduled:
                        continue
                    scheduled.add(step_id)
                    futures[executor.submit(run_step, step_id)] = step_id
                    progress_made = True

                side_effect_ready.sort(key=lambda sid: order_index[sid])
                while side_effect_ready:
                    step_id = side_effect_ready.pop(0)
                    if step_id in scheduled:
                        continue
                    scheduled.add(step_id)
                    result = run_step(step_id)
                    mark_complete(step_id, result)
                    next_side_effect_idx += 1
                    progress_made = True

                    if next_side_effect_idx < len(side_effect_order):
                        next_id = side_effect_order[next_side_effect_idx]
                        if next_id in ready:
                            ready.remove(next_id)
                            side_effect_ready.append(next_id)

                for step_id in blocked_side_effects:
                    add_ready(step_id)

                if futures:
                    done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                    for future in done:
                        step_id = futures.pop(future)
                        result = future.result()
                        mark_complete(step_id, result)
                        progress_made = True

                if not progress_made:
                    if blocked_side_effects and not futures:
                        expected = (
                            side_effect_order[next_side_effect_idx]
                            if next_side_effect_idx < len(side_effect_order)
                            else None
                        )
                        raise RuntimeError(
                            "Pipeline %s is stuck; waiting on side-effect '%s' but only later side-effects are ready"
                            % (pipeline.name, expected)
                        )
                    if not ready and len(results) < len(pipeline.steps):
                        unresolved = [sid for sid, deps in remaining_deps.items() if deps]
                        raise RuntimeError(
                            f"Pipeline {pipeline.name} is stuck; unresolved dependencies: {unresolved}"
                        )

        return results
