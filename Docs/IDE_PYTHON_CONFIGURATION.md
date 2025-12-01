# IDE Python Configuration Guide

## Problem

You're seeing import errors like:
```
Import "django.conf" could not be resolved
```

This is happening in all Python files across the project.

## Root Cause

This is an **IDE/linter configuration issue**, not a code problem. Your IDE is not using the correct Python interpreter (virtual environment) where Django and other packages are installed.

## Solution

### For VS Code / Cursor

1. **Open Command Palette**: `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)

2. **Select Python Interpreter**: Type "Python: Select Interpreter"

3. **Choose the Virtual Environment**:
   - Look for: `./backend/venv/bin/python` or `./backend/venv/bin/python3`
   - The path should show: `Python 3.x.x ('venv': venv) ./backend/venv/bin/python`

4. **Alternatively**, create/edit `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.analysis.extraPaths": [
        "${workspaceFolder}/backend"
    ]
}
```

### For PyCharm

1. Go to **File → Settings → Project → Python Interpreter**
2. Click the gear icon → **Add Interpreter → Add Local Interpreter**
3. Select **Existing Environment**
4. Set path to: `/Volumes/Data/WebSites/youtubefinal/backend/venv/bin/python`
5. Click **OK**

### For Other IDEs

Point your IDE's Python interpreter setting to:
```
/Volumes/Data/WebSites/youtubefinal/backend/venv/bin/python
```

## Verification

After configuring, the import errors should disappear. You can verify:

1. **In IDE**: Hover over `from django.conf import settings` - should show no error
2. **In Terminal**: 
   ```bash
   cd backend
   source venv/bin/activate
   python -c "import django; print('Django works!')"
   ```

## Why This Happens

- The virtual environment (`backend/venv/`) contains all installed packages
- Your IDE needs to know which Python interpreter to use
- If it uses system Python instead of venv Python, imports fail
- This is a **configuration issue**, not a code problem

## Quick Fix Script

Create a `.vscode/settings.json` file in your project root:

```bash
mkdir -p .vscode
cat > .vscode/settings.json << 'SETTINGS'
{
    "python.defaultInterpreterPath": "${workspaceFolder}/backend/venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.analysis.extraPaths": [
        "${workspaceFolder}/backend"
    ],
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false
}
SETTINGS
```

Then restart your IDE.

## Current Setup

- **Virtual Environment**: `backend/venv/`
- **Python Version**: Check with `backend/venv/bin/python --version`
- **Django Location**: Installed in `backend/venv/lib/python3.x/site-packages/`

## Note

The code itself is fine - this is purely an IDE configuration issue. The imports work correctly when running the code with the venv Python interpreter.
