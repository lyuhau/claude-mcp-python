# Claude REPL Server

A Python-based REPL (Read-Eval-Print Loop) server for Claude that provides Python execution, shell command execution, and session management capabilities. Built using the Model Context Protocol (MCP) for seamless integration with Claude.

## Overview

This project implements a REPL server that allows Claude to:
- Execute Python code in both isolated and session-based environments
- Run shell commands with automatic async fallback for long-running operations
- Maintain persistent Python interpreter sessions
- Handle both quick commands and long-running processes safely

## Key Features

### 1. Shell Command Execution with Smart Async Fallback

The shell tool (`ShellTool`) provides a transparent way to execute shell commands with automatic async fallback for long-running operations:

- Commands that complete within 5 seconds return results immediately
- Longer-running commands automatically switch to async mode
- Async mode provides task IDs for status checking
- Built-in timeout handling prevents server crashes
- Standard Python logging for debugging

Example usage:
```python
# Quick command (< 5s)
> shell execute: echo "Hello" && sleep 2
Standard Output: Hello
Execution time: 2.003 seconds

# Long running command (> 5s)
> shell execute: ./scripts/deploy.sh
Task started with ID: b8764e23-2134-40f2-b9ae-25c29620c54a

> shell_status: b8764e23-2134-40f2-b9ae-25c29620c54a
Status: completed
Execution time: 7.710 seconds
...
```

### 2. Python Code Execution

Two complementary Python execution tools:

#### One-off Python Execution (`PythonTool`)
- Fresh environment for each execution
- Sandboxed environment with basic built-ins
- Perfect for quick calculations and tests
- Clean isolation between runs

#### Persistent Python Sessions (`PythonSessionTool`)
- Maintains state between executions
- Sessions persist for 5 minutes of inactivity
- Ideal for interactive data analysis
- Supports incremental development
- Full access to interpreter features

## Technical Details

### Architecture

The server is built on several key components:

1. **Base Tool Framework** (`BaseTool`)
   - Abstract base class for all tools
   - Standardizes tool interface
   - Handles MCP integration

2. **Shell Execution System**
   - Transparent async fallback
   - Task management and status tracking
   - Process monitoring and cleanup
   - Standard Python logging

3. **Python Execution Systems**
   - Sandboxed one-off execution
   - Session-based persistent execution
   - Memory and resource management
   - Output capture and formatting

### Command Execution Flow

1. Command is received through the shell tool
2. Tool begins execution and starts timing
3. If command completes within 5 seconds:
   - Results are returned immediately
   - Process is cleaned up
4. If command exceeds 5 seconds:
   - Switches to async mode
   - Returns task ID
   - Continues execution in background
   - Status can be checked with up to 5s wait time

### Session Management

Python sessions are managed with several key features:
- Unique session IDs
- 5-minute inactivity timeout
- Automatic cleanup of expired sessions
- State preservation between executions
- Resource cleanup on shutdown

## Development Considerations

### Error Handling

The system includes comprehensive error handling:
- Process execution errors
- Timeouts and long-running processes
- Resource cleanup
- Session management
- Invalid commands or arguments

### Logging

Standard Python logging is used for debugging:
- Command execution details
- Process creation and completion
- Execution times and status changes
- Errors and exceptions
- Session creation and cleanup

### Performance

Several performance considerations are built in:
- Automatic async fallback for long operations
- Smart polling with reasonable timeouts
- Resource cleanup and management
- Session timeout handling
- Process monitoring and cleanup

## Future Improvements

Potential areas for enhancement:
1. Advanced task management features (cancel, pause, resume)
2. Resource usage monitoring and limits
3. More sophisticated session management
4. Enhanced error recovery mechanisms
5. Additional debugging tools
6. Configurable logging options

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -e .
   ```

## Integration with Claude Desktop

The REPL server needs to be configured in Claude Desktop's configuration file. The exact configuration depends on your operating system:

### Windows with WSL (Windows Subsystem for Linux)
```json
{
  "mcpServers": {
    "repl": {
      "command": "wsl",
      "args": [
        "--exec",
        "bash",
        "-c",
        "/path/to/your/python/environment/bin/python -m repl"
      ]
    }
  }
}
```

### macOS or Linux
```json
{
  "mcpServers": {
    "repl": {
      "command": "/path/to/your/python/environment/bin/python",
      "args": ["-m", "repl"]
    }
  }
}
```

### Windows (Native)
```json
{
  "mcpServers": {
    "repl": {
      "command": "C:\\Path\\To\\Your\\Python\\Environment\\python.exe",
      "args": ["-m", "repl"]
    }
  }
}
```

Add this configuration to your Claude Desktop config file, adjusting paths according to your environment. The config file location varies by operating system:
- Windows: `%APPDATA%/AnthropicClaude/config.json`
- macOS: `~/Library/Application Support/AnthropicClaude/config.json`
- Linux: `~/.config/AnthropicClaude/config.json`

## Using the REPL Server

Once configured, the following tools will be available in Claude:
- `shell`: Execute shell commands
- `shell_status`: Check status of long-running commands
- `python`: Execute one-off Python code
- `python_session`: Execute Python code in persistent sessions

## Contributing

Contributions are welcome! Please feel free to submit pull requests with improvements or bug fixes.

## License

[Add appropriate license information]