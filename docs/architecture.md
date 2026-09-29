# Architecture

The browser is a Next.js dashboard. It calls FastAPI REST endpoints. The FastAPI orchestration layer separates domain objects, decision analysis, and the Hindsight gateway.

`HindsightGateway` is the only production memory gateway. It wraps the official `hindsight-client` async calls: `aretain` persists decision/outcome/lesson source material into a configured bank, and `arecall` retrieves ranked facts for a new decision. In-memory repository state is limited to short-lived application metadata and is never used as long-term memory.
