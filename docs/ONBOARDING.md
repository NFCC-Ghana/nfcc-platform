NFCC SYSTEM SETUP & ENVIRONMENT CONFIGURATION GUIDE
National Flood Command Center (NFCC) — Engineering Onboarding Document
Version 1.0 — May 2026
1.  SYSTEM OVERVIEW
The NFCC platform is a geospatial AI system for flood prediction and monitoring.
It integrates:
•	Satellite rainfall data (CHIRPS via Google Earth Engine) 
•	Remote sensing (Sentinel-1, SRTM) 
•	Machine learning (XGBoost, Scikit-learn, SHAP) 
•	APIs (FastAPI backend) 
•	Dashboard (Streamlit + Plotly + Folium) 
•	CI/CD automation (GitHub Actions) 
•	Reproducible environments (Conda/Mamba)
DOCUMENT OVERVIEW
Field	Information
Project	National Flood Command Center (NFCC)
Document Type	Engineer Onboarding & Environment Setup
Target Audience	13 Engineers (Geospatial, Data, ML, Backend, Frontend, DevOps, QA, Docs, Community)
Prerequisites	Computer with internet access, willingness to learn
Estimated Setup Time	30-60 minutes
Support	WhatsApp group + GitHub Issues
WHAT THIS DOCUMENT COVERS
Section	Content
Part 1	What has already been set up for you
Part 2	Required downloads and installations
Part 3	GitHub authentication (SSH key)
Part 4	Cloning the repository
Part 5	Creating the Conda environment (with Mamba fallback)
Part 6	Google Earth Engine authentication
Part 7	Verifying everything works
Part 8	First task: CHIRPS data pipeline
Part 9	Engineering workflow (branches, PRs, CI/CD)
Part 10	Troubleshooting common issues
Part 11	VS Code + WSL setup (Windows users)
Part 12	Project structure overview
Part 13	Support & communication
Part 14	Final checklist
PART 1: WHAT HAS ALREADY BEEN SET UP FOR YOU
You do NOT need to do these. They are already complete.
Component	Status	Details
GitHub organization	✅ Done	NFCC-Ghana
Repository	✅ Done	nfcc-platform
main branch	✅ Done	Protected (production)
develop branch	✅ Done	Protected (integration)
CI/CD pipeline	✅ Done	GitHub Actions (automated testing)
Conda environment file	✅ Done	environment.yml
Geospatial stack	✅ Done	GDAL, rasterio, geopandas, xarray
ML stack	✅ Done	XGBoost, scikit-learn, SHAP
Dashboard stack	✅ Done	Streamlit, Folium, Plotly
API stack	✅ Done	FastAPI, Uvicorn
Project structure	✅ Done	api/, src/, data/, tests/, etc.
Your job: Clone, reproduce, and start building.
PART 2: REQUIRED DOWNLOADS & INSTALLATIONS
2.1 Minimum System Requirements
Component	Minimum	Recommended
RAM	8GB	16GB
Storage	20GB free	50GB free
OS	Windows 10, macOS 11, Ubuntu 20.04	Latest version
Internet	Broadband (5+ Mbps)	Fiber
2. REQUIRED SYSTEMS & INSTALLATIONS
2.1 Operating System (Required)
•	Windows 10 → WSL2 (Ubuntu) 
•	OR Native Linux (Ubuntu 20.04+ recommended) 
•	OR macOS (Intel or Apple Silicon)
2.2 Install Git
Windows (WSL users):
sudo apt update
sudo apt install git -y
Windows (native):
•	Download from: https://git-scm.com/download/win
•	Run installer (default options are fine)
Mac:
•	brew install git
Linux (Ubuntu/Debian):
•	sudo apt update
•	sudo apt install git -y
Verify installation:
•	git --version
•	# Should show: git version 2.25.0 or higher
2.3 Install VS Code (Recommended IDE)
Download: https://code.visualstudio.com/download
Install these extensions immediately:
Extension	Search For	Why
Python	ms-python.python	Python support
Pylance	ms-python.vscode-pylance	Fast Python intellisense
Jupyter	ms-toolsai.jupyter	Notebook support
GitLens	eamodio.gitlens	Git integration
Black Formatter	ms-python.black-formatter	Code formatting
Flake8	ms-python.flake8	Code linting
For Windows WSL users (CRITICAL):
1.	Install the WSL extension (ms-vscode-remote.remote-wsl)
2.	After installing, open VS Code
3.	Press Ctrl+Shift+P → type WSL: Connect to WSL
4.	This connects VS Code to your Ubuntu environment
2.4 Install Miniconda (Python Environment Manager)
Download: https://docs.conda.io/en/latest/miniconda.html
Linux/WSL:
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# Follow prompts:
# - Press Enter to scroll through license
# - Type "yes" to accept
# - Accept default install location
# - Type "yes" to run conda init
source ~/.bashrc
Mac:
brew install miniconda
conda init "$(basename "${SHELL}")"
Verify installation:
conda --version
# Should show: conda 24.x.x or higher
2.5 (Optional) Install Mamba — Faster Conda
If you find conda slow, install mamba:
conda install mamba -n base -c conda-forge -y
Then use mamba instead of conda for environment creation:
mamba env create -f environment.yml  # instead of conda env create
PART 3: GITHUB AUTHENTICATION (SSH KEY)
3.1 Generate SSH Key (One Time)
ssh-keygen -t ed25519 -C "your.email@example.com"
# Press Enter for all prompts (no passphrase)

cat ~/.ssh/id_ed25519.pub
# Copy the entire output (starts with ssh-ed25519)
3.2 Add SSH Key to GitHub
1.	Go to: https://github.com/settings/keys
2.	Click "New SSH Key"
3.	Title: NFCC-WSL (or your computer name)
4.	Key type: Authentication Key
5.	Key: Paste the key from Step 3.1
6.	Click "Add SSH Key"
3.3 Verify SSH Connection
ssh -T git@github.com
Expected output:
Hi username! You've successfully authenticated...
________________________________________
PROJECT SETUP
PART 4: CLONE THE REPOSITORY
# Clone the repository
git clone git@github.com:NFCC-Ghana/nfcc-platform.git
cd nfcc-platform

# Switch to develop branch (where all work happens)
git checkout develop

# Verify you are in the right place
pwd
# Should show: /home/YOUR_USERNAME/nfcc-platform (or similar)

ls -la
# Should show: .git, README.md, environment.yml, test_environment.py,
# and directories: api/, src/, data/, tests/, dashboard/, etc.
PART 5: CREATE THE CONDA ENVIRONMENT
5.1 Using Conda (Standard)
# Create environment from the verified environment.yml
conda env create -f environment.yml

# This will take 5-10 minutes
5.2 Using Mamba (Faster — Recommended if conda is slow)
# Install mamba first (one time)
conda install mamba -n base -c conda-forge -y

# Create environment using mamba
mamba env create -f environment.yml

# This is significantly faster than conda
5.3 Activate the Environment
conda activate nfcc
Your prompt should now show: (nfcc)
5.4 Verify Python Version
python --version
# Should show: Python 3.10.20
5.5 Verify Installation
python test_environment.py
Expected output:
✅ Core imports successful
✅ Environment ready
PART 6: GOOGLE EARTH ENGINE AUTHENTICATION
6.1 Authenticate (One Time)
python -c "import ee; ee.Authenticate()"
Follow the browser instructions:
1.	A browser link will appear in the terminal
2.	Click the link (or copy it to your browser)
3.	Log into your Google account
4.	Grant permissions to Earth Engine
5.	Copy the verification code back to the terminal
6.2 Verify GEE Works
python -c "import ee; ee.Initialize(); print('✅ GEE Ready')"
Expected output: ✅ GEE Ready
________________________________________
PART 7: VERIFY EVERYTHING WORKS
python test_environment.py
Expected output:
Testing imports...
✅ Core imports successful
✅ Environment ready
If you see errors, go to Part 9 (Troubleshooting).
✅ Success Criteria for Today
•	Repository cloned
•	Conda/Mamba environment created
•	test_environment.py passes
•	GEE authenticated
•	CHIRPS data downloaded OR sample created
Reply in the team WhatsApp group: "Setup complete + CHIRPS ready"
________________________________________
PART 8: ENGINEERING WORKFLOW (IMPORTANT)
8.1 Branch Strategy
Branch	Purpose	Protection
main	Production code	❌ Never push directly
develop	Integration branch	❌ Never push directly
feature/*	Your work	✅ Create from develop, PR to develop

8.2 Daily Workflow
# 1. Always start from develop
git checkout develop
git pull origin develop

# 2. Create your feature branch
git checkout -b feature/your-name-task

# 3. Write code, make changes
# ... edit files ...

# 4. Stage and commit
git add .
git commit -m "description of what you did"

# 5. Push to GitHub
git push origin feature/your-name-task

# 6. Create Pull Request (in browser or using gh CLI)
gh pr create --base develop --head feature/your-name-task --title "Your Title"
8.3 Pull Request Requirements
Requirement	Why
CI must pass	Automated tests ensure quality
1 review approval	Another engineer checks your code
No merge conflicts	Branch must be up to date with develop

8.4 CI/CD Pipeline
What runs automatically on every PR:
1.	Python 3.10 setup
2.	System dependencies (GDAL)
3.	Python package installation
4.	Unit tests (pytest tests/)
5.	Environment verification (test_environment.py)
Check CI status:
•	In PR page: Look for "All checks have passed" ✅
•	Or go to: https://github.com/NFCC-Ghana/nfcc-platform/actions
________________________________________
PART 9: TROUBLESHOOTING
Problem	Solution
conda: command not found	Restart terminal. Reinstall Miniconda.
Permission denied (publickey)	SSH key not added to GitHub (see Part 3)
environment.yml not found	Run git pull to get latest files
test_environment.py fails	Run conda env create -f environment.yml --force
ee.Initialize() fails	Run python -c "import ee; ee.Authenticate()" again
ModuleNotFoundError: geopandas	Run conda install geopandas -c conda-forge
GitHub Actions failing	Check PR for syntax errors; CI logs are public
VS Code not showing WSL	Install WSL extension, then Ctrl+Shift+P → "WSL: Connect"
Mamba not found	Run conda install mamba -n base -c conda-forge
CHIRPS download timeout	Use fallback script (create_sample_rainfall.py)

________________________________________
PART 10: VS CODE + WSL SETUP (WINDOWS USERS ONLY)
If you are using Windows, this is critical.
10.1 Install WSL
powershell
# Open PowerShell as Administrator
wsl --install
# Restart your computer
10.2 Install Ubuntu
After restart, Ubuntu will launch automatically. Create a username and password.
10.3 Connect VS Code to WSL
1.	Open VS Code
2.	Press Ctrl+Shift+P
3.	Type: WSL: Connect to WSL
4.	Select the Ubuntu distribution
Your VS Code bottom-left corner should show: WSL: Ubuntu
10.4 Verify VS Code Terminal
Open VS Code terminal (Ctrl+``). The prompt should show:
username@computer-name:~$
If you see PS C:\..., you are in Windows, not WSL. Close and reconnect.
________________________________________
📚 PART 11: PROJECT STRUCTURE OVERVIEW
nfcc/
├── api/                 → FastAPI backend (endpoints, routes)
├── configs/             → YAML configuration files
├── dashboard/           → Streamlit frontend
├── data/
│   ├── raw/             → Raw data (CHIRPS, SRTM, OSM)
│   ├── processed/       → Cleaned, ML-ready data (Parquet)
├── docs/                → Documentation
├── models/              → Saved model files (.pkl, .joblib)
├── notebooks/           → Jupyter notebooks for exploration
├── scripts/             → Utility scripts
├── src/
│   ├── data/
│   │   ├── ingestion/   → Download scripts
│   │   └── processing/  → Clean/transform scripts
│   ├── features/        → Feature engineering
│   ├── models/          → Model training
│   └── utils/           → Shared utilities
├── tests/               → Unit and integration tests
└── .github/workflows/   → CI/CD pipelines
PART 12: SUPPORT & COMMUNICATION
Channel	Purpose	When to Use
WhatsApp Group	Quick questions, blockers, daily check-ins	Urgent issues, quick help
GitHub Issues	Bug reports, feature requests	Technical problems, code discussions
Pull Requests	Code review	When code is ready to merge
Weekly Sync (Friday 4pm GMT)	Team coordination, progress updates	Blockers, planning, demos

✅ PART 14: FINAL CHECKLIST
Before you say "Setup Complete", confirm:
•	Git installed (git --version)
•	VS Code installed with Python + WSL extensions
•	Miniconda installed (conda --version)
•	SSH key generated and added to GitHub
•	Repository cloned (git clone git@github.com:NFCC-Ghana/nfcc-platform.git)
•	Conda/Mamba environment created (conda env create -f environment.yml)
•	Environment activated (conda activate nfcc)
•	test_environment.py passes
•	Google Earth Engine authenticated (ee.Authenticate())
•	Branch workflow understood (develop → feature/* → PR)
•	CI/CD pipeline understood (automated testing on PRs)
Engineering Rules (MANDATORY)
•	Work from develop branch
git checkout develop
•	Create your own feature branch
git checkout -b feature/your-task
•	Never push directly to main
•	All work goes through Pull Requests → develop

SYSTEM MENTAL MODEL
Component	Meaning
develop	Active development branch
main	Production-ready code
nfcc env	Python execution environment
PR	Code review mechanism
CI/CD	Automated validation system

What happens next
After CHIRPS is confirmed:
Role	Task
Data Engineers	Build ingestion pipelines
Geospatial Engineers	Start grid + raster processing
ML Engineers	Begin feature matrix
Backend	API skeleton
Frontend	Dashboard skeleton

FINAL SYSTEM STATE
You are working in a:
•	✅ Fully reproducible ML environment 
•	✅ Production-grade Git workflow 
•	✅ CI/CD enabled repository 
•	✅ Geospatial + AI pipeline ready system
WHAT WE ARE BUILDING TOGETHER
Model	Description	Timeline
Model 1	XGBoost flood probability (MVP)	Months 4-6
Model 2	Rainfall nowcasting (0-6hr)	Months 6-9
Model 3	Dam spillage prediction (Akosombo)	Months 5-8
Model 4	Urban inundation mapping	Months 10+

The data pipeline (CHIRPS, SRTM, OSM) must be completed first — unblocks all ML work.
Technical Lead(Zziem)
NFCC Project

