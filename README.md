# Echo Chamber

Most AI assistants remember what you said. Echo Chamber remembers what happened.

Echo Chamber is a decision agent for founders and product teams. It records a decision and its assumptions, stores the real-world outcome in Hindsight, extracts lessons, and brings those lessons into future recommendations.

## Core loop

`Decision -> Prediction -> Outcome -> Lesson -> Hindsight memory -> Better future decision`

## Architecture

```text
Next.js dashboard -> FastAPI -> Decision Agent -> Hindsight Cloud
                              -> Configurable OpenAI-compatible LLM
```

Hindsight is the production long-term-memory authority. The API retains decisions, outcomes, and lessons through the official async Python `hindsight-client`; it recalls only ranked, relevant context for a new decision. The returned response tells the interface precisely which memories changed the recommendation.

## Setup

1. Copy `.env.example` to `.env` and set `HINDSIGHT_API_KEY`, `HINDSIGHT_BANK_ID`, and optionally the LLM settings.
2. In `backend`, create a Python 3.11+ environment and install `py -3 -m pip install -r requirements.txt`.
3. From the project root, run `npm install` then `npm run dev`.
4. In a second terminal at the project root, run `npm run dev:api` (this serves the API on port `8010`).
5. Open `http://localhost:3000`.

## Demo

Click **Load demo scenario**. It writes the resume-builder decision, outcome, and lessons through the same Hindsight adapter as production. Then create a cover-letter-generator decision and stress test it; its analysis displays the Hindsight memories that changed the recommendation.

Without configured Hindsight credentials, operations that require durable memory show `Memory service unavailable.` The application never substitutes a local fake memory store.

## Tests

Run `pytest` in `backend`. Unit tests can inject a memory gateway double; live Hindsight integration tests should be run only with a configured cloud bank.

## Deploy (free tier)

The stack deploys free: **backend → Render**, **frontend → Vercel**. Hindsight Cloud and Groq are already hosted services; you only paste your keys.

1. Push this repo to GitHub.
2. **Backend (Render):** render.com → New → Blueprint → point at the repo. It reads `render.yaml`. Add `HINDSIGHT_API_KEY` and `LLM_API_KEY` when prompted. After deploy, copy the `https://...onrender.com` URL.
3. **Frontend (Vercel):** vercel.com → Add New Project → import the repo. Set Root Directory to `frontend`, then add env var `NEXT_PUBLIC_API_URL=https://<your-render-url>`.
4. **Unblock CORS:** in Render, add env var `CORS_ORIGINS=https://<your-vercel-url>` and redeploy.

Note: Render's free tier sleeps after ~15 min idle; first request after that takes ~30s to wake. Vercel's free tier does not sleep.
