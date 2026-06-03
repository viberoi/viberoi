# CLAUDE.md — frontend

Vite + React + TS + Tremor + TanStack Query + React Router + Tailwind.

## Layout

```
frontend/
  index.html
  vite.config.ts            # dev server + /api proxy → :8003
  tailwind.config.ts
  src/
    main.tsx                # app entry — providers
    App.tsx                 # routes
    index.css
    api/
      client.ts             # typed fetch wrapper + endpoint surface
    auth/
      AuthContext.tsx       # dev-mode user state in localStorage
    components/
      Shell.tsx             # sidebar + outlet
    pages/
      Login.tsx
      Dashboard.tsx
      Sessions.tsx
    test/
      setup.ts
      client.test.ts
  _design/                  # legacy design mockups (recharts, inline styles)
```

## Dev auth (until Slice 6 provisions Cognito)

The Login page picks one of three hardcoded dev users (mirroring the seed
script's UUIDs). The user is persisted to `localStorage`. The API client
attaches `X-Dev-Org-Id` / `X-Dev-Developer-Id` / `X-Dev-Role` /
`X-Dev-Team-Id` headers on every request. The API service accepts these
ONLY when `env=dev` — `verify_jwt` is never bypassed in prod.

When Cognito lands, only two files change:
- `auth/AuthContext.tsx` — populates `user` from the Cognito access token
- `api/client.ts` — replaces the X-Dev-\* headers with `Authorization: Bearer`

Every other component reads `useAuth().user` and is unaware of the auth
mechanism.

## Commands

```powershell
npm install              # one-time
npm run dev              # vite dev server on :5173
npm run build            # production build → dist/
npm run typecheck        # tsc --noEmit
npm test                 # vitest run
```

## Rules

- Never inline-style components — use Tailwind classes. Inline styles
  in `_design/` are reference only; the live codebase uses utility classes.
- Never construct API URLs by hand — use `api.<endpoint>` from
  `api/client.ts`. New endpoints go there with their request + response
  types.
- Never store anything sensitive in localStorage. The dev-user object
  is non-secret (mirrors what a JWT would carry); when Cognito lands,
  the access token lives in memory or sessionStorage, not localStorage.
- Tests with Vitest, NOT Jest. `npm test` runs once; `npm run test:watch`
  for TDD.
