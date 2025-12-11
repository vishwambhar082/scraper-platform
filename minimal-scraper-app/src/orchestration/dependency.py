"""
Dependency planner for multi-stage scraper workflows.
"""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, Iterable, List, Sequence


class DependencyPlanner:
    def __init__(self, edges: Sequence[tuple[str, str]]) -> None:
        self.graph: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = defaultdict(int)
        for upstream, downstream in edges:
            self.graph[upstream].append(downstream)
            self.in_degree[downstream] += 1
            self.in_degree.setdefault(upstream, 0)

    def topological_order(self) -> List[str]:
        queue = deque(node for node, degree in self.in_degree.items() if degree == 0)
        order: List[str] = []
        indegree = dict(self.in_degree)
        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in self.graph.get(node, []):
                indegree[neighbor] -= 1
                if indegree[neighbor] == 0:
                    queue.append(neighbor)
        if len(order) != len(indegree):
            raise ValueError("Cycle detected in dependency graph")
        return order

