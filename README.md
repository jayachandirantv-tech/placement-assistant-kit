# Placement Assistant — Agentic AI

A Python-based **Agentic AI Placement Assistant** that demonstrates how an AI agent can use tools, maintain persistent memory, interact with placement-related data, and handle tasks through a structured agent workflow.

The project combines **LLM integration, tool calling, persistent memory, SQLite, notifications, append-only history, pagination, and automated testing**.

---

## 🚀 Project Overview

The project is organized into four main areas:

| Part   | Focus                                           |
| ------ | ----------------------------------------------- |
| Part 1 | Placement Tools                                 |
| Part 2 | AI Agent                                        |
| Part 3 | Persistent Memory                               |
| Labs   | Notifications, Append-Only History & Pagination |

The project also includes optional **stretch features** for additional agent capabilities.

---

## 🧩 Features

### Placement Tools

The Placement Assistant provides five core tools:

1. `check_eligibility`
2. `apply_to_drive`
3. `get_student`
4. `list_open_drives`
5. `book_interview_slot`

The tools operate on the placement data provided by the project.

### AI Agent

The agent:

* Receives natural-language questions
* Determines which tool is required
* Calls the appropriate tool
* Handles tool failures without crashing
* Records model and tool execution steps
* Maintains conversation history
* Supports a maximum step limit

### Persistent Memory

The agent can persist its state using **SQLite**.

Memory includes:

* Conversation messages
* Agent runs
* Model steps
* Tool calls
* Tool arguments and results
* Token usage
* Tool latency
* Run status
* Error information

The memory survives application restarts.

### Notifications

The project includes:

```text
notify_student(student_id, message)
```

The notification tool validates the student and message before sending the notification.

### Append-Only History

SQLite triggers are used to prevent existing conversation messages from being modified or deleted.

This ensures that the message history remains append-only.

### Pagination

Conversation history can be retrieved page by page using:

```text
page_messages(thread_id, after_seq=0, limit=20)
```

The implementation uses cursor-style pagination rather than `OFFSET`.

---

## 🏗️ Project Structure

```text
placement-assistant/
│
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── data.py
│   ├── domain.py
│   ├── memory.py
│   ├── notify.py
│   ├── providers.py
│   ├── verdict.py
│   │
│   └── tools/
│       ├── __init__.py
│       ├── dispatch.py
│       └── placement_tools.py
│
├── docs/
│   ├── lab1_ab.md
│   └── part3_design.md
│
├── schema/
│   ├── agent.sql
│   └── append_only.sql
│
├── scripts/
│   ├── __init__.py
│   ├── ab_descriptions.py
│   └── chat.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_lab1_notify.py
│   ├── test_lab2_append_only.py
│   ├── test_lab3_pagination.py
│   ├── test_part1_tools.py
│   ├── test_part2_agent.py
│   ├── test_part3_memory.py
│   ├── test_part3_schema.py
│   ├── test_stretch_my_applications.py
│   └── test_stretch_verdict.py
│
├── .env.example
├── HANDOUT.html
├── pytest.ini
├── README.md
└── requirements.txt
```

---

## 🔧 Core Components

### `app/domain.py`

Contains the core domain objects used by the Placement Assistant:

* Student
* Drive
* Rule
* Slot

### `app/data.py`

Contains the placement data and repository methods used by the tools.

The placement data is kept separate from the agent's persistent memory.

### `app/tools/placement_tools.py`

Contains the placement tools used by the agent.

### `app/tools/dispatch.py`

Handles model tool calls and dispatches them to the appropriate Python function.

It also handles common argument issues and invalid tool calls.

### `app/agent.py`

Contains the main agent implementation.

The agent follows a workflow similar to:

```text
User
  ↓
Agent
  ↓
LLM / Model
  ↓
Tool Call
  ↓
Tool Execution
  ↓
Tool Result
  ↓
LLM / Model
  ↓
Final Response
```

The agent also records a trace of model and tool steps.

### `app/memory.py`

Implements persistent agent memory using SQLite.

It stores:

```text
Thread
 ├── Messages
 └── Runs
      └── Run Steps
           └── Tool Calls
```

### `schema/agent.sql`

Defines the database schema for:

* `thread`
* `message`
* `run`
* `run_step`
* `tool_call`

### `schema/append_only.sql`

Contains SQLite triggers that prevent updates and deletes on conversation messages.

### `scripts/chat.py`

Provides a terminal interface for interacting with the Placement Assistant.

---

## 📊 Placement Data

The project contains sample students and placement drives used by the tools and tests.

### Students

| Roll No | Name            | Branch | CGPA | Backlogs | Graduation |
| ------- | --------------- | ------ | ---: | -------: | ---------: |
| 22CS045 | Priya Raman     | CSE    |  8.4 |        0 |       2026 |
| 22IT017 | Arjun Kumar     | IT     |  6.8 |        1 |       2026 |
| 22EC031 | Divya Sekar     | ECE    |  7.2 |        2 |       2026 |
| 22ME008 | Karthik Murugan | MECH   |  7.9 |        0 |       2026 |

### Placement Drives

| Drive | Company    | Role                   | Status |
| ----- | ---------- | ---------------------- | ------ |
| 1     | Zoho       | Member Technical Staff | Open   |
| 2     | TCS        | Ninja                  | Open   |
| 3     | Freshworks | Software Engineer I    | Closed |

The eligibility rules include conditions involving:

* CGPA
* Backlogs
* Branch
* Graduation year

---

## ⚙️ Requirements

* Python 3.10+
* Gemini API key
* pip
* SQLite
* pytest

SQLite is included with Python, so a separate database server is not required.

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/jayachandirantv-tech/placement-assistant-kit.git
cd placement-assistant-kit
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the environment

**Windows:**

```powershell
.venv\Scripts\activate
```

**Linux/macOS:**

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 🔑 Environment Configuration

Create a `.env` file using `.env.example` as the template.

Add your Gemini API key:

```env
GEMINI_API_KEY=your-key
```

**Do not commit `.env` or API keys to GitHub.**

---

## ▶️ Running the Assistant

### Mock Mode

Run the assistant using the scripted model without consuming Gemini API quota:

```bash
python -m scripts.chat --mock
```

### Gemini Mode

Run the assistant using Gemini:

```bash
python -m scripts.chat
```

### Run as a Specific Student

For example:

```bash
python -m scripts.chat --student 22IT017
```

### Run with Persistent Memory

```bash
python -m scripts.chat --db agent.db
```

The thread ID can be reused after restarting the application:

```bash
python -m scripts.chat --db agent.db --thread <thread_id>
```

---

## 🧪 Testing

The project uses **pytest**.

Run the complete test suite:

```bash
pytest
```

Run Part 1 tool tests:

```bash
pytest tests/test_part1_tools.py
```

Run agent tests:

```bash
pytest tests/test_part2_agent.py
```

Run memory tests:

```bash
pytest tests/test_part3_memory.py
```

Run schema tests:

```bash
pytest tests/test_part3_schema.py
```

Run the notification lab:

```bash
pytest tests/test_lab1_notify.py
```

Run the append-only history lab:

```bash
pytest tests/test_lab2_append_only.py
```

Run the pagination lab:

```bash
pytest tests/test_lab3_pagination.py
```

Run all tests with concise output:

```bash
pytest -q
```

The automated tests use a scripted model, so normal test execution does **not** consume Gemini API quota.

---

## 🧪 Labs

### Notification Tool

Implemented:

```text
notify_student(student_id, message)
```

The tool:

* Checks that the student exists
* Validates the message
* Rejects empty messages
* Rejects messages longer than 160 characters
* Sends the notification
* Returns a notification ID and queued status

### Append-Only History

SQLite triggers prevent:

```sql
UPDATE message ...
DELETE FROM message ...
```

from modifying conversation history.

The database itself enforces the append-only requirement rather than relying only on Python code.

### Pagination

The project implements cursor-based pagination:

```text
page_messages(thread_id, after_seq, limit)
```

It returns:

```text
(items, next_after)
```

The implementation avoids `OFFSET` and uses the message sequence number as the cursor.

---

## 🌟 Stretch Features

### List My Applications

A tool for retrieving a student's applications and interview information:

```text
list_my_applications(student_id)
```

### Typed Verdict

`app/verdict.py` contains support for structured eligibility verdicts using validation.

The verdict validates the relationship between:

```text
eligible
```

and:

```text
failed_rules
```

---

## 🧠 Agentic AI Concepts Demonstrated

This project provides practical implementation of:

* LLM-powered agents
* Tool calling
* Tool dispatch
* Agent loops
* Tool error handling
* Self-healing agent behavior
* Conversation state
* Persistent memory
* SQLite-backed memory
* Execution traces
* Model/tool steps
* Structured tool results
* Database transactions
* Append-only data
* Cursor pagination
* Automated testing
* Structured output validation

---

## 📚 Documentation

Additional documentation is available in:

```text
docs/
```

### Part 3 Design

```text
docs/part3_design.md
```

Contains the design decisions behind the agent's persistent memory.

### Lab Description Analysis

```text
docs/lab1_ab.md
```

Contains the tool-description experiment for the notification tool.

### Full Project Handout

The original project instructions are included in:

```text
HANDOUT.html
```

---

## 🎯 Learning Outcome

The Placement Assistant demonstrates how **LLMs, tools, application logic, and persistent memory** can be combined to build a practical agentic application.

The overall workflow is:

```text
Natural Language Query
        ↓
      Agent
        ↓
   Tool Selection
        ↓
   Tool Execution
        ↓
   Tool Result
        ↓
      Agent
        ↓
   Final Response
        ↓
 Persistent Memory
```

---

## 👨‍💻 Project Information

**Project:** Placement Assistant
**Focus:** Agentic AI, Tool Calling, Persistent Memory & Testing
**Language:** Python
**Database:** SQLite
