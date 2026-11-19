import { serve } from "bun";
import index from "./index.html";

const controller = process.env.CONTROLLER_URL ?? "http://127.0.0.1:8000";
const allowed = new Set(["/status", "/incidents", "/telemetry/history", "/experiments", "/mode"]);

serve({
  hostname: "127.0.0.1",
  port: Number(process.env.PORT ?? 5173),
  routes: {
    "/control/*": async request => {
      const path = new URL(request.url).pathname.slice("/control".length);
      if (!allowed.has(path) && !/^\/incidents\/\d+$/.test(path)) {
        return Response.json({ detail: "Unknown control endpoint" }, { status: 404 });
      }
      try {
        const upstream = await fetch(new URL(path, controller), {
          method: request.method,
          headers: { "Content-Type": "application/json" },
          body: request.method === "GET" ? undefined : await request.text(),
          signal: AbortSignal.timeout(15000),
        });
        return new Response(upstream.body, {
          status: upstream.status,
          headers: { "Content-Type": upstream.headers.get("Content-Type") ?? "application/json" },
        });
      } catch {
        return Response.json({ detail: "HealLab API is unavailable. Start the API service and try again." }, { status: 502 });
      }
    },
    "/*": index,
  },
  development: process.env.NODE_ENV !== "production" && { hmr: true, console: true },
});
