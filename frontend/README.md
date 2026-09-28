# GARUDA dashboard

React + Vite + TypeScript + Recharts + Tailwind. Five views over the GARUDA API:
National Index, Route Explorer, Yield Curve, Anomaly Alerts, CPI Export.

```bash
pnpm install
pnpm dev        # http://localhost:5174, expects the API at http://127.0.0.1:8010
pnpm build      # type-check + production build
pnpm lint
```

Point it at another API with `VITE_API_URL=http://host:port pnpm dev`.
From the project root, `pnpm start` runs the API and this dashboard together.
