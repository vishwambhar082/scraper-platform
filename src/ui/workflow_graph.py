"""
Workflow graph visualization widget.

Displays the pipeline workflow as a visual graph with nodes and edges.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PySide6.QtWidgets import QWidget

from src.pipeline import CompiledPipeline


class WorkflowGraphWidget(QWidget):
    """Widget for visualizing pipeline workflows as a graph."""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.pipeline: Optional[CompiledPipeline] = None
        self.node_positions: Dict[str, QPointF] = {}
        self.setMinimumSize(400, 300)
        self.setStyleSheet("background-color: #1e1e1e;")
    
    def set_pipeline(self, pipeline: CompiledPipeline) -> None:
        """Set the pipeline to visualize."""
        self.pipeline = pipeline
        self._calculate_layout()
        self.update()

    def refresh(self) -> None:
        """Recompute layout and repaint."""
        self._calculate_layout()
        self.update()
    
    def _calculate_layout(self) -> None:
        """Calculate node positions for the graph layout."""
        if not self.pipeline:
            return
        
        # Simple hierarchical layout
        nodes = {step.id: step for step in self.pipeline.steps}
        levels: Dict[int, List[str]] = {}
        
        # Calculate levels (topological order)
        def get_level(node_id: str, visited: set) -> int:
            if node_id in visited:
                return 0
            visited.add(node_id)
            
            if node_id not in nodes:
                return 0
            
            step = nodes[node_id]
            if not step.depends_on:
                return 0
            
            max_dep_level = max(get_level(dep, visited) for dep in step.depends_on)
            return max_dep_level + 1
        
        for step_id in nodes.keys():
            level = get_level(step_id, set())
            if level not in levels:
                levels[level] = []
            levels[level].append(step_id)
        
        # Position nodes
        self.node_positions = {}
        h_spacing = 150
        v_spacing = 100
        
        for level, step_ids in sorted(levels.items()):
            y = 50 + level * v_spacing
            total_width = len(step_ids) * h_spacing
            start_x = (self.width() - total_width) / 2 if self.width() > 0 else 100
            
            for i, step_id in enumerate(step_ids):
                x = start_x + i * h_spacing
                self.node_positions[step_id] = QPointF(x, y)
    
    def paintEvent(self, event) -> None:
        """Paint the workflow graph."""
        if not self.pipeline:
            painter = QPainter(self)
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.drawText(self.rect(), Qt.AlignCenter, "No pipeline loaded")
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw edges first (so they appear behind nodes)
        self._draw_edges(painter)
        
        # Draw nodes
        self._draw_nodes(painter)
    
    def _draw_edges(self, painter: QPainter) -> None:
        """Draw edges between nodes."""
        if not self.pipeline:
            return
        
        pen = QPen(QColor(100, 100, 100), 2)
        painter.setPen(pen)
        
        for step in self.pipeline.steps:
            if step.id not in self.node_positions:
                continue
            
            start_pos = self.node_positions[step.id]
            
            for dep_id in step.depends_on:
                if dep_id not in self.node_positions:
                    continue
                
                end_pos = self.node_positions[dep_id]
                
                # Draw arrow
                painter.drawLine(
                    int(end_pos.x() + 60), int(end_pos.y() + 30),
                    int(start_pos.x()), int(start_pos.y() + 30)
                )
    
    def _draw_nodes(self, painter: QPainter) -> None:
        """Draw nodes in the graph."""
        if not self.pipeline:
            return
        
        node_width = 120
        node_height = 60
        
        for step in self.pipeline.steps:
            if step.id not in self.node_positions:
                continue
            
            pos = self.node_positions[step.id]
            rect = QRectF(pos.x(), pos.y(), node_width, node_height)
            
            # Node color based on status
            status_color = QColor(70, 130, 180)  # Default blue
            brush = QBrush(status_color)
            painter.setBrush(brush)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawRoundedRect(rect, 5, 5)
            
            # Node text
            painter.setPen(QPen(QColor(255, 255, 255)))
            font = QFont()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, step.id)

