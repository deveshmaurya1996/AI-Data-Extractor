# Frontend (Next.js latest structure)

This frontend keeps the latest Next.js App Router structure under `app/`.

## Run

```bash
npm install
npm run dev
```

## Tests

```bash
npm test
```

Uses `jest.config.cjs` and `next/jest`. Test files: `src/**/*.test.ts(x)` (excluded from `tsc --noEmit` via `tsconfig.json`).
