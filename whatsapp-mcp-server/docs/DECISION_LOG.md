# Decision Log

## Entry Point Rename: main.py → server.py

**Date:** October 9, 2025  
**Status:** Implemented

### Context

The `whatsapp-mcp-server` directory contained a `main.py` file that serves as the primary entry point for both the MCP (Model Context Protocol) server and HTTP server functionality.

### Decision

Rename `main.py` to `server.py` while maintaining backward compatibility.

### Rationale

**Benefits:**
- **Clarity**: The name `server.py` more clearly describes the file's purpose as a server implementation
- **Discoverability**: Newcomers to the codebase can more easily identify the server entry point
- **Consistency**: Aligns with the server functionality (both MCP and HTTP transport modes)
- **Future-proofing**: Prepares for potential future CLI entry-points or multiple main modules

**Costs:**
- Minor code churn in references (Dockerfile, README, deployment scripts)
- Potential confusion during transition period

### Implementation

1. **Renamed** `main.py` → `server.py`
2. **Created** a thin `main.py` wrapper using `runpy.run_module()` for backward compatibility
3. **Updated** primary references:
   - README.md MCP configuration examples
   - Dockerfile CMD instruction
   - Test imports in `tests/test_http_app.py`
4. **Maintained** full backward compatibility - existing scripts continue to work

### Backward Compatibility

- All existing references to `python main.py` continue to work unchanged
- Docker containers and deployment scripts function without modification
- The wrapper introduces minimal overhead (single import + module execution)

### Testing

- Verified both entry points work: `python server.py --help` and `python main.py --help`
- All existing tests pass with updated imports
- Both MCP and HTTP transport modes function correctly

### Future Considerations

- The `main.py` wrapper can be deprecated in a future major version if desired
- Documentation should primarily reference `server.py` going forward
- Consider adding a proper CLI structure if additional entry points are needed