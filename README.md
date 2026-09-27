# AI Software Engineer Agent

An AI-powered software engineering agent that can understand a repository, retrieve relevant code using RAG, plan and implement changes, modify source files, generate and run tests, debug failures, and review the final implementation.

The system combines LLM reasoning, repository intelligence, autonomous coding workflows, and human approval to simulate a controlled AI software engineer.

## 🚀 Live Demo

**Streamlit App:**  
https://ai-software-engineer-agent-9bkubf8zicdzhp9rjcswtj.streamlit.app/

**GitHub Repository:**  
https://github.com/samirafathima27/AI-Software-Engineer-Agent

---

## ✨ Features

- 📂 Upload a software project as a ZIP file
- 🔎 Automatically index the uploaded repository
- 🧠 Semantic code search using RAG
- 🌳 Python AST-based code parsing
- 🧩 Code chunking and repository intelligence
- 🤖 AI-powered implementation planning
- ✍️ Automated source-code modification
- 🧪 Automated test generation and execution
- 🐛 Debug and retest workflow
- 👤 Human approval before implementation
- 🔍 Automated implementation review
- 🔄 LangGraph-based workflow orchestration
- 💾 Persistent workflow state using SQLite
- 🌐 Streamlit web interface
- 🐙 Git/GitHub integration

---

## 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │    Streamlit UI     │
                    │   User Task / ZIP    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Project Upload    │
                    │   & Safe Extraction │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Repository Indexing │
                    │   AST + Chunking    │
                    │    + Embeddings     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       RAG           │
                    │ Semantic Code Search│
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    LangGraph        │
                    │    Orchestrator     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌────────────┐   ┌────────────┐   ┌────────────┐
       │ Code Agent │   │ Test Agent │   │ Debug Agent│
       └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                    ┌─────────────────────┐
                    │ Human Approval      │
                    │     Checkpoint      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Code Changes      │
                    │   + Test Changes    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Test Execution     │
                    │       pytest         │
                    └──────────┬──────────┘
                               │
                         Tests Failed?
                          /          \
                        Yes           No
                         │             │
                         ▼             ▼
                  ┌────────────┐ ┌────────────┐
                  │ Debug Agent│ │Review Agent│
                  │  & Retest  │ └─────┬──────┘
                  └─────┬──────┘       │
                        │               ▼
                        └──────►   Final Result