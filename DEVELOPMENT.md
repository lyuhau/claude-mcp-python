# Development Guide

This document contains implementation details, design decisions, and development guidelines for the Claude REPL server.

## Architecture Overview

### Tool Framework
- All tools inherit from `BaseTool`
- MCP (Model Context Protocol) integration for Claude Desktop
- Standard output formatting via `CodeOutput` class
- Consistent error handling patterns

### Python Tools

#### One-off Python (`PythonTool`)
- Uses fresh globals dict each time
- Built-in pandas/pyarrow lazy imports
- Tries eval() first, falls back to exec()
- Captures stdout/stderr via StringIO
- Timing info included by default

Design decisions:
- Fresh environment each time for predictability
- Basic imports available but lazy-loaded
- Simple output capture over process isolation
- No persistent state to avoid memory leaks

#### Session Python (`PythonSessionTool`)
- Uses InteractiveInterpreter for REPL-like experience
- Session timeout after 5 minutes of inactivity
- Background cleanup of expired sessions
- Full traceback for better error messages

Design decisions:
- Session-based for data analysis workflows
- Timeout to prevent resource exhaustion
- Async cleanup to avoid blocking operations
- Better error handling for interactive use

### Shell Tools

#### Command Execution (`ShellTool`)
- 5-second threshold for async mode
- Task-based management system
- Automatic process cleanup
- Working directory validation

Design choices:
- Short timeout favors responsiveness
- Task system allows progress tracking
- Async design prevents blocking
- Safety checks before execution

#### Status Tool (`ShellStatusTool`)
- Smart polling with 100ms intervals
- Up to 5-second wait per check
- Detailed status information
- Execution time tracking

Rationale:
- Quick polling for responsiveness
- Reasonable wait time for results
- Comprehensive status info for monitoring
- Time tracking for performance analysis

### File Tools

#### Perl Tool (`PerlTool`)
- Uses temp files for script execution
- UTF-8 handling built-in
- Optional whitespace cleaning
- Pattern-based transformations

Key decisions:
- Temp files avoid shell escaping issues
- UTF-8 by default for modern text
- Whitespace cleaning for consistency
- Perl for powerful text processing

## Development Guidelines

### Code Style
- Double quotes for strings
- Trailing commas in multi-line structures
- No trailing whitespace (except Makefiles)
- Empty lines = single newline

### Error Handling
- Detailed error messages
- Proper exception types
- Clean resource handling
- Fail early and explicitly

### Performance
- Async for long operations
- Resource cleanup
- Memory usage monitoring
- Process management

### Testing
- Unit tests for tools
- Integration tests with Claude
- Performance benchmarks
- Security testing needed

## Future Improvements

### High Priority
1. Resource usage monitoring
2. Enhanced error recovery
3. Better session management
4. Process isolation

### Nice to Have
1. Task cancelation
2. More debugging tools
3. Configuration options
4. Additional tool types

## Security Notes

- No global pip usage
- Virtual env required
- Working directory validation
- UTF-8 encoding enforced
- Resource limits needed
- Process isolation considerations

## Troubleshooting

Common issues and solutions:
1. Session timeouts
   - Check activity threshold
   - Verify cleanup tasks
2. Process hangs
   - Review timeout settings
   - Check resource usage
3. File encoding
   - Verify UTF-8 handling
   - Check input validation

## Release Process
1. Version bump
2. Changelog update
3. Test suite run
4. Documentation review
5. Security audit
6. Release notes

Remember: This doc is for developer context - keep user-facing docs simple!