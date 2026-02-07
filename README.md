# Adaptive Generative AI

A RAG (Retrieval-Augmented Generation) service that improves answer quality through **adaptive chunking** — an automated audit step that enriches each chunk with contextual information from its neighbors so it can stand on its own during retrieval.

---

## Table of Contents

1. [Why Adaptive Chunking](#1-why-adaptive-chunking)
2. [How It Works](#2-how-it-works)
3. [Architecture](#3-architecture)
4. [Tech Stack](#4-tech-stack)
5. [Project Structure](#5-project-structure)
6. [Getting Started](#6-getting-started)
7. [API Reference](#7-api-reference)
8. [Adaptive Chunking in Action](#8-adaptive-chunking-in-action)
9. [Configuration](#9-configuration)
10. [Design Decisions](#10-design-decisions)
11. [Trade-offs](#11-trade-offs)
12. [Limitations](#12-limitations)
13. [Future Improvements](#13-future-improvements)
14. [Author](#14-author)

---

## 1. Why Adaptive Chunking

RAG systems often retrieve chunks that are semantically similar to a query but lack enough context to be understood in isolation. If a chunk refers to "the project mentioned above" or lists bullet points without a heading, the LLM produces vague or incorrect answers.

This project adds a lightweight, automated audit step: a background agent reviews each chunk, compares it with its neighbors, and prepends minimal context (up to 2 sentences) so the chunk becomes self-contained. The result is more relevant retrieval and more accurate answers.

---

## 2. How It Works

1. **Upload** a PDF document via the API.
2. **Extract** text and split it into chunks using character-based boundaries with sentence awareness (800 chars min, 1600 overlap max).
3. **Embed** chunks with Ollama and store them in Qdrant, isolated per tenant.
4. **Audit** — a Celery background worker reviews each chunk against its neighbors and prepends minimal context to make it self-contained.
5. **Chat** — a chat agent retrieves relevant chunks and answers user questions using an agentic tool-use loop.
6. **Evaluate** — after each chat response, a retrieval evaluation agent checks chunk quality and triggers re-audits for weak chunks.

---

## 3. Architecture

```text
                        +-------------+
                        |    User     |
                        +------+------+
                               |
                               v
                     +-------------------+
                     |   FastAPI (API)   |
                     +----+--------+----+
                          |        |
              +-----------+        +-----------+
              |                                |
              v                                v
  +-----------+----------+         +-----------+---------+
  | POST /documents/upload|        |    POST /chat       |
  +-----------+----------+         +-----------+---------+
              |                                |
              v                                v
  +---------------------+         +---------------------+
  | PDF Text Extraction |         |     Chat Agent      |
  | (pdfplumber)        |         | (agentic tool-use)  |
  +-----------+---------+         +-----------+---------+
              |                                |
              v                                v
  +---------------------+         +---------------------+
  | Character Chunking  |         | Search Qdrant       |
  +-----------+---------+         +-----------+---------+
              |                                |
              v                                v
  +---------------------+         +---------------------+
  | Embed (Ollama)      |         | Generate Answer     |
  +-----------+---------+         | (Ollama Chat)       |
              |                   +-----------+---------+
              v                                |
  +---------------------+                      v
  | Store in Qdrant     |         +---------------------+
  +-----------+---------+         | Save Chat History   |
              |                   | (Redis)             |
              v                   +-----------+---------+
  +---------------------+                      |
  | Enqueue Audit Tasks |                      v
  | (Celery + Redis)    |         +---------------------+
  +-----------+---------+         | Evaluation Agent    |
              |                   +-----------+---------+
              v                                |
  +---------------------+                      v
  | Indexing Agent      |         +---------------------+
  | (Background Worker) |         | Re-audit Weak       |
  +-----------+---------+         | Chunks (Celery)     |
              |                   +---------------------+
              v
  +---------------------+
  | Audit + Enrich      |
  | Chunks in Qdrant    |
  +---------------------+
```

---

## 4. Tech Stack

| Component          | Technology                      |
| ------------------ | ------------------------------- |
| Language           | Python 3.12                     |
| Web Framework      | FastAPI + Uvicorn               |
| Task Queue         | Celery + Redis                  |
| Vector Database    | Qdrant v1.16.2                  |
| LLM / Embeddings   | Ollama (local or cloud)         |
| PDF Processing     | pdfplumber                      |
| Chat History       | Redis (24h TTL, last 20 msgs)   |
| Containerization   | Docker + Docker Compose         |

---

## 5. Project Structure

```
.
├── agent/
│   ├── chat_agent.py          # Agentic chat with tool-use loop
│   └── indexing_agent.py      # Chunk audit + retrieval evaluation agents
├── background_tasks/
│   └── celery_app.py          # Celery configuration
├── chat/
│   ├── chat_controller.py     # /chat endpoint router
│   ├── chat_dto.py            # Request/Response models
│   └── chat_service.py        # Chat orchestration
├── chat_history/
│   └── chat_history_service.py  # Redis-backed chat history
├── documents/
│   ├── documents_controller.py  # /documents endpoint router
│   ├── documents_dto.py         # Request/Response models
│   └── documents_service.py     # PDF extraction + chunking
├── embedding/
│   └── embedding_service.py   # Ollama embedding client
├── llm/
│   └── llm_service.py         # Ollama chat client (async + sync)
├── vector_db/
│   └── vector_db_service.py   # Qdrant operations (async + sync)
├── main.py                    # FastAPI app entrypoint
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example               # Local environment template
└── .env.docker.example        # Docker environment template
```

---

## 6. Getting Started

### 6.1 Prerequisites

- **Python 3.12+**
- **Ollama** running locally (or a cloud endpoint) with the required models pulled:
  - Embedding model: `llama3.2:1b`
  - Chat model: `deepseek-r1:7b` (or any preferred model)
- **Qdrant** and **Redis** (provided via Docker Compose, or run separately for local setup)

### 6.2 Run with Docker (Recommended)

1. Copy the environment file and adjust values:

   ```bash
   cp .env.docker.example .env.docker
   ```

2. Ensure Ollama is running on the host with the required models available.

3. Start the stack:

   ```bash
   docker compose up --build
   ```

4. Services will be available at:

   | Service | URL                     |
   | ------- | ----------------------- |
   | API     | http://localhost:8001    |
   | Docs    | http://localhost:8001/docs |
   | Qdrant  | http://localhost:6333    |
   | Redis   | localhost:6379           |

### 6.3 Run Locally (Without Docker)

1. Create a virtualenv and install dependencies:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate        # Windows
   # source .venv/bin/activate   # Linux/macOS
   pip install -r requirements.txt
   ```

2. Copy and configure the environment file:

   ```bash
   cp .env.example .env
   ```

3. Start Qdrant, Redis, and Ollama locally.

4. Run the API server and Celery worker in separate terminals:

   ```bash
   # Terminal 1 — API
   uvicorn main:app --host 0.0.0.0 --port 8000

   # Terminal 2 — Background Worker
   celery -A background_tasks.celery_app:celery_app worker -c 2 -l INFO
   ```

---

## 7. API Reference

### 7.1 Upload Document

```
POST /api/v1/documents/upload
Content-Type: multipart/form-data
```

| Field         | Type   | Default      | Description             |
| ------------- | ------ | ------------ | ----------------------- |
| `tenant`      | string | `tenant_0`   | Tenant identifier       |
| `document_id` | string | `document_0` | Document identifier     |
| `file`        | file   | *(required)* | PDF file to upload      |

**Example:**

```bash
curl -X POST "http://localhost:8001/api/v1/documents/upload" \
  -F "tenant=tenant_0" \
  -F "document_id=document_0" \
  -F "file=@./path/to/file.pdf"
```

**Response:**

```json
{
  "result": "File Indexing Success"
}
```

### 7.2 Chat

```
POST /api/v1/chat
Content-Type: application/json
```

| Field     | Type   | Description                  |
| --------- | ------ | ---------------------------- |
| `query`   | string | The question to ask          |
| `tenant`  | string | Tenant identifier            |
| `user_id` | string | User identifier for history  |

**Example:**

```bash
curl -X POST "http://localhost:8001/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?", "tenant": "tenant_0", "user_id": "user_0"}'
```

**Response:**

```json
{
  "question": "What is this document about?",
  "answer": "...",
  "ritrieved_documents": [...],
  "prompt_used": [...],
  "token_usage_estimation": 1234
}
```

---

## 8. Adaptive Chunking in Action

Below is an example showing how the audit process enriches a chunk. The `original_text` is the raw chunk extracted from the PDF. The `audited_text` contains contextual information prepended by the indexing agent.

**Models used in this example:**

| Role | Model |
| --- | --- |
| Embedding | `llama3.2:1b` (local) |
| Indexing Agent (audit) | `qwen3-coder:480b` (Ollama cloud) |

<details>
<summary>Click to expand example</summary>

**Original text (raw chunk):**

```
Makasar, Purwakarta, Yogyakarta and others.
• Design Logic Software and Web-based monitoring system for Level Crossings
  and Platform Screen Doors.
▪ Developed real-time dashboards and historical logs using
  JavaScript/HTML/CSS hosted on Weidmüller Node-RED.
▪ Enabling effective fault detection and maintenance support.
▪ Delivered design for Padang, Lahat–Lubuklinggau, and Gedebage–Haurpugur
  Level Crossings. LRT Jabodebek and LRT Jakarta Phase 1B Platform Screen
  Door systems.
• Develop auto-code generation tools for PLC programming.
▪ Built Python + Qt applications to generate source code for HIMA and
  Siemens IDEs
▪ Reducing design time by ~90%. Improving accuracy and enforcing
  safety-critical software standards.
• Automate Interlocking Table drawings in AutoCAD.
▪ Used Python with the ActiveX API to generate DWG diagrams automatically
  from interlocking data
```

**Audited text (context added by indexing agent):**

```
Part of Logic Software Team, Railway Signaling Division. The team designs
safety-critical Logic Software for Railway Signaling Systems, including SCADA
and Traffic Control System integration.

The work was conducted as part of the Logic Software Team within the Railway
Signaling Division, which focuses on safety-critical systems such as SCADA
and Traffic Control System integration. This team is responsible for designing
and developing software solutions that ensure safe and efficient railway
operations in locations including Makasar, Purwakarta, Yogyakarta, Padang,
Lahat–Lubuklinggau, Gedebage–Haurpugur, and LRT projects in Jabodebek and
Jakarta Phase 1B.
```

**Final chunk text (audited_text + original_text combined):**

The `text` field stored in Qdrant is the concatenation of `audited_text` and `original_text`. This is the actual content used for embedding and retrieval:

```
Part of Logic Software Team, Railway Signaling Division. The team designs
safety-critical Logic Software for Railway Signaling Systems, including SCADA
and Traffic Control System integration.

The work was conducted as part of the Logic Software Team within the Railway
Signaling Division, which focuses on safety-critical systems such as SCADA
and Traffic Control System integration. This team is responsible for designing
and developing software solutions that ensure safe and efficient railway
operations.

The work involved designing logic software and web-based monitoring systems
for Level Crossings and Platform Screen Doors in various locations including
Makasar, Purwakarta, Yogyakarta, Padang, Lahat–Lubuklinggau,
Gedebage–Haurpugur, and LRT projects in Jabodebek and Jakarta Phase 1B.

The work was conducted as part of the Logic Software Team within the Railway
Signaling Division, which focuses on safety-critical systems such as SCADA
and Traffic Control System integration. This team is responsible for designing
and developing software solutions that ensure safe and efficient railway
operations in locations including Makasar, Purwakarta, Yogyakarta, Padang,
Lahat–Lubuklinggau, Gedebage–Haurpugur, and LRT projects in Jabodebek and
Jakarta Phase 1B.

The work was conducted as part of the Logic Software Team within the Railway
Signaling Division, which focuses on safety-critical systems such as SCADA
and Traffic Control System integration. This team is responsible for designing
and developing software solutions that ensure safe and efficient railway
operations in locations including Makasar, Purwakarta, Yogyakarta, Padang,
Lahat–Lubuklinggau, Gedebage–Haurpugur, and LRT projects in Jabodebek and
Jakarta Phase 1B.
Makasar, Purwakarta, Yogyakarta and others.
• Design Logic Software and Web-based monitoring system for Level Crossings
  and Platform Screen Doors.
▪ Developed real-time dashboards and historical logs using
  JavaScript/HTML/CSS hosted on Weidmüller Node-RED.
▪ Enabling effective fault detection and maintenance support.
▪ Delivered design for Padang, Lahat–Lubuklinggau, and Gedebage–Haurpugur
  Level Crossings. LRT Jabodebek and LRT Jakarta Phase 1B Platform Screen
  Door systems.
• Develop auto-code generation tools for PLC programming.
▪ Built Python + Qt applications to generate source code for HIMA and
  Siemens IDEs
▪ Reducing design time by ~90%. Improving accuracy and enforcing
  safety-critical software standards.
• Automate Interlocking Table drawings in AutoCAD.
▪ Used Python with the ActiveX API to generate DWG diagrams automatically
  from interlocking data
```

The original chunk starts mid-sentence ("Makasar, Purwakarta...") and lacks context about what team or division the work belongs to. The audited version prepends context from neighboring chunks, making the chunk self-contained for retrieval and answering.

**How the three fields relate:**

| Field | Content | Purpose |
| --- | --- | --- |
| `original_text` | Raw chunk from PDF | Preserved as-is, never modified |
| `audited_text` | Context sentences added by the indexing agent | Grows with each audit pass |
| `text` | `audited_text` + `original_text` | Used for embedding and retrieval |

</details>

---

## 9. Configuration

Copy one of the example env files and adjust values as needed:

```bash
# For Docker
cp .env.docker.example .env.docker

# For local development
cp .env.example .env
```

### 9.1 Environment Variables

| Variable                     | Description                          | Default                              |
| ---------------------------- | ------------------------------------ | ------------------------------------ |
| `OLLAMA_LOCAL_HOST`          | Local Ollama server URL              | `http://host.docker.internal:11434`  |
| `OLLAMA_CLOUD_HOST`          | Cloud Ollama endpoint                | `https://ollama.com`                 |
| `OLLAMA_EMBED_MODEL`         | Model for embeddings                 | `llama3.2:1b`                        |
| `OLLAMA_CHAT_MODEL`          | Model for chat completions           | `deepseek-r1:7b`                     |
| `OLLAMA_INDEXING_AGENT_MODEL`| Model for chunk audit agent          | `deepseek-r1:7b`                     |
| `OLLAMA_API_KEY`             | API key for cloud Ollama             | —                                    |
| `QDRANT_HOST`                | Qdrant server hostname               | `qdrant` (Docker) / `localhost`      |
| `QDRANT_PORT`                | Qdrant REST port                     | `6333`                               |
| `QDRANT_ID_NAMESPACE`        | UUID namespace for point IDs         | *(see .env.example)*                 |
| `REDIS_HOST`                 | Redis hostname                       | `redis` (Docker) / `localhost`       |
| `REDIS_PORT`                 | Redis port                           | `6379`                               |
| `REDIS_PASSWORD`             | Redis password                       | `redis`                              |
| `CELERY_BROKER_URL`          | Celery broker connection string      | `redis://:password@redis:6379/0`     |
| `CELERY_RESULT_BACKEND`      | Celery result backend connection     | `redis://:password@redis:6379/1`     |

---

## 10. Design Decisions

### 10.1 Why Character-Based Chunking Instead of Semantic Chunking

The chunking strategy uses character count with sentence-aware boundaries (min 800 chars, max 1600 chars) rather than semantic or token-based splitting. This was intentional:

- **Predictable chunk sizes** — character-based chunking guarantees consistent vector payload sizes, which simplifies Qdrant storage planning and keeps embedding costs uniform.
- **Sentence-aware breaks** — the chunker only splits at sentence boundaries (`.` or `\n`), preventing mid-sentence cuts that would degrade both embedding quality and readability.
- **Context is added later, not during chunking** — instead of trying to produce perfect chunks at split time (which is hard to get right), the system delegates context enrichment to a background LLM agent. This separates the fast, deterministic chunking step from the slow, intelligent enrichment step.

---

### 10.2 Why an Agentic Chat Loop Instead of a Single Retrieval Call

The chat agent (`chat_agent.py`) runs an agentic tool-use loop (up to 15 iterations) rather than doing a single embed-and-search. The agent decides:

- **What query to use** — it can rephrase the user's question for better retrieval.
- **How many chunks to retrieve** — it adjusts the `limit` parameter based on question complexity.
- **Whether to retrieve at all** — if the question can be answered from chat history alone, it skips retrieval entirely.
- **When to stop** — it can do multiple retrieval rounds, refining results before generating a final answer.

This design lets small local models (7B) compensate for retrieval limitations through iteration.

---

### 10.3 Why Background Tasks (Celery)

The system runs two categories of work that don't belong inside an API request: **chunk auditing** after document upload, and **retrieval evaluation** after every chat response. Both are handled by Celery workers backed by Redis as the message broker.

#### 10.3.1 The Problem with Doing Everything Inline

Consider what happens when a user uploads a 30-page PDF:

1. Extract text — fast (~1 second).
2. Chunk into ~20–40 pieces — fast (milliseconds).
3. Embed all chunks with Ollama — moderate (~5–15 seconds depending on hardware).
4. Audit each chunk against its neighbors — **slow** (each chunk requires multiple LLM calls, one per neighbor).

For a document with N chunks, the audit step alone produces roughly N*(N-1)/2 LLM calls. A 30-chunk document means ~435 LLM calls. At ~2 seconds per call on a local 7B model, that's ~15 minutes of work. No user should wait 15 minutes for an upload response.

The same problem applies to retrieval evaluation after chat. The evaluation agent reviews every retrieved chunk, decides which ones need re-auditing, and triggers new audit tasks. This is useful work, but it has no business blocking the chat response.

#### 10.3.2 How Background Tasks Solve This

```text
Upload Request                    Background (Celery)
─────────────                     ───────────────────
Extract text
Chunk text
Embed chunks
Store in Qdrant
Enqueue audit tasks ──────────►   audit_chunk(chunk_0)
Return "Success"                  audit_chunk(chunk_1)
                                  audit_chunk(chunk_2)
                                  ...
                                  (chunks improve over time)

Chat Request                      Background (Celery)
────────────                      ───────────────────
Retrieve chunks
Generate answer
Save chat history
Return answer
Enqueue evaluation ───────────►   background_evaluation_agent()
                                      │
                                      ▼
                                  (if weak chunks found)
                                  audit_chunk(chunk_X, extra_prompt)
                                  audit_chunk(chunk_Y, extra_prompt)
```

The API returns immediately. Background workers pick up tasks from the Redis queue and process them at their own pace.

#### 10.3.3 Why Celery Specifically

- **Task-level granularity** — each chunk audit is an independent Celery task (`audit_chunk.delay(tenant, doc_id, chunk_idx)`). This means chunks are audited in parallel across workers, and a failure in one chunk doesn't block others.
- **Built-in retry** — Celery supports automatic retry with backoff. If Ollama is temporarily overloaded, the task retries instead of failing permanently.
- **Concurrency control** — the worker runs with `-c 2` (2 concurrent workers). This limits how many LLM calls hit Ollama at once, preventing resource exhaustion on machines with limited GPU memory.
- **Task chaining** — the evaluation agent can dynamically enqueue new audit tasks with additional context (`addtional_prompt`), creating a feedback loop without complex orchestration code.
- **Separation of concerns** — the API process (`uvicorn`) handles HTTP requests. The worker process (`celery`) handles heavy computation. They share no state except Redis (queue) and Qdrant (data).

#### 10.3.4 The Two Background Tasks

**1. `audit_chunk`** — triggered after document upload

For each chunk, the agent iterates over every previous chunk (from the nearest to the farthest) and the next chunk. For each neighbor, it asks the LLM: "Does the target chunk need context from this neighbor to make sense?" If yes, it prepends up to 2 sentences of context and updates the chunk in Qdrant (re-embedding with the enriched text).

```
audit_chunk(tenant="tenant_0", doc_id="document_0", chunk_idx=5)
  → compare chunk 5 with chunk 4, 3, 2, 1, 0, then chunk 6
  → append context where needed
  → re-embed and update chunk 5 in Qdrant
```

**2. `background_evaluation_agent`** — triggered after every chat response

After the chat agent returns an answer, this task evaluates the retrieved chunks against 8 quality criteria (unclear context, low relevance, duplicated content, high score but not answerable, etc.). If it finds weak chunks, it enqueues new `audit_chunk` tasks with a custom `addtional_prompt` that tells the audit agent specifically what context is missing.

This creates a **self-improving loop**: the more users ask questions, the more the system discovers and fixes weak chunks.

```
User asks question
  → chat agent retrieves chunks A, B, C
  → returns answer
  → evaluation agent reviews A, B, C
  → chunk B is unclear → enqueue audit_chunk(B, "add project name context")
  → next time B is retrieved, it has better context
```

#### 10.3.5 Why Not Threads, asyncio.create_task, or subprocess

| Alternative | Why Not |
| --- | --- |
| `threading` / `asyncio.create_task` | Runs inside the API process. If the process restarts or crashes, all in-progress tasks are lost. No persistence, no retry, no visibility into task status. |
| `subprocess` | No task queue, no retry logic, no concurrency control. Hard to manage at scale. |
| `multiprocessing` | Same problems as threading — no durability, no monitoring. |
| **Celery + Redis** | Tasks survive process restarts (they're in the Redis queue). Built-in retry, rate limiting, monitoring (Flower). Workers can scale independently from the API. |

The key insight is that chunk auditing and retrieval evaluation are **durable background jobs**, not fire-and-forget side effects. They must complete eventually, they should retry on failure, and they must not block user-facing requests. Celery is purpose-built for exactly this.

---

### 10.4 Why Separate Async and Sync Clients

The codebase maintains both async (`AsyncClient`, `AsyncQdrantClient`) and sync (`Client`, `QdrantClient`) versions of the Ollama and Qdrant clients:

- **FastAPI handlers are async** — the API endpoints use `async/await` for non-blocking I/O, which is standard for FastAPI.
- **Celery workers are sync** — Celery tasks run in a synchronous context. Using async clients inside Celery requires running an event loop manually, which adds complexity and potential deadlocks. Dedicated sync clients avoid this entirely.

---

### 10.5 Why Ollama Over OpenAI or Cloud-Only APIs

- **Privacy** — all data stays local. No documents leave the machine.
- **Cost** — no per-token API charges for development and testing.
- **Flexibility** — the `cloud` keyword in model names switches to a cloud endpoint automatically, so the same codebase supports both local and hosted models without code changes.

---

### 10.6 Why Redis for Both Task Queue and Chat History

Redis serves dual roles (Celery broker + chat history store) to minimize infrastructure:

- **Chat history is ephemeral** — messages expire after 24 hours and only the last 20 are kept. Redis's in-memory model is a good fit for short-lived, fast-access data.
- **Single dependency** — using Redis for both Celery and chat history means one fewer service to operate and monitor.

---

### 10.7 Why Per-Tenant Qdrant Collections

Each tenant gets its own Qdrant collection (`tenants_{tenant}_documents`) instead of sharing a single collection with metadata filters:

- **Hard isolation** — tenant data is physically separated. A query for tenant A can never accidentally return tenant B's documents, even if there's a bug in the filter logic.
- **Independent lifecycle** — a tenant's collection can be deleted, backed up, or resized without affecting others.

---

### 10.8 Why UUID5 for Point IDs

Point IDs in Qdrant are generated with `uuid.uuid5(namespace, "{tenant}:{doc_id}:{chunk_index}")`:

- **Deterministic** — the same document always produces the same point IDs, making upserts idempotent. Re-uploading a document updates existing chunks instead of creating duplicates.
- **No ID tracking needed** — the system can reconstruct any point ID from the tenant, document, and chunk index without storing a mapping table.

---

## 11. Trade-offs

| Decision | Benefit | Cost |
| --- | --- | --- |
| Character-based chunking | Simple, predictable, fast | May split related content across chunks; relies on audit step to fix context loss |
| Background audit (Celery) | Non-blocking uploads, retry-friendly | Chunks may be unaudited during the first few minutes after upload; queries in this window get raw chunks |
| Agentic chat loop (up to 15 iterations) | Better retrieval through iterative refinement | Higher latency per chat request; more LLM calls = more compute |
| Separate async/sync clients | Clean separation between FastAPI and Celery | Code duplication across async and sync versions of the same operations |
| Per-tenant collections | Strong data isolation | More collections to manage; cannot do cross-tenant search |
| Ollama (local LLM) | Free, private, no external dependency | Slower than cloud APIs; limited by local GPU; model quality depends on hardware |
| Redis for chat history | Fast, simple, no extra dependency | Data is volatile (no persistence configured); history lost on Redis restart |
| Iterative neighbor comparison for audit | Thorough context from all surrounding chunks | O(n) LLM calls per chunk where n is the chunk index; expensive for documents with many chunks |
| JSON-based tool-use protocol | Works with any model that can output JSON | Fragile with smaller models; requires robust JSON parsing with fallbacks |

---

## 12. Limitations

- **PDF only** — ingestion supports PDF files only. Other formats (Word, HTML, plain text) are not handled.
- **Character-based chunking** — may split tables, code blocks, or structured content poorly. Not optimized for documents with complex layouts.
- **No authentication** — the API has no auth layer. Any client can upload documents or query any tenant.
- **No rate limiting** — the API does not throttle requests, which could overwhelm Ollama or Qdrant under load.
- **No automated tests** — no unit or integration tests are configured yet.
- **Audit timing gap** — chunks are served unaudited immediately after upload until the background Celery worker finishes processing them.
- **Audit cost scales with document size** — the indexing agent compares each chunk against all previous chunks plus the next one. For a document with N chunks, this produces roughly N*(N-1)/2 LLM calls total.
- **Chat history is volatile** — stored in Redis without persistence. A Redis restart loses all conversation history.
- **Single embedding model** — the embedding model (`llama3.2:1b`, 2048 dimensions) is hardcoded in the collection vector size. Changing the model requires recreating all collections.
- **No streaming** — chat responses are returned in full after the agent loop completes. There is no streaming support for partial answers.

---

## 13. Future Improvements

- **Semantic chunking** — replace or complement character-based chunking with structure-aware splitting (headings, paragraphs, tables) using document layout analysis.
- **Streaming responses** — add SSE or WebSocket support so partial answers are streamed to the client as the agent works through its tool-use loop.
- **Authentication and authorization** — add API key or JWT-based auth to protect tenant data and control access.
- **Multi-format ingestion** — support Word (`.docx`), HTML, Markdown, and plain text documents alongside PDF.
- **Automated test suite** — add unit tests for chunking logic, integration tests for the audit pipeline, and end-to-end tests for the API.
- **Smarter audit scheduling** — prioritize auditing chunks that are more likely to be retrieved (e.g., based on query frequency) instead of auditing all chunks equally.
- **Chunk deduplication** — detect and merge near-duplicate chunks that arise from overlapping text or repeated sections in the source document.
- **Persistent chat history** — switch to Redis with AOF/RDB persistence or use a database (PostgreSQL, SQLite) for durable conversation storage.
- **Configurable vector dimensions** — allow the collection vector size to adapt to the chosen embedding model rather than hardcoding 2048.
- **Rate limiting and backpressure** — add request throttling to prevent overloading Ollama and Qdrant, especially during bulk uploads.
- **Observability** — add structured logging, metrics (Prometheus), and tracing (OpenTelemetry) for monitoring audit progress, retrieval quality, and system health.
- **Audit quality metrics** — track how often audited chunks produce better answers than unaudited ones, to validate the enrichment strategy with data.

---

## 14. Author

**Ikhsan Maulana** — ikhsanmsumarno@gmail.com
