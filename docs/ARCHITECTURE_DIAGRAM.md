# MeowVerse — Architecture Diagrams

Companion to [ARCHITECTURE.md](../ARCHITECTURE.md)'s full written
design (38 sections). These diagrams are meant to be legible in a
technical interview — each one maps directly to real code, referenced
inline.

## A. System Architecture

```mermaid
flowchart LR
    subgraph Client
        FE[Next.js Frontend<br/>App Router · TanStack Query]
    end

    subgraph Backend[FastAPI Backend]
        MW[Middleware<br/>CORS · Security Headers · Rate Limit]
        API[REST API<br/>app/api/v1/*]
        SVC[Services<br/>app/services/*]
        ML[ML Layer<br/>app/ml/*]
        AI[AI Providers<br/>app/ai/*]
        VEC[FAISS Vector Index<br/>app/similarity/*]
    end

    DB[(PostgreSQL)]
    STORE[(Image Storage<br/>Local / S3)]
    ANTHROPIC[Anthropic API]
    OPENAI[OpenAI API]

    FE -->|httpOnly cookie| MW --> API --> SVC
    SVC --> ML
    SVC --> AI
    SVC --> VEC
    SVC --> DB
    ML --> STORE
    AI -.optional.-> ANTHROPIC
    AI -.optional.-> OPENAI
```

Real request path: `app/main.py` wires `CORSMiddleware` →
`SecurityHeadersMiddleware` → the FastAPI routers in
`app/api/v1/`. Each router calls into `app/services/`, which
orchestrates `app/ml/` (breed/color/embedding/Grad-CAM),
`app/ai/` (LLM/image-gen providers), `app/similarity/`
(FAISS), and the SQLAlchemy repositories in `app/repositories/`.

## B. ML Pipeline

See [ML_PIPELINE.md](ML_PIPELINE.md) for the full, labeled
(TRAINED/DETERMINISTIC/LLM-GENERATED/DEMO FALLBACK) diagram.

## C. Authentication Flow

```mermaid
sequenceDiagram
    participant Browser
    participant API as FastAPI
    participant DB as PostgreSQL

    Browser->>API: POST /auth/register {email, password, display_name}
    API->>API: bcrypt.hash(password)
    API->>DB: INSERT users, INSERT sessions (token_hash)
    API-->>Browser: Set-Cookie (httpOnly, SameSite=Lax)<br/>raw token never stored server-side

    Note over Browser,API: Every subsequent request
    Browser->>API: GET /api/v1/... (cookie attached automatically)
    API->>DB: SELECT sessions WHERE token_hash = hash(cookie)
    DB-->>API: session row (if valid + not expired)
    API-->>Browser: 200 (or 401 if no/invalid/expired session)

    Browser->>API: POST /auth/logout
    API->>DB: DELETE FROM sessions WHERE token_hash = ...
    API-->>Browser: session immediately unusable, even before cookie expiry
```

Sessions are **opaque, DB-backed tokens**, not JWT — only the *hash*
of the token is stored (`app/core/security.py`), mirroring password
hashing's own "a DB leak shouldn't hand over usable sessions"
principle. See
[docs/INTERVIEW_PREPARATION.md](INTERVIEW_PREPARATION.md) for the
JWT-vs-session-token trade-off discussion.

## D. Similarity Search Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Embed as Embedding Model
    participant FAISS
    participant DB as PostgreSQL

    Client->>API: GET /analyses/{id}/similar
    API->>DB: resolve + authorize source cat (public OR owned)
    API->>DB: look up stored embedding row for source cat
    API->>FAISS: reconstruct query vector by vector_id
    API->>FAISS: search(query_vector, k × oversample)
    FAISS-->>API: candidate (vector_id, score) pairs
    API->>DB: resolve candidate vector_ids back to analysis rows
    API->>API: privacy filter (public OR caller-owned) + self-exclusion
    API->>API: optional breed/rarity/favorite filters (post-retrieval)
    API-->>Client: top-k results, each with real cosine similarity
```

Privacy filtering happens **after** retrieval but **before** the
response is built — a private candidate is discarded in-process, never
sent to the client and hidden client-side. Guests and other users can
never see a private cat's existence via this endpoint, even indirectly
through a similarity score.

## E. Explainability Flow (Grad-CAM)

```mermaid
flowchart TD
    A[Client clicks<br/>'Why this breed?'] --> B[POST /analyses/id/explanation]
    B --> C{Cached for this<br/>target_class + model_version?}
    C -->|yes| H[Return cached heatmap URL]
    C -->|no| D[Load original photo via<br/>ImageStorageProvider]
    D --> E[Forward pass through<br/>real breed classifier]
    E --> F[Backward pass:<br/>gradients of predicted class score<br/>w.r.t. features-1 layer]
    F --> G[Weight feature maps by<br/>gradient importance → ReLU → normalize]
    G --> I[Resize to original image size,<br/>colorize, alpha-blend overlay]
    I --> J[Store heatmap + overlay,<br/>cache on analysis_id + target_class + model_version]
    J --> H
```

Caching key is `(analysis_id, target_class, breed_model_version)` —
if the classifier is ever retrained, a stale explanation can never be
served against the new model version.

## F. Generative AI Fallback Flow

```mermaid
flowchart TD
    A[Request needs generative content<br/>story / personality narrative / portrait] --> B{Provider API key<br/>configured?}
    B -->|no| F[NullProvider:<br/>is_available = False]
    B -->|yes| C[Real provider call<br/>forced tool-use / image-edit]
    C --> D{Call succeeds &<br/>schema valid?}
    D -->|yes| E[Real generated content<br/>mode: 'generated']
    D -->|no, after 1 retry| F
    F --> G[Deterministic offline fallback<br/>mode: 'demo', clearly labeled]

    style E fill:#f5a3c4,color:#1a1a2e
    style G fill:#d3d3d3,color:#1a1a2e
```

Every path terminates in either real, clearly-labeled AI-generated
content or a clearly-labeled deterministic fallback — never a crash,
never an ambiguous or silently-faked result.
