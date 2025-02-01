from typing import List, Callable, Optional, Any
from pydantic import BaseModel, Field, model_validator
from scrapybara.anthropic import Anthropic
from scrapybara.prompts import UBUNTU_SYSTEM_PROMPT
from scrapybara.types.act import Message
from .util import pretty_print_step
import random

AGENT_COLORS = ["91", "92", "93", "94", "95", "96"]  # red, green, yellow, blue, purple, cyan

class Agent(BaseModel):
    """A wrapper around Scrapybara's client.act parameters with additional swarm-specific fields"""
    # Swarm-specific fields
    name: str = "Agent"
    instance: Optional[str] = "shared"  # Track which Scrapybara instance this agent uses
    color: Optional[str] = random.choice(AGENT_COLORS)
    orchestrator: bool = False
    
    # client.act parameters
    model: Anthropic = Field(default_factory=Anthropic)
    tools: List[Any] = Field(default_factory=list)  # List of tool instances
    system: str = UBUNTU_SYSTEM_PROMPT
    prompt: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)  # Agent's conversation history
    schema: Optional[Any] = None  # Type for structured output
    on_step: Optional[Callable] = None
    
    @model_validator(mode='after')
    def setup_defaults(self) -> 'Agent':
        """Set up default on_step function and orchestrator system prompt"""
        if self.on_step is None:
            self.on_step = lambda step: pretty_print_step(step, self.color)
            
        return self

class Response(BaseModel):
    messages: List[Message] = []
    agent: Optional[Agent] = None
    context_variables: dict = {}
    steps: List = []  # Track Scrapybara execution steps
    usage: Optional[dict] = None  # Track token usage
    output: Optional[Any] = None  # For schema-based structured output

def get_orchestrator_prompt(agents: List['Agent']) -> str:
    agent_info = "\n".join([
        f"  - {a.name}: {a.prompt}"
        for a in agents if not a.orchestrator
    ])
    
    return f"""You are the Orchestrator Agent, the central coordinator of a swarm of AI agents working together on computer tasks. You will be given a task and a list of agents with their capabilities. Your role is to:

1. TASK ANALYSIS & DELEGATION
- Break down complex tasks into smaller, manageable subtasks
- Identify which specialized agent is best suited for each subtask based on their name and prompt
- Maintain awareness of each agent's capabilities and current status

2. COORDINATION & OVERSIGHT
- Monitor task progress through agent communications
- Handle handoff requests between agents
- Ensure tasks are completed efficiently and in the correct order
- Prevent redundant work or conflicts between agents

3. COMMUNICATION PROTOCOL
- When receiving a task, first analyze and break it down
- For each subtask, specify:
  * The exact prompt/instructions for the agent
  * Required tools and resources
  * Expected outcomes and success criteria
  * Dependencies on other subtasks

4. DECISION MAKING
- When handling handoff requests, consider:
  * The requesting agent's reason for handoff
  * The suggested agent's suitability
  * Current workload of all agents
  * Task dependencies and priorities

5. PROBLEM SOLVING
- Identify potential bottlenecks or conflicts
- Suggest alternative approaches when agents face difficulties
- Adapt the task distribution based on agent feedback

<AGENTS>
{agent_info}
</AGENTS>

For each task, you must output a structured plan using the Orchestrator schema, which includes:
- The overall task description
- Specific task assignments for each agent, including:
  * The exact prompt/instructions
  * Priority level
- Any additional execution notes or coordination requirements

Remember: You are the orchestrator of the swarm. Your decisions should optimize for efficient task completion while maintaining clear communication and coordination between all agents."""
