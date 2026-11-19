# HealLab control room

React and Bun frontend for live workload telemetry, incident investigation, and controlled recovery experiments.

Start the HealLab backend from the repository root, then run `bun install` and `bun dev` here. Open http://localhost:5173. The Bun server proxies `/control/*` to `CONTROLLER_URL` (default `http://127.0.0.1:8000`). It binds to localhost; `PORT` defaults to 5173 to avoid the Grafana port.

`bun run build` builds the browser bundle. `bun start` serves the app and proxy with production mode enabled. Deploying `dist/` alone requires a separate equivalent API proxy.

See [the operations guide](../Docs/OPERATIONS.md#react-workspace) for controls, setup, and verification limits. UI test responses are not shipped with the application.

The UI uses the existing shadcn Button and Select primitives, with React Bits `AnimatedContent-TS-TW` retrieved from `https://reactbits.dev/r/AnimatedContent-TS-TW.json` in `src/components/react-bits/AnimatedContent.tsx`. Its GSAP animation honors reduced motion; GSAP also animates live metric changes. See the upstream [React Bits repository and license](https://github.com/DavidHDev/react-bits) for component attribution. The workspace uses a dynamic viewport height and its own keyboard-accessible scroll region; scrollbar rails are hidden without disabling scrolling.
