# Windows Setup Guide

This guide covers Windows-specific setup requirements for the WhatsApp MCP server.

## Overview

The WhatsApp MCP server works on Windows with some additional setup. The main requirement is enabling CGO and installing a C compiler for the `go-sqlite3` dependency used by the Go bridge.

## CGO Requirement

The `go-sqlite3` library requires **CGO to be enabled** to compile and work properly. By default, **CGO is disabled on Windows**, so you need to explicitly enable it and have a C compiler installed.

## Installation Steps

### 1. Install MSYS2 and C Compiler

We recommend using [MSYS2](https://www.msys2.org/) to install a C compiler for Windows.

**Download and Install MSYS2**:
1. Download the installer from [https://www.msys2.org/](https://www.msys2.org/)
2. Run the installer and follow the installation wizard
3. Complete the installation to `C:\msys64` (default location)

**Install the C Compiler**:
1. Open MSYS2 UCRT64 terminal (from Start menu)
2. Update package database:
   ```bash
   pacman -Syu
   ```
3. Install the MinGW-w64 GCC compiler:
   ```bash
   pacman -S mingw-w64-ucrt-x86_64-gcc
   ```

**Step-by-Step Guide**: For detailed instructions with screenshots, see the [VS Code C++ configuration guide](https://code.visualstudio.com/docs/cpp/config-mingw).

### 2. Add Compiler to PATH

Add the MSYS2 compiler to your Windows PATH environment variable:

1. Open System Properties:
   - Press `Win + R`
   - Type `sysdm.cpl` and press Enter
   - Go to "Advanced" tab
   - Click "Environment Variables"

2. Edit the PATH variable:
   - Under "System variables", find and select "Path"
   - Click "Edit"
   - Click "New"
   - Add: `C:\msys64\ucrt64\bin`
   - Click "OK" on all dialogs

3. Verify installation:
   - Open a new Command Prompt or PowerShell
   - Run: `gcc --version`
   - Should display GCC version information

### 3. Enable CGO

Enable CGO in your Go environment:

```bash
# Navigate to the bridge directory
cd whatsapp-bridge

# Enable CGO
go env -w CGO_ENABLED=1

# Verify CGO is enabled
go env CGO_ENABLED
# Should output: 1
```

### 4. Build and Run the Bridge

With CGO enabled and the compiler installed, you can now build and run the bridge:

```bash
# From the whatsapp-bridge directory
go run main.go
```

## Common Windows Errors

### Error: Binary was compiled with 'CGO_ENABLED=0'

**Full Error Message**:
```
Binary was compiled with 'CGO_ENABLED=0', go-sqlite3 requires cgo to work.
This is a stub
```

**Cause**: CGO is disabled (default on Windows)

**Solution**: Enable CGO as described in step 3 above
```bash
cd whatsapp-bridge
go env -w CGO_ENABLED=1
go run main.go
```

### Error: gcc: not found

**Full Error Message**:
```
exec: "gcc": executable file not found in %PATH%
```

**Cause**: C compiler is not installed or not in PATH

**Solution**: Install MSYS2 and add compiler to PATH (steps 1-2 above)

### Error: undefined reference to 'sqlite3_...'

**Cause**: Compiler cannot find SQLite library files

**Solution**: Ensure you installed the full MSYS2 GCC package:
```bash
# In MSYS2 UCRT64 terminal
pacman -S mingw-w64-ucrt-x86_64-gcc
```

### Path Issues with Spaces

**Issue**: Errors when paths contain spaces (e.g., "Program Files")

**Solution**: Use short path names or move installation to path without spaces
```bash
# Use short path
cd /d C:\PROGRA~1\whatsapp-mcp

# Or move to simpler path
cd C:\dev\whatsapp-mcp
```

## Prerequisites

### Required Software

1. **Go**: Download from [https://go.dev/dl/](https://go.dev/dl/)
   - Install using the Windows installer
   - Verify: `go version`

2. **Python 3.6+**: Download from [https://www.python.org/downloads/](https://www.python.org/downloads/)
   - Install with "Add Python to PATH" option checked
   - Verify: `python --version`

3. **UV Package Manager**: Install via PowerShell
   ```powershell
   # Using installation script
   irm https://astral.sh/uv/install.ps1 | iex

   # Verify installation
   uv --version
   ```

4. **FFmpeg** (Optional, for audio messages):
   - Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
   - Extract to a directory (e.g., `C:\ffmpeg`)
   - Add `C:\ffmpeg\bin` to PATH

### Optional: Git for Windows

For cloning the repository:
- Download from [https://git-scm.com/download/win](https://git-scm.com/download/win)
- Install with default options

## PowerShell vs Command Prompt

The WhatsApp MCP server works with both PowerShell and Command Prompt. Choose based on your preference:

**PowerShell** (Recommended):
- Modern shell with better scripting
- Better Unicode support
- Easier environment variable management

**Command Prompt**:
- Traditional Windows shell
- May require different syntax for some commands

## Configuration Paths

### Claude Desktop Configuration

Windows configuration location:
```
%APPDATA%\Claude\claude_desktop_config.json
```

Full path example:
```
C:\Users\YourUsername\AppData\Roaming\Claude\claude_desktop_config.json
```

### Cursor Configuration

Windows configuration location:
```
%USERPROFILE%\.cursor\mcp.json
```

Full path example:
```
C:\Users\YourUsername\.cursor\mcp.json
```

### Example Configuration

```json
{
  "mcpServers": {
    "whatsapp": {
      "command": "C:\\Users\\YourUsername\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\uv.exe",
      "args": [
        "--directory",
        "C:\\Users\\YourUsername\\Projects\\whatsapp-mcp\\whatsapp-mcp-server",
        "run",
        "main.py"
      ]
    }
  }
}
```

**Note**: Use double backslashes (`\\`) in JSON paths on Windows.

## Finding Executable Paths

### Find UV Path

**PowerShell**:
```powershell
(Get-Command uv).Path
```

**Command Prompt**:
```cmd
where uv
```

### Find Python Path

**PowerShell**:
```powershell
(Get-Command python).Path
```

**Command Prompt**:
```cmd
where python
```

## Database Paths

### SQLite Default Locations

```
whatsapp-bridge\store\messages.db
whatsapp-bridge\store\whatsapp.db
```

### PostgreSQL Connection

Same format as Linux/macOS:
```bash
set DATABASE_URL=postgresql://user:password@host:5432/dbname
```

## Running the Server

### Start Bridge Manually

```bash
# Using Command Prompt or PowerShell
cd whatsapp-bridge
go run main.go
```

### Start with Environment Variables

**PowerShell**:
```powershell
$env:DATABASE_URL = "postgresql://user:password@host:5432/dbname"
cd whatsapp-bridge
go run main.go
```

**Command Prompt**:
```cmd
set DATABASE_URL=postgresql://user:password@host:5432/dbname
cd whatsapp-bridge
go run main.go
```

## Troubleshooting

### CGO Still Disabled After Enabling

**Solution**: Restart your terminal or IDE after enabling CGO
```bash
# Close and reopen terminal, then verify
go env CGO_ENABLED
```

### Compiler Works in MSYS2 but Not in PowerShell

**Solution**: Verify PATH is set correctly in Windows System Environment Variables, not just in the MSYS2 terminal

### Permission Denied Errors

**Solution**: Run PowerShell or Command Prompt as Administrator
- Right-click on PowerShell/Command Prompt
- Select "Run as administrator"

### Python Module Not Found

**Solution**: Install modules in the correct Python environment
```bash
cd whatsapp-mcp-server
pip install -r requirements.txt
```

### Port Already in Use

**Solution**: Find and kill the process using the port

**PowerShell**:
```powershell
# Find process using port 8080
Get-Process -Id (Get-NetTCPConnection -LocalPort 8080).OwningProcess

# Kill the process
Stop-Process -Id (Get-NetTCPConnection -LocalPort 8080).OwningProcess -Force
```

## Additional Resources

- **MSYS2 Documentation**: [https://www.msys2.org/docs/what-is-msys2/](https://www.msys2.org/docs/what-is-msys2/)
- **MinGW-w64**: [https://www.mingw-w64.org/](https://www.mingw-w64.org/)
- **Go on Windows**: [https://go.dev/doc/install](https://go.dev/doc/install)
- **VS Code C++ Setup**: [https://code.visualstudio.com/docs/cpp/config-mingw](https://code.visualstudio.com/docs/cpp/config-mingw)
- **Main Documentation**: See [../README.md](../../README.md) for general setup instructions
