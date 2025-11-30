# Artificer – Cursor AI Collaboration Rules

## High-Level Goals

- I am actively trying to **understand my existing codebase better**, not just ship features.
- I am comfortable with **“back-of-the-napkin” / works-on-my-machine prototypes**, but I want help turning them into **scalable, robust implementations**.
- I want the system to **scale well** (architecture, data flow, storage, concurrency, distribution, and multi-user scenarios).
- I care about writing **production-quality code**: readable, tested, observable, and maintainable.

## How the AI Should Work With Me

- **Explain first, then change**  
  - When touching unfamiliar parts of the code, first give a short explanation of:  
    - What the module does  
    - How it fits into the larger `algo_trader` architecture  
    - Any important invariants or contracts  
  - For non-trivial changes, include a brief rationale for the design and call out tradeoffs.

- **Optimize for my understanding, not just speed**  
  - Prefer clear, boring, well-structured code over “clever” solutions.  
  - When introducing patterns (e.g. data piping, concurrency, storage/queueing technologies, external services), explain them in plain language and tie them back to the concrete files you modify.

- **Keep architecture and scalability in mind**  
  - Favor separation of concerns:  
    - Pure, testable core logic (functions/classes that work on Python data structures).  
    - Thin adapters for I/O and tools (databases, caches, queues, external APIs, CLIs, etc.).  
  - Call out when a change affects performance characteristics, data volume, or fan-out/fan-in patterns.

- **Use tools and infrastructure intentionally**  
  - Treat databases, caches, queues, and external services as **infrastructure primitives**, not dumping grounds.  
  - Prefer:  
    - Clear, documented schemas and key/identifier patterns.  
    - Explicit serialization/deserialization boundaries.  
    - Small, domain-focused helper modules/classes on top of low-level clients, instead of spreading raw calls everywhere.  
  - When changing or adding new flows through these tools, briefly document: the data shape, how it’s stored/addressed, lifecycle/TTL behavior (if any), and expected producers/consumers.

- **Testing and production readiness**  
  - For any non-trivial logic or data piping, propose or update tests:  
    - Happy path  
    - Important edge cases and failure modes  
    - Round-trips through storage/DB/queues when relevant  
  - Call out missing tests that would materially increase safety, even if not implemented yet.  
  - Keep an eye on observability: suggest logging/metrics where they help with debugging and live operations.

- **First I draft, then AI critiques and drives tests**  
  - Assume I will often write an initial, possibly “quick and dirty” implementation that may not scale or follow all best practices.  
  - Your job is to:  
    - Evaluate my implementation for **scalability, correctness, and industry-standard patterns** (especially around distribution, concurrency, multi-user behavior, and failure handling).  
    - Suggest concrete improvements and refactors, but avoid fully rewriting everything unless I explicitly ask; start from what I wrote.  
    - Propose or create **unit, integration, and/or end-to-end tests** that capture the desired behavior and scalability/robustness properties.  
  - Tests should follow the existing **`testing` rules** in this repo:  
    - Shared fixtures, mocks, and common test data live in `conftest.py` (not in the test files).  
    - Use the Bazel pattern: `tests/.../BUILD` defines `py_library(test_*_lib, srcs=[conftest, test_*.py])`, and the implementation `BUILD` defines a `pytest_test` target pointing at that library.  
    - Mark tests with `pytest.mark` to distinguish `unit` / `integration` / `e2e`, and add matching Bazel `tags` on the `pytest_test` target.  
  - After tests exist, **do not silently “fix” my implementation**; instead, tell me what’s failing and why, so I can iterate until the tests pass (TDD-style), unless I explicitly ask you to apply the implementation changes.

- **Use explanations as a teaching tool**  
  - When you generate or refactor code, briefly:  
    - Explain the main functions/classes  
    - Point out any tricky parts (race conditions, error handling, state transitions)  
    - Highlight assumptions about other parts of the system

## Style and Interaction Preferences

- Prefer **concise, high-signal explanations** over long essays, unless I explicitly ask for deep dives.
- When multiple approaches exist, list 2–3 options with pros/cons and a clear recommendation.
- When refactoring or designing something new, start with a **short design sketch** (inputs/outputs, data flow, responsibilities) before large code changes.


