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
from .tools import HandoffTool

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

    def process_handoff_requests(self) -> None:
        """Process any pending handoff requests in the queue"""
        if not self.message_queue or not self.orchestrator:
            return

        # Process each request in the queue
        while self.message_queue:
            request = self.message_queue.popleft()
            if request["type"] != "handoff_request":
                continue

            # Create a message for the orchestrator agent
            orchestrator_message = {
                "role": "user",
                "content": f"""Handoff request from {request['from_agent']}:
                Reason: {request['reason']}
                Task: {request['task_description']}
                Suggested Agent: {request['suggested_agent'] or 'None'}
                Requires Response: {request['requires_response']}
                Additional Context: {request['context']}
                
                Available Agents: {[a.name for a in self.agents if not a.orchestrator]}
                
                Please decide how to handle this request. You can:
                1. Assign it to the suggested agent
                2. Assign it to a different agent
                3. Tell the original agent to continue
                4. Put the task on hold pending other work
                """
            }

            # Get orchestrator agent's decision
            response = self.get_act_completion(
                agent=self.orchestrator,
                messages=[orchestrator_message],
            )

            # TODO: Process orchestrator agent's response and update task assignments

    def get_act_completion(
        self,
        agent: Agent,
        messages: Optional[List[Message]] = None,
        debug: bool = False,
    ):
        """Get a completion from the agent"""
        instance = self._get_or_create_instance(agent)
        tools = self._setup_agent_tools(agent, instance)
        
        # Process any pending handoffs before getting completion
        if not agent.orchestrator:
            self.process_handoff_requests()

        # If this is the orchestrator, use the dynamic prompt with agent information
        system = agent.system
        if agent.orchestrator:
            system = get_orchestrator_prompt(self.agents)

        response = self.client.act(
            model=agent.model,
            tools=tools,
            system=system,
            prompt=agent.prompt,
            messages=messages if messages else [],
            schema=agent.schema,
            on_step=agent.on_step,
        )

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
        
        while len(messages) - init_len < max_turns and active_agent:
            completion = self.get_act_completion(
                agent=active_agent,
                messages=messages,
                debug=debug,
            )
            
            debug_print(debug, "Received completion:", completion)
            messages.extend(completion.messages)
            all_steps.extend(completion.steps)

        return Response(
            messages=messages[init_len:],
            agent=active_agent,
            context_variables=context_variables,
            steps=all_steps,
            usage=completion.usage if hasattr(completion, 'usage') else None,
            output=completion.output if hasattr(completion, 'output') else None,
        )
