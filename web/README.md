# Signal Web

Portfolio dashboard for the Signal backend project. The UI reads data from your FastAPI API and highlights:

- feed quality and reliability
- curated article highlights
- recent scheduler job runs

## Local Setup

1. Install dependencies:

```bash
bun install
```

2. Create `web/.env.local`:

```bash
SIGNAL_API_BASE_URL=http://127.0.0.1:8000/api
SIGNAL_API_KEY=your_api_key_here
```

3. Run:

```bash
bun run dev
```

Then open [http://localhost:3000](http://localhost:3000).
