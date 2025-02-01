from typing import Any, Optional, List
from pydantic import BaseModel
from scrapybara.tools import Tool
from scrapybara.client import UbuntuInstance

class OrchestratorSchema(BaseModel):
    """The orchestrator's structured plan for task distribution"""
    class TaskAssignment(BaseModel):
        agent_name: str
        prompt: str
        priority: int = 1  # Higher number = higher priority
    overall_task: str  # The original task being broken down
    task_assignments: List[TaskAssignment]  # List of assignments for each agent
    execution_notes: str  # Any additional notes about task execution or coordination

# class HandoffParameters(BaseModel):
#     reason: str  # Why the agent wants to hand off the task
#     suggested_agent: Optional[str] = None  # Name of suggested agent to handle the task
#     task_description: str  # Description of the task to be handed off
#     requires_response: bool = False  # Whether the agent needs a response from the task
#     context: Optional[dict] = None  # Any additional context needed for the task

# class HandoffTool(Tool):
#     _instance: UbuntuInstance
#     _swarm: Any  # Reference to the Swarm instance
#     _agent: Any  # Reference to the current agent

#     def __init__(self, instance: UbuntuInstance, swarm: Any, agent: Any) -> None:
#         super().__init__(
#             name="handoff",
#             description="Hand off a task to another agent or notify the orchestrator agent about task status. Use this when you think another agent would be better suited for the current task, or when you need to coordinate with other agents.",
#             parameters=HandoffParameters,
#         )
#         self._instance = instance
#         self._swarm = swarm
#         self._agent = agent

#     def __call__(self, **kwargs: Any) -> Any:
#         params = HandoffParameters(**kwargs)
        
#         # If this is the orchestrator agent, we shouldn't allow handoffs
#         if self._agent.orchestrator:
#             return {
#                 "status": "error",
#                 "message": "Orchestrator agent cannot hand off tasks"
#             }

#         # Find the orchestrator agent
#         orchestrator_agent = next(
#             (agent for agent in self._swarm.agents if agent.orchestrator),
#             None
#         )
        
#         if not orchestrator_agent:
#             return {
#                 "status": "error",
#                 "message": "No orchestrator agent found in the swarm"
#             }

#         # Create a handoff request message
#         handoff_request = {
#             "type": "handoff_request",
#             "from_agent": self._agent.name,
#             "reason": params.reason,
#             "suggested_agent": params.suggested_agent,
#             "task_description": params.task_description,
#             "requires_response": params.requires_response,
#             "context": params.context or {}
#         }

#         # Add the request to the swarm's message queue
#         self._swarm.message_queue.append(handoff_request)

#         return {
#             "status": "success",
#             "message": f"Task handoff request sent to orchestrator agent",
#             "request": handoff_request
#         } 