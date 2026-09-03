# Deploying NotebookLM Autonomous System to Hermes VPS

This guide provides step-by-step instructions for deploying the **NotebookLM Autonomous Automation System** to your Hermes VPS or remote Linux server.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    HERMES AI VPS                            │
│                                                             │
│  Hermes Agent Loop / OpenClaw / Claude Code                │
│    │                                                        │
│    ▼                                                        │
│  Hermes Skill (~/.hermes/skills/notebooklm/SKILL.md)        │
│    │                                                        │
│    ▼                                                        │
│  Runner (python hermes/hermes_notebooklm.py)                │
│    │                                                        │
│    ▼                                                        │
│  FastAPI Gateway (http://127.0.0.1:8000)                   │
│    │                                                        │
│    ▼                                                        │
│  Google Master Token (durable 1-year headless auth)         │
│    │                                                        │
│    ▼                                                        │
│  Google NotebookLM Cloud API                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Server Prerequisites & Installation

On your Hermes VPS (Ubuntu / Debian / CentOS / Arch):

```bash
# 1. Update package list & install Python 3.10+
sudo apt update && sudo apt install -y python3 python3-pip python3-venv git curl

# 2. Clone your repository
git clone https://github.com/Somnathmodak25/Notebooklm_auto.git
cd Notebooklm_auto

# 3. Create virtual environment & activate
python3 -m venv .venv
source .venv/bin/activate

# 4. Install dependencies with headless & server extras
pip install --upgrade pip
pip install -e ".[headless,server]"
pip install aiosqlite redis
```

---

## 3. Deploying the Master Token (No Manual Cookies)

Because you already generated a **1-year Master Token** on your machine, you never have to log into a browser on the VPS.

### Step 1: Copy your master token to the VPS
From your local Windows terminal (PowerShell), SCP your master token to your VPS:

```powershell
# Replace user@your-vps-ip with your actual VPS SSH credentials
scp ~/.notebooklm/profiles/default/master_token.json user@your-vps-ip:~/.notebooklm/profiles/default/master_token.json
```

Or paste its contents directly on the VPS:
```bash
mkdir -p ~/.notebooklm/profiles/default
chmod 700 ~/.notebooklm/profiles/default
nano ~/.notebooklm/profiles/default/master_token.json
# Paste your master token JSON here, save & exit (Ctrl+O, Enter, Ctrl+X)
chmod 600 ~/.notebooklm/profiles/default/master_token.json
```

### Step 2: Verify Authentication on the VPS
Run the verification check:
```bash
python3 -m notebooklm.notebooklm_cli auth check --test --json
```
Ensure it returns `"status": "ok"` and `"checks.token_fetch": true`.

---

## 4. Installing the Hermes AI Skill

To make Hermes recognize and automatically invoke NotebookLM:

```bash
# Register skill in Hermes / Claude / OpenClaw skills directory
mkdir -p ~/.hermes/skills/notebooklm
cp hermes/skills/notebooklm/SKILL.md ~/.hermes/skills/notebooklm/

# If your agent uses ~/.agents or ~/.claude:
mkdir -p ~/.agents/skills/notebooklm
cp hermes/skills/notebooklm/SKILL.md ~/.agents/skills/notebooklm/
```

Now, Hermes will automatically detect the skill and know how to autonomously:
1. Create and manage notebooks.
2. Ingest structured text, live URLs, and PDFs.
3. Conduct fast and deep AI web research.
4. Run grounded knowledge-verification chat audits.
5. Trigger Studio media (Documentary Video Overviews, Infographics, Slide Decks, Audio Podcasts).
6. Download and store finished assets in `./media/`.

---

## 5. Running the Background FastAPI Gateway

You can run the gateway as a background daemon or systemd service.

### Option A: Using systemd (Recommended for 24/7 VPS)

Create `/etc/systemd/system/notebooklm-gateway.service`:

```ini
[Unit]
Description=NotebookLM Automation FastAPI Gateway
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Notebooklm_auto
Environment="PATH=/root/Notebooklm_auto/.venv/bin"
ExecStart=/root/Notebooklm_auto/.venv/bin/python -m uvicorn gateway.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable notebooklm-gateway
sudo systemctl start notebooklm-gateway
sudo systemctl status notebooklm-gateway
```

### Option B: Quick background process
```bash
nohup python3 -m uvicorn gateway.main:app --host 127.0.0.1 --port 8000 > gateway.log 2>&1 &
```

Verify it's healthy:
```bash
curl http://127.0.0.1:8000/health
```

---

## 6. How Hermes Operates the CLI

Hermes can execute tasks via simple commands:

```bash
# 1. List notebooks
python3 hermes/hermes_notebooklm.py list

# 2. Create notebook
python3 hermes/hermes_notebooklm.py create --title "AI Robotics 2026"

# 3. Add source
python3 hermes/hermes_notebooklm.py add-source --notebook-id <ID> --url "https://arxiv.org/abs/example"

# 4. Deep research
python3 hermes/hermes_notebooklm.py research --notebook-id <ID> --query "Embodied AI foundation models" --mode deep --import-top 5

# 5. Quality audit
python3 hermes/hermes_notebooklm.py verify-quality --notebook-id <ID> --topic "Embodied AI"

# 6. Generate documentary video overview
python3 hermes/hermes_notebooklm.py studio --notebook-id <ID> --type video --format explainer --instructions "PBS NOVA style documentary" --download --output ./media/robotics.mp4

# 7. One-shot end-to-end pipeline
python3 hermes/hermes_notebooklm.py pipeline --topic "Next-Gen Quantum Computing" --research-mode deep --media video,slide-deck --output-dir ./media
```
