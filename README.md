<div id="toc" align="center">
  <ul style="list-style: none">
    <summary>
      <h1><img src="https://github.com/user-attachments/assets/5c96e78f-b3ea-4714-beaf-e2afcfc1a405" width="30"> Capyswarm <img src="https://github.com/user-attachments/assets/04379257-2e36-4e09-b084-65257f132eac" alt="Scrapybara" width="30"></h1>
    </summary>
  </ul>
</div>

<p align="center">
  A lightweight multi-agent orchestration framework for Scrapybara computer-use agents built on top of OpenAI's Swarm.
</p>
<p align="center">
  <a href="https://github.com/kcoopermiller/baraswarm/blob/main/LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/license-MIT-blue" /></a>
  <a href="https://discord.gg/s4bPUVFXqA"><img alt="Discord" src="https://img.shields.io/badge/Discord-Join%20the%20community-yellow.svg?logo=discord" /></a>
</p>

> [!NOTE]
> This is a work in progress and is not yet ready for production use. Also, while the API is similar to OpenAI's Swarm, the underlying implementation has been almost entirely rewritten.

## Install

Requires Python 3.12+

```shell
pip install git+ssh://git@github.com/kcoopermiller/capyswarm.git
```

or

```shell
pip install git+https://github.com/kcoopermiller/capyswarm.git
```

## Usage

```python
from capyswarm import Swarm, Agent

client = Swarm()

def transfer_to_agent_b():
    return agent_b


agent_a = Agent(
    name="Agent A",
    instructions="You are a helpful agent.",
    functions=[transfer_to_agent_b],
)

agent_b = Agent(
    name="Agent B",
    instructions="Only speak in Haikus.",
)

response = client.run(
    agent=agent_a,
    messages=[{"role": "user", "content": "I want to talk to agent B."}],
)

print(response.messages[-1]["content"])
```

```
Hope glimmers brightly,
New paths converge gracefully,
What can I assist?
```

### REPL

Use the `run_demo_loop` to run a REPL on your command line.

```python
from capyswarm.repl import run_demo_loop
...
run_demo_loop(client)
```

## Table of Contents

- [Overview](#overview)
- [Examples](#examples)
- [Documentation (WIP)](#documentation)
  - [Running Swarm](#running-swarm)
  - [Agents](#agents)
  - [Functions](#functions)
- [Evaluations](#evaluations)

# Overview

Swarm focuses on making agent **coordination** and **execution** lightweight, highly controllable, and easily testable.

In the OpenAI Swarm framework, this is achieved through two core abstractions: `Agent`s and **handoffs**. An `Agent` encompasses `instructions` and `tools`, and can at any point choose to hand off a conversation to another `Agent`. Handoffs occur synchronously, ensuring controlled transitions between agents.

Capyswarm introduces an **orchestrator-worker** architecture. Instead of direct agent-to-agent handoffs, all task delegation is routed through a central `Orchestrator`. The `Orchestrator` decomposes high-level tasks, assigns subtasks to individual agents, and manages asynchronous execution. Agents can still transfer tasks to others, but only via the orchestrator, ensuring structured coordination.

Additionally, agents can retrieve relevant information about each other's progress, enabling more informed decision-making. Once all assigned tasks are completed, the Orchestrator aggregates the results and determines whether the user's request has been successfully fulfilled.

All interactions between the user and agents are mediated by the `Orchestrator`, maintaining a streamlined and coherent workflow.

![Swarm Diagram](https://www.anthropic.com/_next/image?url=https%3A%2F%2Fwww-cdn.anthropic.com%2Fimages%2F4zrzovbb%2Fwebsite%2F8985fc683fae4780fb34eab1365ab78c7e51bc8e-2401x1000.png&w=3840&q=75)  
*Image source: [Building effective agents](https://www.anthropic.com/research/building-effective-agents)*

# Examples

Check out `/examples` for inspiration! Learn more about each one in its README.

- [`basic`](examples/basic): Simple examples of fundamentals like setup, function calling, handoffs, and context variables
- [`fireboy_and_watergirl`](examples/fireboy_and_watergirl): An example of two agents playing [Fireboy and Watergirl](https://www.coolmathgames.com/0-fireboy-and-water-girl-in-the-forest-temple)

# Documentation

> [!IMPORTANT]
> This section is a work in progress and is mostly copied from the OpenAI Swarm docs.

## Running Swarm

Start by instantiating a Swarm client (which internally instantiates a `Scrapybara` client).

```python
from swarm import Swarm

client = Swarm()
```

### `client.run()`

Swarm's `run()` function is analogous to the `client.act()` function in the [Scrapybara Act SDK](https://docs.scrapybara.com/act-sdk) – it takes a `model` that serves as the base LLM for the agent, `tools` that enable agents to interact with the computer, a `prompt` that should denote the agent’s current objective, and starts an interaction loop that continues until the agent achieves the user's objective.

At its core, Swarm's `client.run()` implements the following loop: TODO

#### Arguments

| Argument              | Type    | Description                                                                                                                                            | Default        |
| --------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------- |
| **agent**             | `Agent` | The (initial) agent to be called.                                                                                                                      | (required)     |
| **prompt**            | `str`   | Objective                                                                                                                                              | (required)     |
| **debug**             | `bool`  | If `True`, enables debug logging                                                                                                                       | `False`        |



**OUTDATED**

Once `client.run()` is finished (after potentially multiple calls to agents and tools) it will return a `Response` containing all the relevant updated state. Specifically, the new `messages`, the last `Agent` to be called, and the most up-to-date `context_variables`. You can pass these values (plus new user messages) in to your next execution of `client.run()` to continue the interaction where it left off – much like `chat.completions.create()`. (The `run_demo_loop` function implements an example of a full execution loop in `/swarm/repl/repl.py`.)

#### `Response` Fields

| Field                 | Type    | Description                                                                                                                                                                                                                                                                  |
| --------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **messages**          | `List`  | A list of message objects generated during the conversation. Very similar to [Chat Completions `messages`](https://platform.openai.com/docs/api-reference/chat/create#chat-create-messages), but with a `sender` field indicating which `Agent` the message originated from. |
| **agent**             | `Agent` | The last agent to handle a message.                                                                                                                                                                                                                                          |
| **context_variables** | `dict`  | The same as the input variables, plus any changes.                                                                                                                                                                                                                           |

**OUTDATED_END**

## Agents

An `Agent` simply encapsulates a set of `instructions` with a set of `functions` (plus some additional settings below), and has the capability to hand off execution to another `Agent`.

While it's tempting to personify an `Agent` as "someone who does X", it can also be used to represent a very specific workflow or step defined by a set of `instructions` and `functions` (e.g. a set of steps, a complex retrieval, single step of data transformation, etc). This allows `Agent`s to be composed into a network of "agents", "workflows", and "tasks", all represented by the same primitive.

## `Agent` Fields

| Field            | Type                             | Description                                                                   | Default                                          |
| ---------------- | -------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------ |
| **name**         | `str`                            | The name of the agent.                                                        | `"Agent"`                                        |
| **instance**     | `str`                            | The Scrapybara instance this agent uses.                                      | `"shared"`                                       |
| **color**        | `str`                            | Terminal Color                                                                | `random.choice(["91","92","93","94","95","96"])` |
| **orchestrator** | `bool`                           | True if this agent is orchestrator                                            | `False`                                          |
| **model**        | `scrapybara.anthropic.Anthropic` | The model to be used by the agent.                                            | `scrapybara.anthropic.Anthropic`                 |
| **tool**         | `list`                           | List of tools available to agent                                              | check [_setup_agent_tools](https://github.com/kcoopermiller/baraswarm/blob/main/swarm/core.py#L75)                                                                                                                 |
| **system**        | `str`                           | System prompt                                                                 | `scrapybara.prompts.UBUNTU_SYSTEM_PROMPT`        |
| **prompt**        | `str`                           | Description of preferred Agent objective                                      | `None`                                           |
| **messages**      | `List`                          | A list of `scrapybara.types.act.Message` objects                              | `None`                                           |
| **schema**        | `Any`                           | [Structured output](https://docs.scrapybara.com/act-sdk#structured-output)    | `None`                                           |
| **on_step**       | `Callable`                      | What to print after one iteration                                             | [pretty_print_step](https://github.com/kcoopermiller/baraswarm/blob/main/swarm/util.py#L4) |



ANYTHING BELOW THIS IS NOT DONE

### Instructions

`Agent` `instructions` are directly converted into the `system` prompt of a conversation (as the first message). Only the `instructions` of the active `Agent` will be present at any given time (e.g. if there is an `Agent` handoff, the `system` prompt will change, but the chat history will not.)

```python
agent = Agent(
   instructions="You are a helpful agent."
)
```

The `instructions` can either be a regular `str`, or a function that returns a `str`. The function can optionally receive a `context_variables` parameter, which will be populated by the `context_variables` passed into `client.run()`.

```python
def instructions(context_variables):
   user_name = context_variables["user_name"]
   return f"Help the user, {user_name}, do whatever they want."

agent = Agent(
   instructions=instructions
)
response = client.run(
   agent=agent,
   messages=[{"role":"user", "content": "Hi!"}],
   context_variables={"user_name":"John"}
)
print(response.messages[-1]["content"])
```

```
Hi John, how can I assist you today?
```

## Functions

- Swarm `Agent`s can call python functions directly.
- Function should usually return a `str` (values will be attempted to be cast as a `str`).
- If a function returns an `Agent`, execution will be transferred to that `Agent`.
- If a function defines a `context_variables` parameter, it will be populated by the `context_variables` passed into `client.run()`.

```python
def greet(context_variables, language):
   user_name = context_variables["user_name"]
   greeting = "Hola" if language.lower() == "spanish" else "Hello"
   print(f"{greeting}, {user_name}!")
   return "Done"

agent = Agent(
   functions=[greet]
)

client.run(
   agent=agent,
   messages=[{"role": "user", "content": "Usa greet() por favor."}],
   context_variables={"user_name": "John"}
)
```

```
Hola, John!
```

- If an `Agent` function call has an error (missing function, wrong argument, error) an error response will be appended to the chat so the `Agent` can recover gracefully.
- If multiple functions are called by the `Agent`, they will be executed in that order.

### Handoffs and Updating Context Variables

An `Agent` can hand off to another `Agent` by returning it in a `function`.

```python
sales_agent = Agent(name="Sales Agent")

def transfer_to_sales():
   return sales_agent

agent = Agent(functions=[transfer_to_sales])

response = client.run(agent, [{"role":"user", "content":"Transfer me to sales."}])
print(response.agent.name)
```

```
Sales Agent
```

It can also update the `context_variables` by returning a more complete `Result` object. This can also contain a `value` and an `agent`, in case you want a single function to return a value, update the agent, and update the context variables (or any subset of the three).

```python
sales_agent = Agent(name="Sales Agent")

def talk_to_sales():
   print("Hello, World!")
   return Result(
       value="Done",
       agent=sales_agent,
       context_variables={"department": "sales"}
   )

agent = Agent(functions=[talk_to_sales])

response = client.run(
   agent=agent,
   messages=[{"role": "user", "content": "Transfer me to sales"}],
   context_variables={"user_name": "John"}
)
print(response.agent.name)
print(response.context_variables)
```

```
Sales Agent
{'department': 'sales', 'user_name': 'John'}
```

> [!NOTE]
> If an `Agent` calls multiple functions to hand-off to an `Agent`, only the last handoff function will be used.

### Function Schemas

Swarm automatically converts functions into a JSON Schema that is passed into Chat Completions `tools`.

- Docstrings are turned into the function `description`.
- Parameters without default values are set to `required`.
- Type hints are mapped to the parameter's `type` (and default to `string`).
- Per-parameter descriptions are not explicitly supported, but should work similarly if just added in the docstring. (In the future docstring argument parsing may be added.)

```python
def greet(name, age: int, location: str = "New York"):
   """Greets the user. Make sure to get their name and age before calling.

   Args:
      name: Name of the user.
      age: Age of the user.
      location: Best place on earth.
   """
   print(f"Hello {name}, glad you are {age} in {location}!")
```

```javascript
{
   "type": "function",
   "function": {
      "name": "greet",
      "description": "Greets the user. Make sure to get their name and age before calling.\n\nArgs:\n   name: Name of the user.\n   age: Age of the user.\n   location: Best place on earth.",
      "parameters": {
         "type": "object",
         "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "location": {"type": "string"}
         },
         "required": ["name", "age"]
      }
   }
}
```

# Evaluations

TODO: create example evals. Check `weather_agent` and `triage_agent` in OpenAI Swarm for example

