"""
Pipeline Graph Module

Provides graph data structure and algorithms for pipeline dependency management.
Handles topological sorting, cycle detection, and graph visualization.

Author: Scraper Platform Team
"""

import logging
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Graph node types."""
    STEP = "step"
    PROCESSOR = "processor"
    GATE = "gate"
    MERGER = "merger"


@dataclass
class GraphNode:
    """Graph node representation."""

    id: str
    node_type: NodeType
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.node_type.value,
            "data": self.data,
            "metadata": self.metadata
        }


@dataclass
class GraphEdge:
    """Graph edge representation."""

    source: str
    target: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "weight": self.weight,
            "metadata": self.metadata
        }


class DirectedGraph:
    """
    Directed graph for pipeline dependency management.

    Features:
    - Node and edge management
    - Topological sorting
    - Cycle detection
    - Path finding
    - Graph traversal
    """

    def __init__(self, name: str = "graph"):
        """
        Initialize directed graph.

        Args:
            name: Graph name
        """
        self.name = name
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency_list: Dict[str, List[str]] = {}
        logger.debug(f"Initialized DirectedGraph: {name}")

    def add_node(self, node: GraphNode) -> None:
        """
        Add a node to the graph.

        Args:
            node: Node to add
        """
        self.nodes[node.id] = node
        if node.id not in self.adjacency_list:
            self.adjacency_list[node.id] = []
        logger.debug(f"Added node: {node.id}")

    def add_edge(self, edge: GraphEdge) -> None:
        """
        Add an edge to the graph.

        Args:
            edge: Edge to add
        """
        # Ensure nodes exist
        if edge.source not in self.nodes or edge.target not in self.nodes:
            raise ValueError(f"Edge nodes must exist: {edge.source} -> {edge.target}")

        self.edges.append(edge)
        self.adjacency_list[edge.source].append(edge.target)
        logger.debug(f"Added edge: {edge.source} -> {edge.target}")

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get node by ID."""
        return self.nodes.get(node_id)

    def get_successors(self, node_id: str) -> List[str]:
        """Get successor nodes."""
        return self.adjacency_list.get(node_id, [])

    def get_predecessors(self, node_id: str) -> List[str]:
        """Get predecessor nodes."""
        predecessors = []
        for source, targets in self.adjacency_list.items():
            if node_id in targets:
                predecessors.append(source)
        return predecessors

    def topological_sort(self) -> List[str]:
        """
        Perform topological sort using Kahn's algorithm.

        Returns:
            Ordered list of node IDs

        Raises:
            ValueError: If graph contains cycle
        """
        # Calculate in-degrees
        in_degree = {node_id: 0 for node_id in self.nodes}
        for source, targets in self.adjacency_list.items():
            for target in targets:
                in_degree[target] += 1

        # Find nodes with no incoming edges
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            # Process successors
            for successor in self.adjacency_list.get(current, []):
                in_degree[successor] -= 1
                if in_degree[successor] == 0:
                    queue.append(successor)

        # Check if all nodes processed
        if len(result) != len(self.nodes):
            raise ValueError("Graph contains a cycle")

        return result

    def detect_cycle(self) -> Optional[List[str]]:
        """
        Detect cycle in graph using DFS.

        Returns:
            Cycle path if found, None otherwise
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for successor in self.adjacency_list.get(node_id, []):
                if successor not in visited:
                    if dfs(successor):
                        return True
                elif successor in rec_stack:
                    # Found cycle
                    path.index(successor)
                    return True

            path.pop()
            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return path

        return None

    def find_path(self, source: str, target: str) -> Optional[List[str]]:
        """
        Find path between two nodes using BFS.

        Args:
            source: Source node ID
            target: Target node ID

        Returns:
            Path as list of node IDs, or None if no path exists
        """
        if source not in self.nodes or target not in self.nodes:
            return None

        queue = [(source, [source])]
        visited = {source}

        while queue:
            current, path = queue.pop(0)

            if current == target:
                return path

            for successor in self.adjacency_list.get(current, []):
                if successor not in visited:
                    visited.add(successor)
                    queue.append((successor, path + [successor]))

        return None

    def get_roots(self) -> List[str]:
        """Get root nodes (no predecessors)."""
        roots = []
        for node_id in self.nodes:
            if not self.get_predecessors(node_id):
                roots.append(node_id)
        return roots

    def get_leaves(self) -> List[str]:
        """Get leaf nodes (no successors)."""
        leaves = []
        for node_id in self.nodes:
            if not self.get_successors(node_id):
                leaves.append(node_id)
        return leaves

    def to_dict(self) -> Dict[str, Any]:
        """Convert graph to dictionary."""
        return {
            "name": self.name,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "node_count": len(self.nodes),
            "edge_count": len(self.edges)
        }


class PipelineGraph(DirectedGraph):
    """
    Specialized graph for pipeline dependency management.

    Extends DirectedGraph with pipeline-specific functionality.
    """

    def __init__(self, pipeline_name: str):
        """
        Initialize pipeline graph.

        Args:
            pipeline_name: Pipeline name
        """
        super().__init__(name=pipeline_name)
        self.pipeline_name = pipeline_name

    def add_step(
        self,
        step_name: str,
        depends_on: Optional[List[str]] = None,
        **metadata
    ) -> None:
        """
        Add a step to the pipeline graph.

        Args:
            step_name: Step name
            depends_on: List of dependency step names
            **metadata: Additional metadata
        """
        # Add node
        node = GraphNode(
            id=step_name,
            node_type=NodeType.STEP,
            metadata=metadata
        )
        self.add_node(node)

        # Add dependency edges
        if depends_on:
            for dep in depends_on:
                edge = GraphEdge(source=dep, target=step_name)
                self.add_edge(edge)

    def get_execution_order(self) -> List[str]:
        """
        Get step execution order.

        Returns:
            Ordered list of step names
        """
        try:
            return self.topological_sort()
        except ValueError as e:
            logger.error(f"Cannot determine execution order: {e}")
            cycle = self.detect_cycle()
            if cycle:
                logger.error(f"Cycle detected: {' -> '.join(cycle)}")
            raise

    def get_parallel_groups(self) -> List[List[str]]:
        """
        Get groups of steps that can run in parallel.

        Returns:
            List of groups (each group can run in parallel)
        """
        execution_order = self.get_execution_order()
        groups: List[List[str]] = []
        processed: Set[str] = set()

        for step_name in execution_order:
            # Check if all dependencies are processed
            deps = self.get_predecessors(step_name)
            if all(dep in processed for dep in deps):
                # Can start with current group or new group
                if not groups or any(dep in groups[-1] for dep in deps):
                    # Need new group
                    groups.append([step_name])
                else:
                    # Can add to current group
                    groups[-1].append(step_name)

            processed.add(step_name)

        return groups
