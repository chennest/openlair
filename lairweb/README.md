# OpenLair Web

Vue 3 + TypeScript web admin console for OpenLair.

## Commands

```sh
npm install
npm run dev
npm run build
npm run preview
```

During development, Vite proxies `/assistant`, `/health`, and `/notes` to `LAIRWEB_API_PROXY_TARGET`.

To point the web UI at another backend, copy `.env.example` to `.env.local` and set:

```sh
LAIRWEB_API_PROXY_TARGET=http://127.0.0.1:8000
VITE_API_BASE_URL=
```

Keep `VITE_API_BASE_URL` empty for local development so the browser calls same-origin paths through the Vite proxy. Set it only when the browser should call an absolute API URL directly.
