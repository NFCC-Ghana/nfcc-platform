# NFCC Evidence-Based Classification

## Classification Rules

### PRODUCTION (Confirmed Active)
- **Evidence Required:** File is imported by dashboard.py, streamlit_app.py, or deployed in production
- **Action:** NEVER TOUCH

### RUNTIME (Loaded Dynamically)
- **Evidence Required:** File is referenced in configuration, deployment, or loaded by name
- **Action:** KEEP

### DEVELOPMENT (Build/Test Support)
- **Evidence Required:** File is used for development, testing, or build process
- **Action:** KEEP

### BACKUP (Historical Copy)
- **Evidence Required:** File is a backup of another file (same name with .backup, .bak, .orig)
- **Action:** ARCHIVE

### LEGACY (Historical/Disabled)
- **Evidence Required:** File is in archive/ or pages_disabled/ directory
- **Action:** ARCHIVE

### GENERATED (Auto-generated)
- **Evidence Required:** File is cache, coverage, or generated output
- **Action:** DELETE

### UNKNOWN (Needs Manual Review)
- **Evidence Required:** No evidence found in imports, git history, or deployment
- **Action:** REVIEW MANUALLY

---

## Classification Results

### PRODUCTION FILES (Confirmed Active)

| File | Evidence |
|------|----------|
| hackathon/app/pages/dashboard.py | ✅ Imported by streamlit_app.py |
| hackathon/app/streamlit_app.py | ✅ Deployment entry point |
| hackathon/app/modules/v4/__init__.py | ✅ Package init |
| hackathon/app/modules/v4/state.py | ✅ Imported by dashboard.py |
| hackathon/app/modules/v4/state_fallback.py | ✅ Imported by dashboard.py |
| hackathon/app/modules/v4/visual_components.py | ✅ Imported by dashboard.py |
| hackathon/app/modules/v4/situation_map.py | ✅ Imported by dashboard.py |
| hackathon/app/modules/v4/ai_copilot.py | ⚠️ Imports found in archive, needs verification |
| hackathon/ai/flood_explainer.py | ✅ Imported by test_ai_modules.py |
| hackathon/ai/hydrological_intelligence.py | ✅ Imported by __init__.py |
| hackathon/ai/impact_estimator.py | ✅ Imported by tests and src |
| .streamlit/config.toml | ✅ Streamlit configuration |
| render.yaml | ✅ Render deployment |
| requirements.txt | ✅ Main dependencies |
| Dockerfile | ✅ Container build |

