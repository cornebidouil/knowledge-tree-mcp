#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["mcp>=0.3.0"]
# requires-python = ">=3.8"
# ///

"""
Code Knowledge Tree MCP Server
==============================

A tool-only MCP server for managing recursive code analysis and dependency trees.
Designed to help understand complex codebases by building a structured knowledge tree
of functions, modules, constants, and their interdependencies.

Core Philosophy:
- Simple JSON-based storage
- Tool-only architecture (no resources)
- Incremental knowledge building
- Clear dependency visualization
- Configurable working directory for knowledge tree storage

Usage:
  python code_knowledge_server.py [--working-dir <directory>]
  
  --working-dir: Base directory where the 'knowledge-tree' folder will be created
                 (default: current directory)

Examples:
  python code_knowledge_server.py
    # Creates: ./knowledge-tree/

  python code_knowledge_server.py --working-dir ./my_project_analysis
    # Creates: ./my_project_analysis/knowledge-tree/

  python code_knowledge_server.py --working-dir /absolute/path/to/base
    # Creates: /absolute/path/to/base/knowledge-tree/

The knowledge tree structure:
  <working-dir>/
  └── knowledge-tree/        # Always named 'knowledge-tree'
      ├── elements/          # Individual code element JSON files
      │   ├── element1.json
      │   ├── element2.json
      │   └── ...
      └── metadata.json      # Global metadata and statistics
"""

import json
import os
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("Code Knowledge Tree Server")

# Global configuration variables (will be set based on command line args)
KNOWLEDGE_BASE_DIR: Path = None
ELEMENTS_DIR: Path = None
METADATA_FILE: Path = None

@dataclass
class CodeElement:
    """Represents a code element in the knowledge tree"""
    id: str
    type: str  # "function", "module", "constant", "variable"
    code: str
    description: str
    dependencies: List[str]  # IDs of elements this depends on
    dependents: List[str]    # IDs of elements that depend on this
    source_file: Optional[str] = None
    line_range: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

def initialize_working_directory(working_dir: str = "."):
    """
    Initialize the global path configuration based on the working directory.
    Creates a 'knowledge-tree' subfolder inside the specified working directory.
    
    Args:
        working_dir: Base directory where the knowledge-tree folder should be created
    """
    global KNOWLEDGE_BASE_DIR, ELEMENTS_DIR, METADATA_FILE
    
    # The working directory is the base, and we create knowledge-tree inside it
    base_working_dir = Path(working_dir).resolve()
    KNOWLEDGE_BASE_DIR = base_working_dir / "knowledge-tree"
    ELEMENTS_DIR = KNOWLEDGE_BASE_DIR / "elements"
    METADATA_FILE = KNOWLEDGE_BASE_DIR / "metadata.json"
    
    # Ensure the directory structure exists
    ensure_knowledge_base()

def ensure_knowledge_base():
    """Ensure the knowledge base directory structure exists"""
    KNOWLEDGE_BASE_DIR.mkdir(exist_ok=True)
    ELEMENTS_DIR.mkdir(exist_ok=True)
    
    if not METADATA_FILE.exists():
        initial_metadata = {
            "created_at": datetime.now().isoformat(),
            "total_elements": 0,
            "last_updated": datetime.now().isoformat()
        }
        with open(METADATA_FILE, 'w') as f:
            json.dump(initial_metadata, f, indent=2)

def load_element(element_id: str) -> Optional[CodeElement]:
    """Load a code element from storage"""
    element_file = ELEMENTS_DIR / f"{element_id}.json"
    if not element_file.exists():
        return None
    
    with open(element_file, 'r') as f:
        data = json.load(f)
        return CodeElement(**data)

def save_element(element: CodeElement) -> bool:
    """Save a code element to storage"""
    ensure_knowledge_base()
    
    element.updated_at = datetime.now().isoformat()
    if not element.created_at:
        element.created_at = element.updated_at
    
    element_file = ELEMENTS_DIR / f"{element.id}.json"
    with open(element_file, 'w') as f:
        json.dump(asdict(element), f, indent=2)
    
    # Update metadata
    update_metadata()
    return True

def update_metadata():
    """Update global metadata"""
    element_count = len(list(ELEMENTS_DIR.glob("*.json")))
    metadata = {
        "total_elements": element_count,
        "last_updated": datetime.now().isoformat()
    }
    
    if METADATA_FILE.exists():
        with open(METADATA_FILE, 'r') as f:
            existing = json.load(f)
            metadata["created_at"] = existing.get("created_at", datetime.now().isoformat())
    
    with open(METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2)

def get_all_elements() -> List[CodeElement]:
    """Get all elements from the knowledge base"""
    elements = []
    for element_file in ELEMENTS_DIR.glob("*.json"):
        element_id = element_file.stem
        element = load_element(element_id)
        if element:
            elements.append(element)
    return elements

@mcp.tool()
def add_code_element(
    element_id: str,
    element_type: str,
    code: str,
    description: str,
    dependencies: List[str] = None,
    source_file: str = "",
    line_range: str = ""
) -> Dict[str, Any]:
    """
    Add a new code element to the knowledge tree.
    
    Args:
        element_id: Unique identifier for the element (e.g., "hr", "ge", "r5634")
        element_type: Type of element ("function", "module", "constant", "variable")
        code: The actual code content
        description: Human-readable description of what this element does
        dependencies: List of element IDs this element depends on (optional)
        source_file: Optional source file name
        line_range: Optional line range (e.g., "33490-33511")
    
    Returns:
        Success status, element info, and missing dependencies analysis
    """
    try:
        # Check if element already exists
        existing = load_element(element_id)
        if existing:
            return {
                "success": False,
                "message": f"Element '{element_id}' already exists. Use update_code_element to modify it.",
                "existing_element": {
                    "id": existing.id,
                    "type": existing.type,
                    "description": existing.description
                }
            }
        
        # Process dependencies
        deps_list = dependencies or []
        if isinstance(deps_list, str):
            # Handle single dependency passed as string
            deps_list = [deps_list]
        
        # Create new element
        element = CodeElement(
            id=element_id,
            type=element_type,
            code=code.strip(),
            description=description,
            dependencies=deps_list,
            dependents=[],
            source_file=source_file or None,
            line_range=line_range or None
        )
        
        # Save element
        save_element(element)
        
        # Update dependents in referenced elements and check for missing dependencies
        missing_dependencies = []
        existing_dependencies = []
        
        for dep_id in deps_list:
            dep_element = load_element(dep_id)
            if dep_element:
                # Add this element to the dependency's dependents list
                if element_id not in dep_element.dependents:
                    dep_element.dependents.append(element_id)
                    save_element(dep_element)
                existing_dependencies.append(dep_id)
            else:
                missing_dependencies.append(dep_id)
        
        return {
            "success": True,
            "message": f"Successfully added {element_type} '{element_id}'",
            "element": {
                "id": element.id,
                "type": element.type,
                "description": element.description,
                "dependencies": element.dependencies,
                "created_at": element.created_at
            },
            "dependency_analysis": {
                "total_dependencies": len(deps_list),
                "existing_dependencies": existing_dependencies,
                "missing_dependencies": missing_dependencies,
                "missing_count": len(missing_dependencies)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error adding element: {str(e)}"
        }

@mcp.tool()
def edit_dependencies(
    element_id: str,
    dependencies: List[str],
    operation: str = "replace"
) -> Dict[str, Any]:
    """
    Edit the dependency list of an existing element.
    
    Args:
        element_id: The element whose dependencies to modify
        dependencies: List of dependency element IDs
        operation: "replace" (default), "add", or "remove"
    
    Returns:
        Success status and updated dependency info
    """
    try:
        # Load the element
        element = load_element(element_id)
        if not element:
            return {
                "success": False,
                "message": f"Element '{element_id}' not found. Add it first with add_code_element."
            }
        
        # Process dependencies input
        if isinstance(dependencies, str):
            dependencies = [dependencies]
        
        # Store original dependencies for cleanup
        original_deps = element.dependencies.copy()
        
        # Perform the operation
        if operation == "replace":
            element.dependencies = dependencies
        elif operation == "add":
            for dep in dependencies:
                if dep not in element.dependencies:
                    element.dependencies.append(dep)
        elif operation == "remove":
            for dep in dependencies:
                if dep in element.dependencies:
                    element.dependencies.remove(dep)
        else:
            return {
                "success": False,
                "message": f"Invalid operation: {operation}. Use 'replace', 'add', or 'remove'."
            }
        
        # Save the updated element
        save_element(element)
        
        # Update dependents lists in affected elements
        # 1. Remove this element from old dependencies' dependents
        for old_dep in original_deps:
            if old_dep not in element.dependencies:  # Dependency was removed
                old_dep_element = load_element(old_dep)
                if old_dep_element and element_id in old_dep_element.dependents:
                    old_dep_element.dependents.remove(element_id)
                    save_element(old_dep_element)
        
        # 2. Add this element to new dependencies' dependents
        missing_dependencies = []
        existing_dependencies = []
        
        for dep_id in element.dependencies:
            dep_element = load_element(dep_id)
            if dep_element:
                if element_id not in dep_element.dependents:
                    dep_element.dependents.append(element_id)
                    save_element(dep_element)
                existing_dependencies.append(dep_id)
            else:
                missing_dependencies.append(dep_id)
        
        return {
            "success": True,
            "message": f"Successfully {operation}d dependencies for '{element_id}'",
            "element": {
                "id": element.id,
                "type": element.type,
                "description": element.description
            },
            "dependency_changes": {
                "operation": operation,
                "original_dependencies": original_deps,
                "new_dependencies": element.dependencies,
                "existing_dependencies": existing_dependencies,
                "missing_dependencies": missing_dependencies,
                "missing_count": len(missing_dependencies)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error editing dependencies: {str(e)}"
        }

@mcp.tool()
def get_element(element_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific code element and its information.
    
    Args:
        element_id: The ID of the element to retrieve
    
    Returns:
        Element details including code, dependencies, and metadata
    """
    try:
        element = load_element(element_id)
        if not element:
            return {
                "success": False,
                "message": f"Element '{element_id}' not found in knowledge tree"
            }
        
        return {
            "success": True,
            "element": {
                "id": element.id,
                "type": element.type,
                "description": element.description,
                "code": element.code,
                "dependencies": element.dependencies,
                "dependents": element.dependents,
                "source_file": element.source_file,
                "line_range": element.line_range,
                "created_at": element.created_at,
                "updated_at": element.updated_at
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving element: {str(e)}"
        }

@mcp.tool()
def find_missing_dependencies(element_id: str = "") -> Dict[str, Any]:
    """
    Find dependencies that are referenced but not yet defined in the knowledge tree.
    
    Args:
        element_id: Optional - check dependencies for specific element, or all if empty
    
    Returns:
        List of missing dependencies and their referencing elements
    """
    try:
        missing_deps = {}
        elements_to_check = []
        
        if element_id:
            # Check specific element
            element = load_element(element_id)
            if not element:
                return {
                    "success": False,
                    "message": f"Element '{element_id}' not found"
                }
            elements_to_check = [element]
        else:
            # Check all elements
            elements_to_check = get_all_elements()
        
        # Find missing dependencies
        all_element_ids = {elem.id for elem in get_all_elements()}
        
        for element in elements_to_check:
            for dep_id in element.dependencies:
                if dep_id not in all_element_ids:
                    if dep_id not in missing_deps:
                        missing_deps[dep_id] = []
                    missing_deps[dep_id].append({
                        "referencing_element": element.id,
                        "element_type": element.type,
                        "description": element.description
                    })
        
        return {
            "success": True,
            "missing_dependencies": missing_deps,
            "total_missing": len(missing_deps),
            "checked_elements": len(elements_to_check)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error finding missing dependencies: {str(e)}"
        }

@mcp.tool()
def get_knowledge_tree_view(root_element_id: str = "", max_depth: int = 3) -> Dict[str, Any]:
    """
    Generate a visual tree representation of the knowledge tree.
    
    Args:
        root_element_id: Optional root element to start from, or show all if empty
        max_depth: Maximum depth to traverse (default: 3)
    
    Returns:
        Tree visualization and statistics
    """
    try:
        all_elements = {elem.id: elem for elem in get_all_elements()}
        
        if not all_elements:
            return {
                "success": True,
                "message": "Knowledge tree is empty",
                "tree": "",
                "statistics": {"total_elements": 0}
            }
        
        def build_tree_recursive(element_id: str, depth: int = 0, visited: set = None) -> List[str]:
            if visited is None:
                visited = set()
            
            if depth > max_depth or element_id in visited:
                return []
            
            visited.add(element_id)
            lines = []
            
            element = all_elements.get(element_id)
            if not element:
                lines.append("  " * depth + f"├── {element_id} [MISSING]")
                return lines
            
            # Add current element
            prefix = "├── " if depth > 0 else ""
            lines.append("  " * depth + f"{prefix}{element.id} [{element.type}] - {element.description}")
            
            # Add dependencies
            for dep_id in element.dependencies:
                lines.extend(build_tree_recursive(dep_id, depth + 1, visited.copy()))
            
            return lines
        
        tree_lines = []
        
        if root_element_id:
            # Show tree from specific root
            if root_element_id not in all_elements:
                return {
                    "success": False,
                    "message": f"Root element '{root_element_id}' not found"
                }
            tree_lines = build_tree_recursive(root_element_id)
        else:
            # Show all top-level elements (elements with no dependents)
            top_level = [elem for elem in all_elements.values() if not elem.dependents]
            
            if not top_level:
                # If no clear top-level, show all elements
                top_level = list(all_elements.values())
            
            for element in top_level:
                tree_lines.extend(build_tree_recursive(element.id))
                tree_lines.append("")  # Add spacing between trees
        
        # Generate statistics
        stats = {
            "total_elements": len(all_elements),
            "element_types": {},
            "avg_dependencies": 0,
            "max_dependencies": 0,
            "orphaned_elements": 0
        }
        
        total_deps = 0
        for element in all_elements.values():
            # Count by type
            stats["element_types"][element.type] = stats["element_types"].get(element.type, 0) + 1
            
            # Dependency stats
            dep_count = len(element.dependencies)
            total_deps += dep_count
            stats["max_dependencies"] = max(stats["max_dependencies"], dep_count)
            
            # Orphaned elements (no dependencies and no dependents)
            if not element.dependencies and not element.dependents:
                stats["orphaned_elements"] += 1
        
        if len(all_elements) > 0:
            stats["avg_dependencies"] = round(total_deps / len(all_elements), 2)
        
        return {
            "success": True,
            "tree": "\n".join(tree_lines),
            "statistics": stats
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating tree view: {str(e)}"
        }

@mcp.tool()
def list_all_elements() -> Dict[str, Any]:
    """
    List all elements in the knowledge tree with basic information.
    
    Returns:
        List of all elements with summary information
    """
    try:
        elements = get_all_elements()
        
        if not elements:
            return {
                "success": True,
                "message": "Knowledge tree is empty",
                "elements": [],
                "total": 0
            }
        
        element_summaries = []
        for element in sorted(elements, key=lambda x: x.id):
            element_summaries.append({
                "id": element.id,
                "type": element.type,
                "description": element.description,
                "dependencies_count": len(element.dependencies),
                "dependents_count": len(element.dependents),
                "created_at": element.created_at
            })
        
        return {
            "success": True,
            "elements": element_summaries,
            "total": len(elements)
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error listing elements: {str(e)}"
        }


@mcp.tool()
def update_code_element(
    element_id: str,
    code: str = "",
    description: str = "",
    dependencies: List[str] = None,
    source_file: str = "",
    line_range: str = ""
) -> Dict[str, Any]:
    """
    Update an existing code element in the knowledge tree.
    
    Args:
        element_id: ID of the element to update
        code: New code content (optional - leave empty to keep existing)
        description: New description (optional - leave empty to keep existing)
        dependencies: New dependencies list (optional - leave None to keep existing)
        source_file: New source file (optional - leave empty to keep existing)
        line_range: New line range (optional - leave empty to keep existing)
    
    Returns:
        Success status and updated element info
    """
    try:
        element = load_element(element_id)
        if not element:
            return {
                "success": False,
                "message": f"Element '{element_id}' not found. Use add_code_element to create it."
            }
        
        # Update only provided fields
        updated_fields = []
        original_deps = element.dependencies.copy()
        
        if code.strip():
            element.code = code.strip()
            updated_fields.append("code")
        if description.strip():
            element.description = description
            updated_fields.append("description")
        if source_file.strip():
            element.source_file = source_file
            updated_fields.append("source_file")
        if line_range.strip():
            element.line_range = line_range
            updated_fields.append("line_range")
        
        # Handle dependencies update
        missing_dependencies = []
        existing_dependencies = []
        dependencies_changed = False
        
        if dependencies is not None:
            if isinstance(dependencies, str):
                dependencies = [dependencies]
            
            element.dependencies = dependencies
            updated_fields.append("dependencies")
            dependencies_changed = True
            
            # Clean up old dependency relationships
            for old_dep in original_deps:
                if old_dep not in dependencies:  # Dependency was removed
                    old_dep_element = load_element(old_dep)
                    if old_dep_element and element_id in old_dep_element.dependents:
                        old_dep_element.dependents.remove(element_id)
                        save_element(old_dep_element)
            
            # Update new dependency relationships
            for dep_id in dependencies:
                dep_element = load_element(dep_id)
                if dep_element:
                    if element_id not in dep_element.dependents:
                        dep_element.dependents.append(element_id)
                        save_element(dep_element)
                    existing_dependencies.append(dep_id)
                else:
                    missing_dependencies.append(dep_id)
        
        if not updated_fields:
            return {
                "success": False,
                "message": "No fields provided for update. Specify at least one field to update."
            }
        
        save_element(element)
        
        result = {
            "success": True,
            "message": f"Successfully updated {element.type} '{element_id}'",
            "updated_fields": updated_fields,
            "element": {
                "id": element.id,
                "type": element.type,
                "description": element.description,
                "dependencies": element.dependencies,
                "updated_at": element.updated_at
            }
        }
        
        # Add dependency analysis if dependencies were changed
        if dependencies_changed:
            result["dependency_analysis"] = {
                "original_dependencies": original_deps,
                "new_dependencies": element.dependencies,
                "existing_dependencies": existing_dependencies,
                "missing_dependencies": missing_dependencies,
                "missing_count": len(missing_dependencies)
            }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error updating element: {str(e)}"
        }

@mcp.tool()
def remove_element(element_id: str) -> Dict[str, Any]:
    """
    Remove an element from the knowledge tree and clean up its dependencies.
    
    Args:
        element_id: ID of the element to remove
    
    Returns:
        Success status and cleanup information
    """
    try:
        element = load_element(element_id)
        if not element:
            return {
                "success": False,
                "message": f"Element '{element_id}' not found"
            }
        
        # Clean up references in other elements
        all_elements = get_all_elements()
        updated_elements = []
        
        for other_element in all_elements:
            if other_element.id == element_id:
                continue
            
            # Remove from dependencies
            if element_id in other_element.dependencies:
                other_element.dependencies.remove(element_id)
                save_element(other_element)
                updated_elements.append(f"{other_element.id} (removed from dependencies)")
            
            # Remove from dependents
            if element_id in other_element.dependents:
                other_element.dependents.remove(element_id)
                save_element(other_element)
                updated_elements.append(f"{other_element.id} (removed from dependents)")
        
        # Remove the element file
        element_file = ELEMENTS_DIR / f"{element_id}.json"
        element_file.unlink()
        
        # Update metadata
        update_metadata()
        
        return {
            "success": True,
            "message": f"Successfully removed {element.type} '{element_id}'",
            "cleaned_references": updated_elements,
            "dependencies_removed": element.dependencies,
            "dependents_updated": element.dependents
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error removing element: {str(e)}"
        }

@mcp.tool()
def import_from_analysis_file(
    file_path: str,
    element_id: str = "",
    auto_extract: bool = True
) -> Dict[str, Any]:
    """
    Import code elements from existing analysis files (like the analysis/ directory).
    
    Args:
        file_path: Path to the analysis file to import
        element_id: Optional specific element ID to use, otherwise auto-detect
        auto_extract: Whether to automatically extract dependencies from comments
    
    Returns:
        Import results and extracted elements
    """
    try:
        if not os.path.exists(file_path):
            return {
                "success": False,
                "message": f"File not found: {file_path}"
            }
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract basic info from the file
        lines = content.split('\n')
        
        # Try to extract element info from comments
        extracted_info = {
            "functions": [],
            "modules": [],
            "constants": [],
            "dependencies": []
        }
        
        current_function = None
        current_code = []
        in_function = False
        
        for line in lines:
            line = line.strip()
            
            # Extract function definitions
            if line.startswith('function ') and '(' in line:
                if current_function and current_code:
                    # Save previous function
                    extracted_info["functions"].append({
                        "id": current_function,
                        "code": '\n'.join(current_code),
                        "description": f"Function extracted from {file_path}"
                    })
                
                # Start new function
                func_name = line.split('function ')[1].split('(')[0].strip()
                current_function = func_name
                current_code = [line]
                in_function = True
            elif in_function and (line.startswith('}') or line == ''):
                # End of function
                if line.startswith('}'):
                    current_code.append(line)
                if current_function and current_code:
                    extracted_info["functions"].append({
                        "id": current_function,
                        "code": '\n'.join(current_code),
                        "description": f"Function extracted from {file_path}"
                    })
                current_function = None
                current_code = []
                in_function = False
            elif in_function:
                current_code.append(line)
            
            # Extract dependencies from comments
            if auto_extract and ('DEPENDENCIES' in line.upper() or 'CALLS:' in line.upper()):
                # Look for dependency patterns in comments
                if 'r(' in line:
                    # Extract r(nnnn) module references
                    import re
                    matches = re.findall(r'r\((\d+)\)', line)
                    for match in matches:
                        extracted_info["modules"].append(f"r{match}")
                
                # Extract function calls
                if '()' in line and not line.startswith('//'):
                    func_matches = re.findall(r'(\w+)\(\)', line)
                    for func in func_matches:
                        extracted_info["dependencies"].append(func)
        
        # Add final function if exists
        if current_function and current_code:
            extracted_info["functions"].append({
                "id": current_function,
                "code": '\n'.join(current_code),
                "description": f"Function extracted from {file_path}"
            })
        
        # Import the extracted elements
        imported_elements = []
        failed_imports = []
        
        for func_info in extracted_info["functions"]:
            try:
                # Check if element already exists
                existing = load_element(func_info["id"])
                if existing:
                    failed_imports.append(f"Function '{func_info['id']}' already exists")
                    continue
                
                element = CodeElement(
                    id=func_info["id"],
                    type="function",
                    code=func_info["code"],
                    description=func_info["description"],
                    dependencies=[],
                    dependents=[],
                    source_file=file_path
                )
                save_element(element)
                imported_elements.append(func_info["id"])
            except Exception as e:
                failed_imports.append(f"Failed to import '{func_info['id']}': {str(e)}")
        
        return {
            "success": True,
            "message": f"Import completed from {file_path}",
            "imported_elements": imported_elements,
            "failed_imports": failed_imports,
            "extracted_info": {
                "functions_found": len(extracted_info["functions"]),
                "potential_dependencies": extracted_info["dependencies"],
                "modules_referenced": extracted_info["modules"]
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error importing from file: {str(e)}"
        }

@mcp.tool()
def get_knowledge_tree_stats() -> Dict[str, Any]:
    """
    Get comprehensive statistics about the current knowledge tree.
    
    Returns:
        Detailed statistics and health metrics
    """
    try:
        elements = get_all_elements()
        
        if not elements:
            return {
                "success": True,
                "message": "Knowledge tree is empty",
                "stats": {
                    "total_elements": 0,
                    "element_types": {},
                    "dependency_health": "N/A"
                }
            }
        
        # Basic counts
        stats = {
            "total_elements": len(elements),
            "element_types": {},
            "dependency_stats": {
                "total_dependencies": 0,
                "avg_dependencies_per_element": 0,
                "max_dependencies": 0,
                "elements_with_no_dependencies": 0,
                "elements_with_no_dependents": 0
            },
            "health_metrics": {
                "orphaned_elements": 0,  # No deps and no dependents
                "missing_dependencies": 0,
                "circular_dependencies": 0
            }
        }
        
        all_element_ids = {elem.id for elem in elements}
        total_deps = 0
        missing_deps = set()
        
        for element in elements:
            # Count by type
            stats["element_types"][element.type] = stats["element_types"].get(element.type, 0) + 1
            
            # Dependency analysis
            dep_count = len(element.dependencies)
            total_deps += dep_count
            stats["dependency_stats"]["max_dependencies"] = max(
                stats["dependency_stats"]["max_dependencies"], dep_count
            )
            
            if dep_count == 0:
                stats["dependency_stats"]["elements_with_no_dependencies"] += 1
            
            if len(element.dependents) == 0:
                stats["dependency_stats"]["elements_with_no_dependents"] += 1
            
            # Health metrics
            if dep_count == 0 and len(element.dependents) == 0:
                stats["health_metrics"]["orphaned_elements"] += 1
            
            # Check for missing dependencies
            for dep_id in element.dependencies:
                if dep_id not in all_element_ids:
                    missing_deps.add(dep_id)
        
        stats["dependency_stats"]["total_dependencies"] = total_deps
        if len(elements) > 0:
            stats["dependency_stats"]["avg_dependencies_per_element"] = round(
                total_deps / len(elements), 2
            )
        
        stats["health_metrics"]["missing_dependencies"] = len(missing_deps)
        
        # Calculate overall health score
        health_score = 100
        if len(elements) > 0:
            orphan_penalty = (stats["health_metrics"]["orphaned_elements"] / len(elements)) * 20
            missing_penalty = (len(missing_deps) / max(total_deps, 1)) * 30
            health_score = max(0, health_score - orphan_penalty - missing_penalty)
        
        stats["health_metrics"]["overall_health_score"] = round(health_score, 1)
        stats["missing_dependency_list"] = list(missing_deps)
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating stats: {str(e)}"
        }

@mcp.tool()
def get_working_directory_info() -> Dict[str, Any]:
    """
    Get information about the current working directory configuration.
    
    Returns:
        Current working directory paths and status
    """
    try:
        base_working_dir = KNOWLEDGE_BASE_DIR.parent if KNOWLEDGE_BASE_DIR else None
        
        return {
            "success": True,
            "working_directory": {
                "base_working_dir": str(base_working_dir) if base_working_dir else "Not initialized",
                "knowledge_tree_dir": str(KNOWLEDGE_BASE_DIR) if KNOWLEDGE_BASE_DIR else "Not initialized",
                "elements_dir": str(ELEMENTS_DIR) if ELEMENTS_DIR else "Not initialized",
                "metadata_file": str(METADATA_FILE) if METADATA_FILE else "Not initialized",
                "knowledge_tree_exists": KNOWLEDGE_BASE_DIR.exists() if KNOWLEDGE_BASE_DIR else False,
                "base_dir_is_absolute": base_working_dir.is_absolute() if base_working_dir else False
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting working directory info: {str(e)}"
        }


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Code Knowledge Tree MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python code_knowledge_server.py
    # Creates: ./knowledge-tree/

  python code_knowledge_server.py --working-dir ./my_project_analysis
    # Creates: ./my_project_analysis/knowledge-tree/

  python code_knowledge_server.py --working-dir /absolute/path/to/base
    # Creates: /absolute/path/to/base/knowledge-tree/
        """
    )
    
    parser.add_argument(
        "--working-dir",
        type=str,
        default=".",
        help="Base directory where the 'knowledge-tree' folder will be created (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Initialize the working directory configuration
    try:
        initialize_working_directory(args.working_dir)
        print(f"✓ Working directory: {Path(args.working_dir).resolve()}")
        print(f"✓ Knowledge tree created at: {KNOWLEDGE_BASE_DIR}")
        print(f"✓ Elements directory: {ELEMENTS_DIR}")
        print(f"✓ Metadata file: {METADATA_FILE}")
    except Exception as e:
        print(f"✗ Error initializing working directory: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Run the MCP server
    mcp.run()