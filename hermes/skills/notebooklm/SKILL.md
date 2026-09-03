---
name: notebooklm-hermes
description: Comprehensive autonomous operational skill for Hermes AI to control Google NotebookLM. Enables creating and managing notebooks, ingesting sources (text, URLs, files), executing fast and deep web research, performing grounded chat quality verification, and producing full Studio media artifacts (Documentary Video Overviews, Cinematic Videos, Infographics, Slide Decks, Audio Podcasts, and Reports).
---

# Hermes AI: Autonomous NotebookLM Mastery Skill

You are an expert autonomous operator of **Google NotebookLM**. You have full-spectrum control over NotebookLM via the `hermes/hermes_notebooklm.py` runner, the underlying `notebooklm` Python API, and the FastAPI Gateway.

Your goal is to autonomously conduct research, ingest and evaluate knowledge, verify factual coverage through grounded chat analysis, and produce high-impact Studio media (documentary videos, infographics, slide decks, podcasts, and briefing reports) without requiring manual human intervention.

---

## 1. Authentication & Operational Invariants

### 1.1 Authentication Model (Master Token)
- The system operates via a **Google Master Token** stored at `~/.notebooklm/profiles/default/master_token.json` (or `storage/tokens/master_token.json`).
- **Never ask the user for session cookies.** The master token automatically and silently re-mints fresh session cookies whenever Google invalidates temporary tokens.
- **Pre-flight Check:** If you suspect an auth issue, run:
  ```bash
  python -m notebooklm.notebooklm_cli auth check --test --json
  ```
  Verify `"status": "ok"` and `"checks.token_fetch": true`.

### 1.2 Operational Rules
1. **Always Retain UUIDs:** Every notebook, source, and generation task returns a UUID. Always preserve and pass explicit IDs (`--notebook-id`, `--source-id`, `--task-id`).
2. **Never Generate Media on Empty Context:** Always ensure the notebook contains at least 3–5 high-depth sources before requesting Video, Infographic, or Slide Deck generation.
3. **Verify Knowledge Quality Before Studio Dispatch:** Always run a grounded chat audit (`verify-quality`) before triggering long-running video or slide generation to ensure the notebook has sufficient factual density.
4. **Non-Blocking Execution:** Studio generation runs asynchronously on Google's backend (taking 3–7 minutes for Video). Retrieve task IDs immediately, poll periodically, and download when status reaches `COMPLETED` (status `3`).

---

## 2. Decision Engine (When to do What)

```mermaid
flowchart TD
    A[User Request] --> B{Existing Notebook Available?}
    B -->|Yes| C[Select / Inspect Notebook]
    B -->|No| D[Create New Dedicated Notebook]
    
    C --> E{Has Ingested Sources?}
    D --> F[Ingest Initial Structured Context]
    F --> G[Run Deep Web Research]
    E -->|No| F
    E -->|Yes, but thin| G
    E -->|Yes, sufficient| H[Run Grounded Chat Audit]
    
    G --> H
    H --> I{Quality & Depth Score >= 8/10?}
    I -->|No| J[Identify Missing Angles & Ingest More Data]
    J --> H
    I -->|Yes| K{Select Studio Media Target}
    
    K -->|Documentary Video| L[Dispatch Video Overview with Director Prompt]
    K -->|Visual Summary| M[Dispatch Infographic / Slide Deck]
    K -->|Audio Podcast| N[Dispatch Audio Overview]
    K -->|Briefing Document| O[Dispatch Comprehensive Report]
    
    L & M & N & O --> P[Poll Completion & Download to Media Directory]
```

---

## 3. Step-by-Step Playbooks

### Playbook 1: Notebook Lifecycle
- **List All Notebooks:**
  ```bash
  python hermes/hermes_notebooklm.py list
  ```
- **Create a New Notebook:**
  ```bash
  python hermes/hermes_notebooklm.py create --title "Frontier AI & Autonomous Systems"
  ```
- **Inspect Notebook & List Sources:**
  ```bash
  python hermes/hermes_notebooklm.py get --notebook-id <NOTEBOOK_ID>
  ```

---

### Playbook 2: Source Ingestion
Always supply rich, structured context. NotebookLM excels when given modular, thematic documents.

- **Add Structured Text / Markdown:**
  ```bash
  python hermes/hermes_notebooklm.py add-source --notebook-id <ID> --title "Core Architecture" --text "# Chapter 1..."
  ```
- **Add Live Web URLs:**
  ```bash
  python hermes/hermes_notebooklm.py add-source --notebook-id <ID> --url "https://example.com/research-paper"
  ```
- **Add Local Document Files (.pdf, .txt, .md):**
  ```bash
  python hermes/hermes_notebooklm.py add-source --notebook-id <ID> --file "./docs/whitepaper.pdf"
  ```

---

### Playbook 3: Autonomous Web Research
NotebookLM has built-in web research capability that searches Google, synthesizes findings, and extracts citations.

- **Run Fast Discovery (Quick overview):**
  ```bash
  python hermes/hermes_notebooklm.py research --notebook-id <ID> --query "Model Context Protocol MCP autonomous agents 2026" --mode fast --import-top 3
  ```
- **Run Deep Research (Comprehensive multi-hop search):**
  ```bash
  python hermes/hermes_notebooklm.py research --notebook-id <ID> --query "Test-time compute scaling Monte Carlo Tree Search frontier reasoning" --mode deep --import-top 5
  ```

---

### Playbook 4: Grounded Knowledge Verification & Quality Audit
Before spending Google compute credits on Studio generation, verify that the notebook can answer essential questions without hallucinations.

- **Run Automated Quality Audit:**
  ```bash
  python hermes/hermes_notebooklm.py verify-quality --notebook-id <ID> --topic "Autonomous AI Agents"
  ```
  *What this does:*
  1. Sends 3 targeted probes across Architecture, Practical Applications, and Future Challenges.
  2. Evaluates whether the answers cite sources and provide concrete mechanics rather than generic fluff.
  3. Returns a Readiness Score (`READY` or `NEEDS_MORE_SOURCES`).

---

### Playbook 5: Studio Media Production

#### 1. Documentary Video Overview (.mp4)
Produce a PBS NOVA / BBC Horizon style documentary video overview:
```bash
python hermes/hermes_notebooklm.py studio \
  --notebook-id <ID> \
  --type video \
  --format explainer \
  --style classic \
  --instructions "Adopt the tone of an authoritative science documentary (PBS NOVA / BBC Horizon). Structure into 4 acts: 1. The Awakening (System-2 reasoning & test-time search), 2. Breaking the Boundary (MCP tool use & computer vision UI control), 3. Multi-Agent Ecosystems & Memory, and 4. The Horizon (Transforming software & safety alignment). Focus on concrete technical mechanics." \
  --download \
  --output ./media/ai_documentary.mp4
```

#### 2. Visual Infographic
Generate structured infographic summaries:
```bash
python hermes/hermes_notebooklm.py studio \
  --notebook-id <ID> \
  --type infographic \
  --instructions "Focus on the architectural layers of autonomous AI agents: perception, reasoning, memory, and tool execution." \
  --download \
  --output ./media/agent_infographic.png
```

#### 3. Executive Slide Deck (.pdf)
Generate an executive presentation slide deck:
```bash
python hermes/hermes_notebooklm.py studio \
  --notebook-id <ID> \
  --type slide-deck \
  --instructions "Create a 10-slide executive briefing for CTOs and engineering leaders on adopting autonomous AI agents." \
  --download \
  --output ./media/executive_briefing.pdf
```

#### 4. Audio Overview Podcast (.mp3)
Generate a two-host deep-dive conversational podcast:
```bash
python hermes/hermes_notebooklm.py studio \
  --notebook-id <ID> \
  --type audio \
  --instructions "Engaging, conversational deep dive into frontier reasoning models and agentic workflows." \
  --download \
  --output ./media/podcast_overview.mp3
```

---

### Playbook 6: One-Shot Autonomous Pipeline
When asked to handle an entire project from scratch, use the unified pipeline:

```bash
python hermes/hermes_notebooklm.py pipeline \
  --topic "The Quantum Computing Leap: Fault-Tolerant Qubits and Practical Applications" \
  --research-mode deep \
  --generate video,infographic \
  --output-dir ./media
```

*The pipeline autonomously:*
1. Creates the notebook.
2. Ingests foundational research context.
3. Conducts deep web research and imports top cited sources.
4. Validates knowledge density via chat probing.
5. Dispatches video and infographic generation tasks.
6. Waits for completion and downloads the final media files.

---

## 4. Troubleshooting & Pro-Tips

- **Google Takes 3–7 Minutes for Video:** Do not terminate the process or re-dispatch. NotebookLM synthesizes custom AI voices, scripts, and video renders. Check status with `python hermes/hermes_notebooklm.py check-status --notebook-id <ID>`.
- **Concurrency:** If multiple agents run simultaneously, pass a unique profile: `NOTEBOOKLM_PROFILE=hermes-1 python hermes/hermes_notebooklm.py ...`.
- **Direct File Streaming:** The FastAPI Gateway at `http://127.0.0.1:8000` also exposes direct streaming endpoints (`/v1/notebooks/{id}/studio/video/download`) returning `video/mp4` and `application/pdf`.
