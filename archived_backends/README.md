# Archived Backends

This directory contains archived/backup versions of backend code that are no longer in active use.

## Contents

### backend/ (Archived on 2024)

**Status**: ❌ Not in active use

**Original Location**: `/backend/`

**Reason for Archive**: 
- This was an unused/older version of the Django backend
- The active backend was previously at `/legacy/root_debris/` but has been moved to `/backend/`
- This version had fewer features (no REST Framework, no Cloudinary, no Google Sheets integration, etc.)
- It had a more customized Django Admin UI (Jazzmin theme) but lacked the advanced features of the active backend

**Key Differences from Active Backend**:
- Simpler architecture (function-based views only, no REST Framework)
- Fewer database migrations (12 vs 30)
- No cloud storage integration
- No Google Sheets tracking
- No watermarking capabilities
- Single AI provider support only

**If You Need This**:
- The code is preserved here in case you need to reference it
- To restore: Copy this directory back to the root as `/backend/`
- Note: You would need to update `run_project.sh` to use it

**Active Backend**: See `/backend/` for the currently running backend (moved from `/legacy/root_debris/` in December 2024).

---

For more details, see `/BACKEND_STRUCTURE_ANALYSIS.md` in the project root.
