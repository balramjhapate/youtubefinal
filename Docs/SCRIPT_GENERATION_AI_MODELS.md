# Hindi Script Generation - AI Models Used

## Overview
The Hindi script generation feature uses a configurable AI provider system. The provider can be set in the AI Provider Settings.

## Configuration
The script generation provider is controlled by the `script_generation_provider` field in `AIProviderSettings` model, which can be set to:
- `gemini` (default)
- `openai`
- `anthropic`

## AI Models Used by Provider

### 1. Gemini (Default)
**Provider**: Google Gemini  
**Models Tried (in order)**:
1. `gemini-1.5-flash` (first attempt - fastest)
2. `gemini-2.0-flash` (fallback)
3. `gemini-2.5-flash` (fallback)
4. `gemini-pro` (fallback)

**Location**: `backend/pipeline/utils.py` - `_call_gemini_api()` function (line 2224)

**Note**: The system tries models in order until one works. If a model returns 404, it automatically tries the next one.

### 2. OpenAI
**Provider**: OpenAI  
**Model**: `gpt-4o-mini`

**Location**: `backend/pipeline/utils.py` - `_call_openai_api()` function (line 2303)

**Note**: This is the model used when `script_generation_provider` is set to `openai`.

### 3. Anthropic
**Provider**: Anthropic (Claude)  
**Model**: `claude-3-sonnet-20240229`

**Location**: `backend/pipeline/utils.py` - `generate_video_metadata()` function (line 3726)

**Note**: ⚠️ **NOT CURRENTLY SUPPORTED** for script generation. Anthropic is only used for metadata generation (title, description, tags). If `script_generation_provider` is set to `anthropic`, script generation will fail with "Unsupported AI provider: anthropic".

## Current Implementation

The Hindi script generation function (`generate_hindi_script()` at line 3799) uses:
- `settings_obj.script_generation_provider` to determine which provider to use
- Calls the appropriate API function based on the provider:
  - `gemini` → `_call_gemini_api()` → tries `gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-pro`
  - `openai` → `_call_openai_api()` → uses `gpt-4o-mini`
  - `anthropic` → ❌ **Returns error**: "Unsupported AI provider: anthropic"

## Verification

To verify which model is currently being used:
1. Check the `script_generation_provider` value in `AIProviderSettings` (default: `gemini`)
2. Check the console logs when script generation runs - it will show:
   ```
   🤖 Generating Hindi script using {PROVIDER} AI...
      - Provider: {provider} (script_generation_provider)
   ```

## Summary

**For OpenAI Provider**: ✅ Uses `gpt-4o-mini` (not "gpt-40-mini" - that was a typo)

**For Gemini Provider**: Uses `gemini-1.5-flash` (or falls back to other models if unavailable)

**Default**: Gemini (`gemini-1.5-flash`)

