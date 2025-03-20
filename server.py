#!/usr/bin/env python3

import os
import json
import sys
import pathlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, TypedDict

from mcp.server.fastmcp import FastMCP, Context

# Create a FastMCP server instance
mcp = FastMCP("secure-filesystem-server")

# Command line argument parsing
if len(sys.argv) < 2:
    print("Usage: python filesystem_server.py <allowed-directory> [additional-directories...]", file=sys.stderr)
    sys.exit(1)

# Normalize all paths consistently
def normalize_path(p: str) -> str:
    return os.path.normpath(p)

def expand_home(filepath: str) -> str:
    if filepath.startswith('~/') or filepath == '~':
        return os.path.join(os.path.expanduser('~'), filepath[1:])
    return filepath

# Store allowed directories in normalized form
allowed_directories = [
    normalize_path(os.path.abspath(expand_home(dir)))
    for dir in sys.argv[1:]
]

# Validate that all directories exist and are accessible
for dir_path in sys.argv[1:]:
    expanded_path = expand_home(dir_path)
    try:
        stats = os.stat(expanded_path)
        if not os.path.isdir(expanded_path):
            print(f"Error: {dir_path} is not a directory", file=sys.stderr)
            sys.exit(1)
    except OSError as e:
        print(f"Error accessing directory {dir_path}: {e}", file=sys.stderr)
        sys.exit(1)

# Security utilities
async def validate_path(requested_path: str) -> str:
    """Validate and resolve file paths against allowed directories for security."""
    expanded_path = expand_home(requested_path)
    absolute = os.path.abspath(expanded_path)
    normalized_requested = normalize_path(absolute)
    
    # Check if path is within allowed directories
    is_allowed = any(normalized_requested.startswith(dir) for dir in allowed_directories)
    if not is_allowed:
        raise ValueError(f"Access denied - path outside allowed directories: {absolute} not in {', '.join(allowed_directories)}")
    
    # Handle symlinks by checking their real path
    try:
        real_path = os.path.realpath(absolute)
        normalized_real = normalize_path(real_path)
        is_real_path_allowed = any(normalized_real.startswith(dir) for dir in allowed_directories)
        if not is_real_path_allowed:
            raise ValueError("Access denied - symlink target outside allowed directories")
        return real_path
    except OSError:
        # For paths that don't exist yet, verify parent directory
        parent_dir = os.path.dirname(absolute)
        try:
            real_parent_path = os.path.realpath(parent_dir)
            normalized_parent = normalize_path(real_parent_path)
            is_parent_allowed = any(normalized_parent.startswith(dir) for dir in allowed_directories)
            if not is_parent_allowed:
                raise ValueError("Access denied - parent directory outside allowed directories")
            return absolute
        except OSError:
            raise ValueError(f"Parent directory does not exist: {parent_dir}")

async def get_file_stats(file_path: str) -> Dict[str, Union[int, str, bool]]:
    """Get detailed file information."""
    stats = os.stat(file_path)
    return {
        "size": stats.st_size,
        "created": datetime.fromtimestamp(stats.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
        "accessed": datetime.fromtimestamp(stats.st_atime).isoformat(),
        "isDirectory": os.path.isdir(file_path),
        "isFile": os.path.isfile(file_path),
        "permissions": oct(stats.st_mode)[-3:],
    }

async def search_files(
    root_path: str,
    pattern: str,
    exclude_patterns: Optional[List[str]] = None
) -> List[str]:
    """Search for files matching a pattern, with optional exclusions."""
    if exclude_patterns is None:
        exclude_patterns = []
    
    results = []
    
    for root, dirs, files in os.walk(root_path):
        # Check if we should process this directory based on exclude patterns
        try:
            # Validate each path before processing
            await validate_path(root)
            
            # Filter out directories in exclude list
            rel_path = os.path.relpath(root, root_path)
            dirs[:] = [d for d in dirs if not any(
                os.path.relpath(os.path.join(root, d), root_path).startswith(exclude_pattern)
                for exclude_pattern in exclude_patterns
            )]
            
            # Check all entries in this directory
            for name in dirs + files:
                full_path = os.path.join(root, name)
                try:
                    await validate_path(full_path)
                    if pattern.lower() in name.lower():
                        results.append(full_path)
                except ValueError:
                    # Skip invalid paths
                    continue
                    
        except ValueError:
            # Skip invalid paths
            continue
    
    return results

# Sequential Thinking Tool
class ThoughtData(TypedDict, total=False):
    thought: str
    thoughtNumber: int
    totalThoughts: int
    nextThoughtNeeded: bool
    isRevision: Optional[bool]
    revisesThought: Optional[int]
    branchFromThought: Optional[int]
    branchId: Optional[str]
    needsMoreThoughts: Optional[bool]

class SequentialThinkingServer:
    def __init__(self):
        self.thought_history = []
        self.branches = {}
    
    def validate_thought_data(self, data: Dict[str, Any]) -> ThoughtData:
        if not isinstance(data.get('thought'), str):
            raise ValueError('Invalid thought: must be a string')
        if not isinstance(data.get('thoughtNumber'), int):
            raise ValueError('Invalid thoughtNumber: must be a number')
        if not isinstance(data.get('totalThoughts'), int):
            raise ValueError('Invalid totalThoughts: must be a number')
        if not isinstance(data.get('nextThoughtNeeded'), bool):
            raise ValueError('Invalid nextThoughtNeeded: must be a boolean')
        
        return {
            'thought': data['thought'],
            'thoughtNumber': data['thoughtNumber'],
            'totalThoughts': data['totalThoughts'],
            'nextThoughtNeeded': data['nextThoughtNeeded'],
            'isRevision': data.get('isRevision'),
            'revisesThought': data.get('revisesThought'),
            'branchFromThought': data.get('branchFromThought'),
            'branchId': data.get('branchId'),
            'needsMoreThoughts': data.get('needsMoreThoughts')
        }
    
    def format_thought(self, thought_data: ThoughtData) -> str:
        """Format a thought with colored borders and context"""
        thought_num = thought_data['thoughtNumber']
        total = thought_data['totalThoughts']
        thought = thought_data['thought']
        is_revision = thought_data.get('isRevision', False)
        revises = thought_data.get('revisesThought')
        branch_from = thought_data.get('branchFromThought')
        branch_id = thought_data.get('branchId')
        
        # Create appropriate prefix and context
        if is_revision:
            prefix = "🔄 Revision"
            context = f" (revising thought {revises})"
        elif branch_from:
            prefix = "🌿 Branch"
            context = f" (from thought {branch_from}, ID: {branch_id})"
        else:
            prefix = "💭 Thought"
            context = ""
        
        header = f"{prefix} {thought_num}/{total}{context}"
        border_len = max(len(header), len(thought)) + 4
        border = "─" * border_len
        
        # Build the formatted output
        output = f"\n┌{border}┐\n"
        output += f"│ {header.ljust(border_len)} │\n"
        output += f"├{border}┤\n"
        output += f"│ {thought.ljust(border_len)} │\n"
        output += f"└{border}┘"
        
        return output
    
    def process_thought(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a thought and return the response"""
        try:
            validated_input = self.validate_thought_data(input_data)
            
            if validated_input['thoughtNumber'] > validated_input['totalThoughts']:
                validated_input['totalThoughts'] = validated_input['thoughtNumber']
            
            self.thought_history.append(validated_input)
            
            # Track branches if applicable
            if validated_input.get('branchFromThought') and validated_input.get('branchId'):
                branch_id = validated_input['branchId']
                if branch_id not in self.branches:
                    self.branches[branch_id] = []
                self.branches[branch_id].append(validated_input)
            
            # Format and log the thought
            formatted_thought = self.format_thought(validated_input)
            print(formatted_thought, file=sys.stderr)
            
            # Return response
            return {
                'thoughtNumber': validated_input['thoughtNumber'],
                'totalThoughts': validated_input['totalThoughts'],
                'nextThoughtNeeded': validated_input['nextThoughtNeeded'],
                'branches': list(self.branches.keys()),
                'thoughtHistoryLength': len(self.thought_history)
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'status': 'failed'
            }

# Create a single instance of the sequential thinking server
thinking_server = SequentialThinkingServer()

# Tool implementations
@mcp.tool()
async def read_file(path: str) -> str:
    """Read the complete contents of a file from the file system.
    
    Handles various text encodings and provides detailed error messages
    if the file cannot be read. Use this tool when you need to examine
    the contents of a single file. Only works within allowed directories.
    
    Args:
        path: The path to the file to read
    """
    valid_path = await validate_path(path)
    with open(valid_path, "r", encoding="utf-8") as f:
        return f.read()

@mcp.tool()
async def read_multiple_files(paths: List[str]) -> str:
    """Read the contents of multiple files simultaneously.
    
    This is more efficient than reading files one by one when you need to analyze
    or compare multiple files. Each file's content is returned with its
    path as a reference. Failed reads for individual files won't stop
    the entire operation. Only works within allowed directories.
    
    Args:
        paths: List of file paths to read
    """
    results = []
    
    for file_path in paths:
        try:
            valid_path = await validate_path(file_path)
            with open(valid_path, "r", encoding="utf-8") as f:
                content = f.read()
            results.append(f"{file_path}:\n{content}\n")
        except Exception as e:
            results.append(f"{file_path}: Error - {str(e)}")
    
    return "\n---\n".join(results)

@mcp.tool()
async def list_directory(path: str) -> str:
    """Get a detailed listing of all files and directories in a specified path.
    
    Results clearly distinguish between files and directories with [FILE] and [DIR]
    prefixes. This tool is essential for understanding directory structure and
    finding specific files within a directory. Only works within allowed directories.
    
    Args:
        path: Directory path to list
    """
    valid_path = await validate_path(path)
    entries = os.listdir(valid_path)
    formatted = []
    
    for entry in entries:
        entry_path = os.path.join(valid_path, entry)
        is_dir = os.path.isdir(entry_path)
        formatted.append(f"{'[DIR]' if is_dir else '[FILE]'} {entry}")
    
    return "\n".join(formatted)

@mcp.tool()
async def directory_tree(path: str) -> str:
    """Get a recursive tree view of files and directories as a JSON structure.
    
    Each entry includes 'name', 'type' (file/directory), and 'children' for directories.
    Files have no children array, while directories always have a children array (which may be empty).
    The output is formatted with 2-space indentation for readability. Only works within allowed directories.
    
    Args:
        path: Root directory path for the tree
    """
    valid_path = await validate_path(path)
    
    async def build_tree(current_path):
        entries = os.listdir(current_path)
        result = []
        
        for entry in entries:
            entry_path = os.path.join(current_path, entry)
            try:
                await validate_path(entry_path)
                is_dir = os.path.isdir(entry_path)
                
                entry_data = {
                    "name": entry,
                    "type": "directory" if is_dir else "file"
                }
                
                if is_dir:
                    entry_data["children"] = await build_tree(entry_path)
                
                result.append(entry_data)
            except ValueError:
                # Skip invalid paths
                continue
        
        return result
    
    tree_data = await build_tree(valid_path)
    return json.dumps(tree_data, indent=2)

@mcp.tool()
async def search_files_tool(path: str, pattern: str, exclude_patterns: Optional[List[str]] = None) -> str:
    """Recursively search for files and directories matching a pattern.
    
    Searches through all subdirectories from the starting path. The search
    is case-insensitive and matches partial names. Returns full paths to all
    matching items. Great for finding files when you don't know their exact location.
    Only searches within allowed directories.
    
    Args:
        path: Directory to start searching from
        pattern: Text pattern to search for in file/directory names
        exclude_patterns: Optional list of patterns to exclude from search
    """
    valid_path = await validate_path(path)
    results = await search_files(valid_path, pattern, exclude_patterns or [])
    return "\n".join(results) if results else "No matches found"

@mcp.tool()
async def get_file_info(path: str) -> str:
    """Retrieve detailed metadata about a file or directory.
    
    Returns comprehensive information including size, creation time, last modified time, permissions,
    and type. This tool is perfect for understanding file characteristics
    without reading the actual content. Only works within allowed directories.
    
    Args:
        path: Path to the file or directory
    """
    valid_path = await validate_path(path)
    info = await get_file_stats(valid_path)
    return "\n".join(f"{key}: {value}" for key, value in info.items())

@mcp.tool()
def list_allowed_directories() -> str:
    """Returns the list of directories that this server is allowed to access.
    
    Use this to understand which directories are available before trying to access files.
    """
    return f"Allowed directories:\n{os.linesep.join(allowed_directories)}"

@mcp.tool()
def sequentialthinking(
    thought: str,
    thoughtNumber: int,
    totalThoughts: int,
    nextThoughtNeeded: bool,
    isRevision: Optional[bool] = None,
    revisesThought: Optional[int] = None,
    branchFromThought: Optional[int] = None,
    branchId: Optional[str] = None,
    needsMoreThoughts: Optional[bool] = None
) -> str:
    """A detailed tool for dynamic and reflective problem-solving through thoughts.
    
    This tool helps analyze problems through a flexible thinking process that can adapt and evolve.
    Each thought can build on, question, or revise previous insights as understanding deepens.
    
    When to use this tool:
    - Breaking down complex problems into steps
    - Planning and design with room for revision
    - Analysis that might need course correction
    - Problems where the full scope might not be clear initially
    - Problems that require a multi-step solution
    - Tasks that need to maintain context over multiple steps
    - Situations where irrelevant information needs to be filtered out
    
    Args:
        thought: Your current thinking step
        thoughtNumber: Current number in sequence (can go beyond initial total if needed)
        totalThoughts: Current estimate of thoughts needed (can be adjusted up/down)
        nextThoughtNeeded: Whether another thought step is needed
        isRevision: Whether this revises previous thinking
        revisesThought: Which thought is being reconsidered
        branchFromThought: Branching point thought number
        branchId: Branch identifier
        needsMoreThoughts: If more thoughts are needed
    """
    input_data = {
        'thought': thought,
        'thoughtNumber': thoughtNumber,
        'totalThoughts': totalThoughts,
        'nextThoughtNeeded': nextThoughtNeeded
    }
    
    # Add optional parameters if provided
    if isRevision is not None:
        input_data['isRevision'] = isRevision
    if revisesThought is not None:
        input_data['revisesThought'] = revisesThought
    if branchFromThought is not None:
        input_data['branchFromThought'] = branchFromThought
    if branchId is not None:
        input_data['branchId'] = branchId
    if needsMoreThoughts is not None:
        input_data['needsMoreThoughts'] = needsMoreThoughts
    
    response = thinking_server.process_thought(input_data)
    return json.dumps(response, indent=2)

# Run the server
if __name__ == "__main__":
    print("Secure MCP Filesystem Server with Sequential Thinking running", file=sys.stderr)
    print(f"Allowed directories: {allowed_directories}", file=sys.stderr)
    mcp.run(transport='stdio')