# Code Knowledge Tree MCP Server

A specialized MCP server for recursive code analysis and dependency mapping. Designed to help understand complex codebases by building structured knowledge trees of functions, modules, constants, and their interdependencies.

## 🎯 Purpose

This server was created to systematically analyze and understand complex code like the `hr()` function in `fp.umd.original.js`. It provides tools to:

- Build incremental understanding of code elements
- Track dependencies between functions, modules, and constants  
- Identify missing dependencies that need further analysis
- Visualize code structure as dependency trees
- Import existing analysis work

## 🛠 Installation & Setup

### Install in Claude Desktop

```bash
# Install the server in Claude Desktop (creates knowledge-tree in current directory)
mcp install code_knowledge_server.py --name "Code Knowledge Tree"

# Install with custom base directory (creates knowledge-tree inside the specified directory)
mcp install code_knowledge_server.py --name "Code Knowledge Tree" -- --working-dir ./my_project_analysis
```

### Development Testing

```bash
# Test with MCP Inspector (creates knowledge-tree in current directory)
mcp dev code_knowledge_server.py

# Test with custom base directory
mcp dev code_knowledge_server.py -- --working-dir ./my_project_analysis

# Test with absolute path
mcp dev code_knowledge_server.py -- --working-dir /absolute/path/to/base
```

### Working Directory Configuration

The server creates a `knowledge-tree` folder inside your specified working directory:

- **Default**: `./knowledge-tree/` (in current directory)
- **Custom relative**: `./my_analysis/knowledge-tree/`  
- **Custom absolute**: `/home/user/projects/my_analysis/knowledge-tree/`

This allows you to:
- Keep knowledge trees organized within project directories
- Share knowledge trees across team members using consistent paths
- Organize multiple analysis projects in separate base directories
- Use centralized storage locations while maintaining the knowledge-tree structure

## 🔧 Available Tools

### Core Tools

1. **`add_code_element`** - Add functions, modules, constants, or variables
   ```python
   # Example: Add the main hr() function
   add_code_element(
       element_id="hr",
       element_type="function", 
       code="function hr(t, e) { ... }",
       description="Main hybrid cryptography function",
       source_file="fp.umd.original.js",
       line_range="33490-33511"
   )
   ```

2. **`add_dependency`** - Link dependencies between elements
   ```python
   # Link hr() function to its dependency ge()
   add_dependency("hr", "ge")
   ```

3. **`get_element`** - Retrieve detailed information about any element
   ```python
   get_element("hr")  # Returns code, dependencies, metadata
   ```

4. **`find_missing_dependencies`** - Identify unresolved dependencies
   ```python
   find_missing_dependencies("hr")  # Shows what needs to be analyzed next
   ```

5. **`get_tree_view`** - Generate visual dependency trees
   ```python
   get_tree_view("hr", max_depth=3)  # ASCII tree visualization
   ```

### Utility Tools

6. **`list_all_elements`** - Overview of all elements in the knowledge tree

7. **`update_code_element`** - Modify existing elements

8. **`remove_element`** - Remove elements and clean up references

9. **`import_from_analysis_file`** - Import from existing analysis files

10. **`get_knowledge_tree_stats`** - Health metrics and statistics

11. **`get_working_directory_info`** - Show current working directory configuration

## 📊 Example Workflow

### Understanding the hr() Function

1. **Start with the main function:**
   ```python
   add_code_element("hr", "function", "function hr(t, e) {...}", "Main crypto function")
   ```

2. **Add known dependencies:**
   ```python
   add_dependency("hr", "ge")  # RSA key selector
   add_dependency("hr", "ze")  # AES encryption
   add_dependency("hr", "Fe")  # Crypto module
   ```

3. **Find what's missing:**
   ```python
   find_missing_dependencies("hr")
   # Returns: ["ge", "ze", "Fe"] - need to analyze these
   ```

4. **Add the missing pieces:**
   ```python
   add_code_element("ge", "function", "function ge() {...}", "RSA key selector")
   add_code_element("ze", "function", "function ze(t, e) {...}", "AES encryption")
   add_code_element("Fe", "module", "r(5634)", "Crypto module")
   ```

5. **Visualize progress:**
   ```python
   get_tree_view("hr")
   ```
   
   Output:
   ```
   hr [function] - Main crypto function
   ├── ge [function] - RSA key selector
   ├── ze [function] - AES encryption  
   └── Fe [module] - Crypto module
   ```

6. **Continue recursively** until all dependencies are understood

## 📁 Data Storage

The server stores knowledge trees in a simple JSON-based format inside a `knowledge-tree` subfolder:

```
<working-dir>/                 # Configurable via --working-dir parameter
└── knowledge-tree/            # Always named 'knowledge-tree'
    ├── metadata.json          # Global metadata
    └── elements/              # Individual element files
        ├── hr.json           # Main function
        ├── ge.json           # Dependencies
        ├── ze.json
        └── Fe.json
```

**Directory Examples:**
- Default: `./knowledge-tree/`
- Custom: `./my_project_analysis/knowledge-tree/`
- Absolute: `/home/user/crypto_analysis/knowledge-tree/`

Each element file contains:
```json
{
  "id": "hr",
  "type": "function", 
  "code": "function hr(t, e) { ... }",
  "description": "Main hybrid cryptography function",
  "dependencies": ["ge", "ze", "Fe"],
  "dependents": [],
  "source_file": "fp.umd.original.js",
  "line_range": "33490-33511",
  "created_at": "2025-07-02T16:25:00Z",
  "updated_at": "2025-07-02T16:25:00Z"
}
```

## 🎯 Use Cases

### Perfect for analyzing:
- ✅ Complex JavaScript libraries with obfuscated code
- ✅ Functions with many interdependent calls
- ✅ Module systems with r(nnnn) style imports
- ✅ Cryptographic implementations
- ✅ Any codebase requiring systematic understanding

### Example Knowledge Tree:
```
hr [function] - Main hybrid cryptography function
├── ge [function] - RSA key selector
│   ├── fe [function] - Environment detection
│   ├── be [constant] - Production RSA key
│   ├── me [constant] - Pre-prod RSA key
│   └── ve [constant] - Mobile RSA key
├── ze [function] - AES encryption wrapper
│   ├── Fe.O6 [function] - Random bytes generator
│   ├── Fe.CW [function] - AES cipher creation
│   └── qe [constant] - AES algorithm constant  
├── Fe [module] - Crypto module (r5634)
│   ├── Fe.O6 [function] - Random bytes
│   ├── Fe.r0 [function] - RSA encryption
│   └── Fe._G [constant] - Crypto constants
└── Ue [module] - Buffer module (r8764)
    ├── Ue.from [function] - Buffer constructor
    └── buffer methods [function] - toString, slice, etc.
```

## 💡 Benefits

- **Incremental Understanding**: Build knowledge piece by piece
- **Dependency Tracking**: See exactly what depends on what
- **Missing Element ID**: Know what to analyze next
- **Visual Structure**: Understand code architecture at a glance
- **Import Existing Work**: Leverage previous analysis
- **Tool-Only Design**: Perfect compatibility with Claude Desktop

## 🔍 Integration with Existing Analysis

This server can import your existing analysis files from the `analysis/` directory:

```python
import_from_analysis_file("analysis/01_hr_main.js")
```

This automatically extracts functions and dependencies from your previous work.

## 🚀 Getting Started

1. Install the server in Claude Desktop
2. Start with your main function of interest
3. Add dependencies as you discover them
4. Use `find_missing_dependencies` to guide your analysis
5. Visualize progress with `get_tree_view`
6. Build complete understanding recursively

The server turns code analysis from a linear process into a systematic, visual, and manageable knowledge-building experience.
