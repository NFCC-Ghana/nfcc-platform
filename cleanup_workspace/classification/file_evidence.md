# NFCC File Evidence Report

## Critical Files Evidence

### hackathon/app/pages/dashboard.py
- **Exists:** ✅
- **Syntax:** ✅
- **Imported By:** streamlit_app.py
- **Status:** PRODUCTION

### hackathon/app/streamlit_app.py
- **Exists:** ✅
- **Syntax:** ✅
- **Imported By:** (entry point - not imported)
- **Status:** PRODUCTION

### hackathon/app/modules/v4/ai_copilot.py
- **Exists:** ✅
- **Syntax:** ❌ (line 80 - unterminated string)
- **Imported By:** archive/dashboard_enhanced.py
- **Status:** PRODUCTION (needs syntax fix)

### hackathon/ai/flood_explainer.py
- **Exists:** ✅
- **Syntax:** ❌ (line 142 - unterminated string)
- **Imported By:** test_ai_modules.py, archive/dashboard_enhanced_v2.py
- **Status:** PRODUCTION (needs syntax fix)

### hackathon/ai/impact_estimator.py
- **Exists:** ✅
- **Syntax:** ❌ (unknown - needs investigation)
- **Imported By:** test_ai_modules.py, archive/dashboard_enhanced_v2.py, src/exposure/__init__.py
- **Status:** PRODUCTION (needs syntax fix)

### hackathon/app/modules/v4/control_panel.py
- **Exists:** ✅
- **Syntax:** ✅
- **Imported By:** (not found - may be dynamic import)
- **Status:** UNKNOWN (needs manual review)

### hackathon/app/modules/v4/impact_assessment.py
- **Exists:** ✅
- **Syntax:** ✅
- **Imported By:** (not found - may be dynamic import)
- **Status:** UNKNOWN (needs manual review)

### hackathon/app/modules/v4/risk_display.py
- **Exists:** ✅
- **Syntax:** ✅
- **Imported By:** (not found - may be dynamic import)
- **Status:** UNKNOWN (needs manual review)

## Backup Files Evidence

### backups/pre_enhancement_20260617_022640/hydrology/rainfall_history.py.bak
- **Exists:** ✅
- **Syntax:** ⚠️ Backup of another file
- **Status:** BACKUP

### backups/state_update_20260714/dashboard.py.backup
- **Exists:** ✅
- **Syntax:** ⚠️ Backup of dashboard.py
- **Status:** BACKUP

## Archive Directories Evidence

### hackathon/archive/
- **Exists:** ✅
- **Contains:** Old dashboard versions
- **Status:** LEGACY

### hackathon/app/pages_disabled/
- **Exists:** ✅
- **Contains:** Disabled pages
- **Status:** LEGACY

### backups/
- **Exists:** ✅
- **Contains:** Pre-migration backups
- **Status:** BACKUP

## Generated Files Evidence

### .pytest_cache/
- **Exists:** ✅
- **Type:** Test cache
- **Status:** GENERATED

### __pycache__/
- **Exists:** ✅
- **Type:** Python cache
- **Status:** GENERATED

### htmlcov/
- **Exists:** ✅
- **Type:** Coverage report
- **Status:** GENERATED

## Unknown Files (Manual Review Required)

### hackathon/app/pages/dashboard_fixed.py
- **Exists:** ✅
- **Syntax:** ✅
- **Imported By:** (not found)
- **Question:** Is this a test or an alternative dashboard?

### hackathon/app/modules/v4/visual_components_fixed.py
- **Exists:** ✅
- **Syntax:** ✅
- **Imported By:** (not found)
- **Question:** Is this a fixed version of visual_components?

### railway.json
- **Exists:** ✅
- **Type:** Railway configuration
- **Question:** Is this still used?

