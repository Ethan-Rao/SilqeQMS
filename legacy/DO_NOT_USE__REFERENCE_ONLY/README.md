# ⚠️ LEGACY CODE - DO NOT USE ⚠️

**THIS CODE IS ARCHIVED FOR HISTORICAL REFERENCE ONLY**

These files are **NOT imported**, **NOT supported**, and **MUST NOT** be copied into the main codebase.

## Why This Exists

This folder contains original prototype code that was used during early development. The patterns and approaches in these files have been **completely replaced** with the modular architecture in `app/eqms/modules/`.

## Files

| File | Description |
|------|-------------|
| `repqms_Proto1_reference.py.py` | Original monolithic prototype |
| `repqms_shipstation_sync.py.py` | Original ShipStation sync code |
| `admin_*.html` | Legacy HTML templates |

## Rules

1. **DO NOT** import any functions from these files
2. **DO NOT** copy-paste code from these files
3. **DO NOT** use these files as examples for new code
4. Use the modular implementations in `app/eqms/modules/` instead

## If You Need Reference

If you need to understand historical behavior:
1. Read the code here for context
2. Implement a **new** solution in the appropriate module
3. Follow the patterns established in `app/eqms/modules/`

## Removal

This folder may be deleted in future versions once all legacy functionality has been verified in the new architecture.
