"""
Minimal agent runtime for desktop app.

Manages agent state and execution with human-in-the-loop.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from threading import RLock

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent execution states."""
    IDLE = "idle"
    THINKING = "thinking"
    WAITING_APPROVAL = "waiting_approval"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ApprovalRequired(Exception):
    """Exception raised when human approval is required."""
    pass


@dataclass
class AgentAction:
    """Action proposed by agent."""
    action_id: str
    action_type: str
    description: str
    parameters: Dict[str, Any]
    risk_level: str  # 'low', 'medium', 'high'
    requires_approval: bool
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved: Optional[bool] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None


@dataclass
class AgentExecution:
    """Agent execution context."""
    agent_id: str
    task: str
    state: AgentState
    started_at: datetime
    finished_at: Optional[datetime] = None
    actions: List[AgentAction] = field(default_factory=list)
    current_action: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class AgentRuntime:
    """
    Minimal agent runtime with human oversight.

    Features:
    - State management
    - Human-in-the-loop approvals
    - Action history
    - Safe execution
    """

    def __init__(self):
        """Initialize agent runtime."""
        self._lock = RLock()
        self._executions: Dict[str, AgentExecution] = {}
        self._approval_callbacks: List[Callable[[AgentAction], bool]] = []

    def start_execution(
        self,
        agent_id: str,
        task: str
    ) -> AgentExecution:
        """
        Start agent execution.

        Args:
            agent_id: Agent identifier
            task: Task description

        Returns:
            Execution context
        """
        with self._lock:
            execution = AgentExecution(
                agent_id=agent_id,
                task=task,
                state=AgentState.IDLE,
                started_at=datetime.utcnow()
            )

            self._executions[agent_id] = execution
            logger.info(f"Agent execution started: {agent_id}")

            return execution

    def propose_action(
        self,
        agent_id: str,
        action_type: str,
        description: str,
        parameters: Dict[str, Any],
        risk_level: str = 'low',
        requires_approval: bool = None
    ) -> AgentAction:
        """
        Propose action for execution.

        Args:
            agent_id: Agent identifier
            action_type: Type of action
            description: Action description
            parameters: Action parameters
            risk_level: Risk assessment
            requires_approval: Require human approval (auto if risk high)

        Returns:
            Created action

        Raises:
            ApprovalRequired: If action requires approval
        """
        with self._lock:
            execution = self._executions.get(agent_id)
            if not execution:
                raise RuntimeError(f"Agent not executing: {agent_id}")

            # Auto-require approval for high-risk actions
            if requires_approval is None:
                requires_approval = risk_level == 'high'

            action = AgentAction(
                action_id=f"action-{len(execution.actions)}",
                action_type=action_type,
                description=description,
                parameters=parameters,
                risk_level=risk_level,
                requires_approval=requires_approval
            )

            execution.actions.append(action)
            execution.current_action = action.action_id

            # Change state
            if requires_approval:
                execution.state = AgentState.WAITING_APPROVAL
                logger.info(f"Action requires approval: {action.action_id}")
                raise ApprovalRequired(action.action_id)
            else:
                execution.state = AgentState.EXECUTING

            return action

    def approve_action(
        self,
        agent_id: str,
        action_id: str,
        approved_by: str = "user"
    ):
        """
        Approve pending action.

        Args:
            agent_id: Agent identifier
            action_id: Action identifier
            approved_by: User who approved
        """
        with self._lock:
            execution = self._executions.get(agent_id)
            if not execution:
                return

            action = next((a for a in execution.actions if a.action_id == action_id), None)
            if not action:
                return

            action.approved = True
            action.approved_at = datetime.utcnow()
            action.approved_by = approved_by

            execution.state = AgentState.EXECUTING

            logger.info(f"Action approved: {action_id} by {approved_by}")

    def reject_action(
        self,
        agent_id: str,
        action_id: str,
        rejected_by: str = "user"
    ):
        """
        Reject pending action.

        Args:
            agent_id: Agent identifier
            action_id: Action identifier
            rejected_by: User who rejected
        """
        with self._lock:
            execution = self._executions.get(agent_id)
            if not execution:
                return

            action = next((a for a in execution.actions if a.action_id == action_id), None)
            if not action:
                return

            action.approved = False
            action.approved_at = datetime.utcnow()
            action.approved_by = rejected_by

            execution.state = AgentState.STOPPED

            logger.info(f"Action rejected: {action_id} by {rejected_by}")

    def complete_execution(
        self,
        agent_id: str,
        result: Any = None
    ):
        """
        Mark execution as completed.

        Args:
            agent_id: Agent identifier
            result: Execution result
        """
        with self._lock:
            execution = self._executions.get(agent_id)
            if not execution:
                return

            execution.state = AgentState.COMPLETED
            execution.finished_at = datetime.utcnow()
            execution.result = result

            logger.info(f"Agent execution completed: {agent_id}")

    def fail_execution(
        self,
        agent_id: str,
        error: str
    ):
        """
        Mark execution as failed.

        Args:
            agent_id: Agent identifier
            error: Error message
        """
        with self._lock:
            execution = self._executions.get(agent_id)
            if not execution:
                return

            execution.state = AgentState.FAILED
            execution.finished_at = datetime.utcnow()
            execution.error = error

            logger.error(f"Agent execution failed: {agent_id} - {error}")

    def get_execution(self, agent_id: str) -> Optional[AgentExecution]:
        """Get execution context."""
        with self._lock:
            return self._executions.get(agent_id)

    def get_pending_approvals(self) -> List[tuple[str, AgentAction]]:
        """
        Get all pending approval actions.

        Returns:
            List of (agent_id, action) tuples
        """
        with self._lock:
            pending = []

            for agent_id, execution in self._executions.items():
                if execution.state == AgentState.WAITING_APPROVAL:
                    for action in execution.actions:
                        if action.requires_approval and action.approved is None:
                            pending.append((agent_id, action))

            return pending

    def get_stats(self) -> Dict[str, Any]:
        """Get runtime statistics."""
        with self._lock:
            by_state = {}
            for state in AgentState:
                by_state[state.value] = len([
                    e for e in self._executions.values()
                    if e.state == state
                ])

            return {
                'total_executions': len(self._executions),
                'by_state': by_state,
                'pending_approvals': len(self.get_pending_approvals())
            }
