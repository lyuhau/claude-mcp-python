import asyncio
import logging
import tempfile
import os
import time
from typing import List

import mcp.types as types

from repl.tools.base import BaseTool, CodeOutput

logger = logging.getLogger('perl_tool')

class PerlTool(BaseTool):
    """Efficient file modification tool using Perl.
    
    This tool provides a safer and more efficient way to modify files using Perl's 
    powerful text processing capabilities. It avoids shell escaping issues by writing
    the Perl script to a temporary file and handles UTF-8 encoding by default.
    
    Example usage:
    ```
    # Simple text replacement
    perl_script = '''
    $content =~ s/old/new/g;
    '''
    
    # Complex multi-line replacement
    perl_script = '''
    $content =~ s/(Start.*?\n).*?(End)/\1New content\n\2/s;
    '''
    ```
    """
    
    @property
    def name(self) -> str:
        return "perl"

    @property
    def description(self) -> str:
        return """Modify files using Perl's text processing capabilities.
        
The tool automatically adds strict mode, warnings, and UTF-8 handling.
The input file content is available in the $content variable.
Write your Perl substitutions and the modified content will be written back.

Example Perl patterns:
- Simple replace: $content =~ s/old/new/g;
- Add after match: $content =~ s/(### Header)/$1\\n\\nNew stuff/;
- Multi-line replace: $content =~ s/old chunk.*?next chunk/new/s;
- Between markers: $content =~ s/(?<=after).*?(?=before)/new/s;
- Insert at line: $content =~ s/^((?:.*\\n){42})/\\1New line 43\\n/;
"""

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to modify"
                },
                "perl_script": {
                    "type": "string",
                    "description": "Perl substitution commands to apply (without boilerplate)"
                }
            },
            "required": ["file_path", "perl_script"]
        }

    async def execute(self, arguments: dict) -> List[types.TextContent]:
        file_path = arguments.get("file_path")
        perl_script = arguments.get("perl_script")
        
        if not os.path.exists(file_path):
            raise ValueError(f"File does not exist: {file_path}")
            
        # Create temporary directory for our script
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, "modify.pl")
            
            # Write the Perl script with all necessary boilerplate
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(f"""#!/usr/bin/env perl
use strict;
use warnings;
no warnings 'uninitialized';
use utf8;
binmode(STDIN, ':utf8');
binmode(STDOUT, ':utf8');
local $/;
my $content = <>;

{perl_script}

$content =~ s/[ \t]+$//mg;

print $content;
""")
            
            # Make script executable
            os.chmod(script_path, 0o755)
            
            output = CodeOutput()
            start_time = time.time()
            
            try:
                # Run the Perl script and capture output
                process = await asyncio.create_subprocess_exec(
                    script_path,
                    stdin=open(file_path, "r", encoding="utf-8"),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0 or (stderr and b"Wide character" in stderr):  # Accept wide character warnings
                    modified_content = stdout.decode("utf-8")
                    if modified_content:
                        # Write content back to original file
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(modified_content)
                        output.stdout = "File modified successfully"
                    else:
                        output.stderr = "Error: Perl script produced empty output"
                        output.result = 1
                else:
                    output.stderr = stderr.decode("utf-8")
                    output.result = process.returncode
                
            except Exception as e:
                output.stderr = f"Error executing Perl script: {str(e)}"
                output.result = 1
            finally:
                output.execution_time = time.time() - start_time
            
            return output.format_output()