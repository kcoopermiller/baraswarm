import json
from datetime import datetime

def pretty_print_step(step, color: str) -> None:
    # Print the step text if available
    if step.text:
        print(f"\033[{color}mAssistant\033[0m: {step.text}")
    
    # Print any tool calls
    if step.tool_calls:
        if len(step.tool_calls) > 1:
            print()
        for tool_call in step.tool_calls:
            name = tool_call.tool_name
            args_str = json.dumps(tool_call.args).replace(":", "=")
            print(f"\033[{color}m{name}\033[0m({args_str[1:-1]})")

def debug_print(debug: bool, *args: str) -> None:
    if not debug:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = " ".join(map(str, args))
    print(f"\033[97m[\033[90m{timestamp}\033[97m]\033[90m {message}\033[0m")
