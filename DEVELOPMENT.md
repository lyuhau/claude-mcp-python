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
- Placeholder support for pandas/pyarrow (not yet implemented)
- Tries eval() first, falls back to exec()
- Captures stdout/stderr via StringIO
- Timing info included by default

Design decisions:
- Fresh environment each time for predictability
- Simple output capture over process isolation
- No persistent state to avoid memory leaks

#### Session Python (`PythonSessionTool`)
- Uses InteractiveInterpreter for REPL-like experience
- Session timeout after 5 minutes of inactivity
- Background cleanup of expired sessions
- Full traceback for better error messages
- Separate stdout/stderr capture per session

Design decisions:
- Session-based for data analysis workflows
- Timeout to prevent resource exhaustion
- Async cleanup to avoid blocking operations
- Better error handling for interactive use

### Shell Tools

#### Command Execution (`ShellTool`)
- 4.9-second threshold for async mode
- Task-based management system
- Automatic process cleanup
- Working directory validation
- Separate subprocess pipes for stdout/stderr

Design choices:
- Short timeout favors responsiveness
- Task system allows progress tracking
- Async design prevents blocking
- Safety checks before execution

#### Status Tool (`ShellStatusTool`)
- Smart polling with 100ms intervals
- Up to 5-second wait per check
- Detailed status information
- Execution time and running time tracking

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
- Safe temporary file cleanup

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

### Performance Considerations
- Async for long operations
- Resource cleanup
- Process management
- Separate output handlers for stdout/stderr
- Task-based long-running processes

## Future Improvements

### High Priority
1. Implement pandas/pyarrow imports in PythonTool
2. Add process isolation
3. Add resource usage monitoring
4. Add task cancellation support

### Infrastructure Needed
1. Test suite setup
2. CI/CD pipeline
3. Documentation automation
4. Performance benchmarks

## Security Notes

- No global pip usage
- Virtual env required
- Working directory validation
- UTF-8 encoding enforced
- Resource limits needed
- Process isolation needed

## Troubleshooting

Common issues and solutions:
1. Session timeouts
   - Check activity threshold (should be 300 seconds)
   - Verify cleanup tasks running properly
   - Check interpreter disposal
2. Process hangs
   - Review timeout settings (4.9s threshold)
   - Check subprocess management
   - Verify async task cleanup
3. File encoding
   - UTF-8 handling is automatic
   - Check input validation
   - Verify temp file cleanup

## Release Process
1. Version bump in pyproject.toml
2. Update CHANGELOG.md
3. Documentation review
4. Security review
5. Release notes
6. Tag version in git

Remember: This doc is for developer context - keep user-facing docs simple!