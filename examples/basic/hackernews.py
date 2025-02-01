from swarm import Swarm
from swarm.types import Agent
from scrapybara.anthropic import Anthropic

# Initialize the swarm
swarm = Swarm(api_key="your_api_key")

# Create an agent with direct client.act parameters
agent = Agent(
    name="Browser Agent",
    model=Anthropic(api_key="your_api_key"),
    system="You are a browser automation expert. Help navigate and interact with web pages.",
    prompt="Go to news.ycombinator.com and get the top 3 posts"
)

# Run the agent
try:
    response = swarm.run(agent, debug=True)
    print(f"Messages: {response.messages}")
    print(f"Steps: {response.steps}")
    print(f"Output: {response.output}")
finally:
    # Clean up resources
    del swarm

# Example with schema and messages
from pydantic import BaseModel
from typing import List

class HNPost(BaseModel):
    title: str
    url: str
    points: int

class HNSchema(BaseModel):
    posts: List[HNPost]

agent = Agent(
    name="HN Scraper",
    model=Anthropic(),
    system="You are a web scraping expert.",
    messages=[
        {"role": "user", "content": "Get the top 3 posts from Hacker News"}
    ],
    schema=HNSchema
)

response = swarm.run(agent)
posts = response.output.posts  # Typed output!