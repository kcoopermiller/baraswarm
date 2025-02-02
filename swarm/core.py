# Standard library imports
import copy
from typing import List, Optional, Dict, Any, Deque
from collections import deque

# Package/library imports
from scrapybara import Scrapybara
from scrapybara.tools import BashTool, ComputerTool, EditTool, BrowserTool
from scrapybara.core.api_error import ApiError
from scrapybara.types.act import Message

# Local imports
from .util import debug_print
from .types import Agent, Response, get_orchestrator_prompt
from .tools import HandoffTool, OrchestratorSchema

class Swarm:
    def __init__(self, agents: List[Agent], api_key: Optional[str] = None):
        self.client = Scrapybara(api_key=api_key)
        self.instances: Dict[str, any] = {}  # Track active Scrapybara instances
        self.agents = agents
        
        orchestrator = [agent for agent in agents if agent.orchestrator]
        match len(orchestrator):
            case 0:
                raise ValueError("Swarm requires exactly one orchestrator agent")
            case 1:
                self.orchestrator = orchestrator[0]
                self.orchestrator.schema = OrchestratorSchema
                self.orchestrator.system = get_orchestrator_prompt(self.agents)
            case _:
                raise ValueError("Cannot have multiple orchestrator agents")
        
        self.message_queue: Deque[dict] = deque()  # Queue for inter-agent messages

    def __del__(self):
        """Clean up all Scrapybara instances"""
        for instance in self.instances.values():
            try:
                instance.browser.stop()
                instance.stop()
            except ApiError as e:
                print(f"Error {e.status_code}: {e.body}")
        self.instances.clear()

    def _get_or_create_instance(self, agent: Agent) -> any:
        """Get existing instance or create new one for agent"""
        if agent.instance in self.instances:
            return self.instances[agent.instance]
            
        try:
            if agent.instance == "shared":
                instance = self.client.start_ubuntu(timeout_hours=1)
            else:
                try:
                    instance = next(
                        inst for inst in self.client.get_instances()
                        if inst.id == agent.instance
                    )
                except StopIteration:
                    print(f"Instance {agent.instance} not found, falling back to shared instance")
                    agent.instance = "shared"
                    # Get or create shared instance
                    if "shared" in self.instances:
                        return self.instances["shared"]
                    instance = self.client.start_ubuntu(timeout_hours=1)
            # instance.browser.start()
            self.instances[agent.instance] = instance
            return instance
        except ApiError as e:
            print(f"Error {e.status_code}: {e.body}")
            raise e

    # TODO: change to use new tool system
    def _setup_agent_tools(self, agent: Agent, instance: any) -> List:
        """Setup agent tools, ensuring HandoffTool is always included"""
        handoff_tool = HandoffTool(instance, self, agent)
        
        # If user provided tools, add HandoffTool if not already present
        if agent.tools:
            if not any(isinstance(tool, HandoffTool) for tool in agent.tools):
                agent.tools.append(handoff_tool)
            return agent.tools
            
        # Otherwise use all default tools
        return [
            BashTool(instance),
            ComputerTool(instance),
            EditTool(instance),
            # BrowserTool(instance),
            handoff_tool,
        ]

    def get_act_completion(
        self,
        agent: Agent,
        messages: Optional[List[Message]] = None,
        debug: bool = False,
    ):
        """Get a completion from the agent"""
        instance = self._get_or_create_instance(agent)
        tools = self._setup_agent_tools(agent, instance)

        response = self.client.act(
            model=agent.model,
            tools=tools,
            system=agent.system,
            prompt=agent.prompt,
            messages=messages if messages else [],
            schema=agent.schema,
            on_step=agent.on_step,
        )

        # If this is the orchestrator and we got a plan, update agent prompts
        if agent.orchestrator and response.output:
            for assignment in response.output.task_assignments:
                target_agent = next(
                    (a for a in self.agents if a.name == assignment.agent_name),
                    None
                )
                if target_agent:
                    target_agent.prompt = assignment.prompt

        return response

    def run(
        self,
        agent: Agent,
        messages: Optional[List[Message]] = None,
        prompt: Optional[str] = None,
        context_variables: dict = {},
        debug: bool = False,
        max_turns: int = float("inf"),
    ) -> Response:
        if not agent.orchestrator:
            raise ValueError("Only the orchestrator agent can be used with run(). Other agents should be coordinated through the orchestrator agent.")
            
        active_agent = agent
        context_variables = copy.deepcopy(context_variables)
        messages = copy.deepcopy(messages) if messages else []
        init_len = len(messages)
        all_steps = []

        if prompt:
            active_agent.prompt = prompt
        
        # TODO: change loop so it stops when the orchestrator has decided to stop
        while len(messages) - init_len < max_turns and active_agent:
            completion = self.get_act_completion(
                agent=active_agent,
                messages=messages,
                debug=debug,
            )
            
            debug_print(debug, "Received completion:", completion)
            # TODO: update agent switching and async handling
            # messages.extend(completion.messages)
            # all_steps.extend(completion.steps)

        return Response(
            messages=messages[init_len:],
            agent=active_agent,
            context_variables=context_variables,
            steps=all_steps,
            usage=completion.usage if hasattr(completion, 'usage') else None,
            output=completion.output if hasattr(completion, 'output') else None,
        )
