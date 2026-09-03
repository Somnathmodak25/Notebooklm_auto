import asyncio
import os
import sys
from notebooklm import NotebookLMClient
from notebooklm._types.enums import VideoFormat, VideoStyle

async def main():
    print("==================================================")
    print("STEP 1: Initializing NotebookLM Client & Auth...")
    print("==================================================")
    async with NotebookLMClient.from_storage("storage/tokens/main_storage_state.json") as client:
        # 1. Create a dedicated notebook for the AI Tech Documentary
        notebook_title = "Frontier AI Agents: The Rise of Autonomous Machine Intelligence"
        print(f"\nCreating notebook: '{notebook_title}'...")
        nb = await client.notebooks.create(notebook_title)
        notebook_id = getattr(nb, "id", str(nb))
        print(f"Created Notebook ID: {notebook_id}")

        # 2. Add in-depth documentary research sources
        print("\n==================================================")
        print("STEP 2: Ingesting Authoritative Research Sources...")
        print("==================================================")

        source_1_title = "The Architecture of Autonomous AI Agents: Reasoning & Test-Time Compute"
        source_1_content = """# The Architecture of Autonomous AI Agents: Reasoning, Planning, and Test-Time Compute

## 1. The Paradigm Shift: From Predictors to Reasoners
Artificial Intelligence has transitioned from simple next-token auto-regressive prediction to autonomous reasoning agents capable of deliberate System-2 thinking. Instead of instantaneous responses, frontier reasoning models utilize test-time compute scaling—spending dynamic compute budgets searching through multi-step solution paths, evaluating counterfactuals, and verifying logical consistency before producing output.

### Key Algorithmic Foundations:
- **Search-Guided Reasoning**: Employing Monte Carlo Tree Search (MCTS), beam search, and self-correction rollouts during inference.
- **Process Supervision vs. Outcome Supervision**: Models trained with Process-supervised Reward Models (PRMs) evaluate each intermediate step of deduction, dramatically reducing hallucinations in complex symbolic logic and mathematics.
- **Dynamic Thought Pacing**: Models allocate varying tokens of hidden scratchpad thinking based on query difficulty.

## 2. Agentic Workflow Topologies
Single-turn prompting has been supplanted by structured agent loops:
- **ReAct (Reason + Act)**: The model iteratively generates reasoning traces, selects an action, executes it in an external environment, and observes the feedback.
- **Reflexion and Metacognition**: Autonomous feedback loops where agents critique their intermediate failures, update internal memory buffers, and retry tasks with revised hypotheses.
- **Hierarchical Multi-Agent Systems**: Decomposition of grand goals into sub-tasks distributed across specialized persona-based agents (e.g., Planner, Coder, Verifier, Synthesizer).
"""

        source_2_title = "Tool Augmentation, Environmental Grounding & Model Context Protocol (MCP)"
        source_2_content = """# Tool Augmentation, Grounded Interaction, and Protocol Standards

## 1. Escaping the Static Context Window
Foundation models inherently suffer from knowledge cutoff and inability to affect the real world. Tool augmentation provides sensory grounding and operational agency:
- **API and Tool Use**: Dynamic tool calling enabling agents to run terminal commands, execute Python in isolated sandboxes, query relational databases, and browse live web pages.
- **The Model Context Protocol (MCP)**: An open universal standard creating bidirectional bridges between AI clients and local/remote developer tools, cloud data lakes, code repositories, and operational infrastructure.

## 2. Computer-Use & Vision-Action Agents
Frontier multimodal models now process visual UI states in real time:
- **Visual Grounding**: Identifying coordinates of buttons, text boxes, and dropdown menus through high-resolution screenshot parsing.
- **Virtual Keystrokes & Clicks**: Operating desktop applications, IDEs, and browser workflows without pre-existing APIs, simulating human-level computer interaction.
- **Self-Healing Automation**: When an unexpected modal or page layout appears, the agent inspects the DOM or visual hierarchy, reasons through the discrepancy, and adjusts its mouse trajectory.
"""

        source_3_title = "Autonomous Memory Systems, Multi-Agent Collaboration & Future Horizons"
        source_3_content = """# Memory Architecture, Industrial Agent Fleets, and Societal Horizons

## 1. The Three-Tiered Memory Architecture
For continuous autonomous operation across days and weeks, agents implement tri-fold memory:
- **Working Memory**: In-context tokens, system instructions, and immediate scratchpad thoughts.
- **Episodic & Experiential Memory**: Vector-indexed logs of past actions, successes, and failed attempts retrieved via semantic and BM25 hybrid search.
- **Semantic / Procedural Knowledge**: Consolidated guidelines, learned skills, and code templates synthesized from repeated tasks.

## 2. Real-World Applications & The Agentic Economy
- **Autonomous Software Engineering**: Agents that ingest entire GitHub codebases, reproduce reported issues, generate unit tests, patch bugs, and open verified pull requests.
- **Scientific Discovery & Drug Design**: Iterative hypothesis formulation, molecular simulation runs, and automated synthesis pipeline orchestration.
- **Enterprise Operations**: Autonomous financial auditing, customer support escalation management, and supply chain logistics optimization.

## 3. Safety, Alignment, and Agentic Containment
- **Prompt Injection & Sandbox Security**: Preventing indirect prompt injection attacks from adversarial web content.
- **Autonomous Alignment**: Ensuring goal-stability, preventing reward-hacking, and maintaining human-in-the-loop oversight for high-consequence operations.
"""

        print(f"Adding Source 1: '{source_1_title}'...")
        await client.sources.add_text(notebook_id, source_1_title, source_1_content)

        print(f"Adding Source 2: '{source_2_title}'...")
        await client.sources.add_text(notebook_id, source_2_title, source_2_content)

        print(f"Adding Source 3: '{source_3_title}'...")
        await client.sources.add_text(notebook_id, source_3_title, source_3_content)

        # 3. Web research run through NotebookLM
        print("\n==================================================")
        print("STEP 3: Initiating Web Research via NotebookLM...")
        print("==================================================")
        try:
            research_query = "Autonomous AI agents test time compute reasoning MCP tool use 2026"
            print(f"Starting research query: '{research_query}'...")
            r_start = await client.research.start(notebook_id, query=research_query, source="web", mode="fast")
            task_id = getattr(r_start, "task_id", str(r_start))
            print(f"Research task started: {task_id}. Waiting for completion...")
            r_task = await client.research.wait_for_completion(notebook_id, task_id, timeout=120)
            discovered = getattr(r_task, "sources", [])
            print(f"Research completed! Discovered {len(discovered)} web sources.")
            if discovered:
                print(f"Importing {len(discovered[:3])} top sources into notebook...")
                await client.research.import_sources(notebook_id, task_id, sources=discovered[:3])
                print("Discovered sources imported successfully!")
        except Exception as e:
            print(f"Web research note: {e} (continuing with comprehensive structured research sources).")

        # 4. Verify total sources and readiness
        print("\n==================================================")
        print("STEP 4: Verifying Notebook Content Depth & Context...")
        print("==================================================")
        nb_details = await client.notebooks.get(notebook_id)
        current_sources = getattr(nb_details, "sources", [])
        print(f"Total Sources in Notebook: {len(current_sources)}")
        for i, s in enumerate(current_sources, 1):
            print(f"  {i}. {getattr(s, 'title', getattr(s, 'id', str(s)))}")

        if len(current_sources) >= 2:
            print("\n[OK] Notebook has rich, authoritative, multidimensional content for a high-production documentary video overview.")
        else:
            print("\n[!] Warning: Source count low, proceeding with available content.")

        # 5. Generate Documentary-Grade Video Overview
        print("\n==================================================")
        print("STEP 5: Generating Documentary-Style Video Overview...")
        print("==================================================")

        documentary_instructions = (
            "Create a captivating, high-impact tech documentary overview about the revolution of Autonomous AI Agents. "
            "Adopt the storytelling tone of an authoritative science and technology documentary (like PBS NOVA or BBC Horizon). "
            "Structure the narrative into clear thematic acts: "
            "1. The Awakening: Moving from simple text predictors to deliberate System-2 thinking and test-time compute search. "
            "2. Breaking the Digital Boundary: Giving AI hands and eyes through tool calling, Model Context Protocol (MCP), and computer vision UI control. "
            "3. Multi-Agent Ecosystems & Memory: How specialized agent collectives collaborate with working, episodic, and procedural memory. "
            "4. The Horizon: Transforming software engineering, scientific discovery, and the profound questions of safety and alignment. "
            "Keep the explanations rigorous, intuitive, and visually vivid, avoiding shallow buzzwords."
        )

        print("Dispatching video generation request with custom documentary instructions...")
        # We invoke generate_video with EXPLAINER format and CLASSIC style
        status = await client.artifacts.generate_video(
            notebook_id=notebook_id,
            language="en",
            video_format=VideoFormat.EXPLAINER,
            video_style=VideoStyle.CLASSIC,
            instructions=documentary_instructions,
        )
        task_id = getattr(status, "task_id", str(status))
        print(f"\nSUCCESS! Video generation task created.")
        print(f"Task ID: {task_id}")
        print(f"Status: {getattr(status, 'status', 'QUEUED')}")

        print("\n==================================================")
        print("COMPLETION SUMMARY:")
        print(f"Notebook Title: {notebook_title}")
        print(f"Notebook ID:    {notebook_id}")
        print(f"Artifact Type:  Documentary Video Overview (Explainer/Classic)")
        print(f"Task ID:        {task_id}")
        print("==================================================")

if __name__ == "__main__":
    asyncio.run(main())
