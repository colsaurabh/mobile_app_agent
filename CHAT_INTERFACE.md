# Chat Interface for Mobile App Agent

## Overview
The desktop chat interface provides a real-time view of the conversation between the AI agent and human user during mobile app automation tasks.

## Features
- **Real-time Updates**: See agent actions and decisions as they happen
- **Visual Context**: Screenshots displayed alongside actions
- **Conversation History**: Complete chat history maintained throughout the session
- **Message Types**: Different colors and icons for different message types:
  - 🤖 Agent messages (blue)
  - 👤 Human responses (purple)
  - ⚙️ System notifications (orange)
  - 🎯 Actions (green)
  - 💭 Thinking/reasoning (brown, italic)
  - ❌ Errors (red)

## Setup

### 1. Install Dependencies
```bash
pip install pillow
```

### 2. Enable Chat Interface
In your `config.yaml`, set:
```yaml
ENABLE_CHAT_INTERFACE: true
CHAT_SHOW_SCREENSHOTS: true  # Optional: show screenshot info
CHAT_SHOW_DETAILED_ACTIONS: true  # Optional: show detailed agent reasoning
```

### 3. Run the Agent
```bash
python scripts/task_executor.py --app your_app_name
```

The chat interface window will automatically open when the agent starts.

## Usage

1. **Start the Agent**: Run the task executor as normal
2. **Chat Window**: A desktop window will open showing the conversation
3. **Real-time Updates**: Watch the agent's thought process and actions
4. **Human Interaction**: When the agent asks questions, your responses appear in the chat
5. **Human Override**: Press the pipe key `|` to trigger human intervention (if enabled)

## Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `ENABLE_CHAT_INTERFACE` | Enable/disable the chat interface | `true` |
| `CHAT_SHOW_SCREENSHOTS` | Show screenshot filenames in chat | `true` |
| `CHAT_SHOW_DETAILED_ACTIONS` | Show agent's observation, thought, action breakdown | `true` |

## Message Types

The chat interface displays different types of messages:

- **System Messages**: Agent startup, round transitions, errors
- **Agent Messages**: Agent's observations, thoughts, and planned actions
- **Human Messages**: Task descriptions and responses to agent questions
- **Action Messages**: Specific actions being performed (tap, swipe, text input)
- **Thinking Messages**: Agent's reasoning and analysis
- **Error Messages**: When actions fail or invalid inputs are provided

## Benefits

1. **Transparency**: See exactly what the agent is thinking and doing
2. **Debugging**: Easier to identify where issues occur
3. **Learning**: Understand how the agent makes decisions
4. **Monitoring**: Keep track of progress without watching logs
5. **Interaction**: Better context for human override situations

## Technical Details

- Built with tkinter (no external GUI dependencies)
- Runs in a separate thread to avoid blocking the main agent
- Uses message queues for thread-safe communication
- Automatically scrolls to show latest messages
- Gracefully handles interface initialization failures

## Troubleshooting

**Chat window doesn't open:**
- Check that `ENABLE_CHAT_INTERFACE: true` in config.yaml
- Ensure pillow is installed: `pip install pillow`
- Check for error messages in the console

**Missing messages:**
- Verify the configuration settings are correct
- Check that the agent is running properly

**Window closes unexpectedly:**
- The chat window automatically closes when the agent session ends
- Check the main agent logs for any errors