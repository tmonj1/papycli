# Copilot instructions for pull request review (Python CLI)

## Language / tone
- Write the review in **Japanese**.
- Be concise. Use bullets. Avoid long explanations unless it’s important for correctness.
- Do **not** include "Nit:" or nitpicks. Do not comment on trivial style-only issues.

## Review priorities (most important first)
1. **Correctness / behavior (strict)** for production source code:
   - Logic correctness, edge cases, error handling, exit codes
   - CLI UX: argument parsing, help text accuracy, defaults, backward compatibility
   - Security concerns: shell injection, path traversal, unsafe file operations, secrets handling
   - Reliability: retries/timeouts, network failures, idempotency, atomic writes
2. **Maintainability (moderate)**:
   - Clear structure, separation of concerns, naming (only when it impacts understanding)
   - Reasonable complexity and duplication (only when meaningful)
3. **Style / comments / docstrings (light)**:
   - Only mention if it causes misunderstanding or maintenance risk
   - Otherwise skip

## File-type sensitivity
- For **application/source code** (e.g., `src/`, package modules): apply the strictness above.
- For **tests**: be **light**; focus only on missing/incorrect assertions, flaky patterns, and obvious gaps.
- For **CI/config** (GitHub Actions, linters, packaging config): be **light**; flag only clear breakage, security issues, or major inefficiencies.
- For **docs**: be **light**; correct only factual/usage mistakes.

## Output format
- Start with a short summary:
  - `概要:` 1–3 bullets
- Then list issues, only if present:
  - `指摘:` bullets grouped by severity:
    - `重大` (must fix)
    - `重要` (should fix)
    - `参考` (optional)
- When suggesting code changes:
  - Provide a minimal, concrete patch suggestion (small snippet) only for `重大` or `重要`.
  - Prefer small, targeted changes over refactors.

## What to ignore
- Formatting-only preferences (quote style, blank lines, import sorting) unless it breaks tooling.
- Minor wording preferences in comments/docstrings.
- Micro-optimizations unless they affect correctness or CLI responsiveness.
