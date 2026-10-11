import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"
import react from "@vitejs/plugin-react"

const root = path.dirname(fileURLToPath(import.meta.url))
const runsRoot = path.resolve(root, "../runs")

function serveRuns() {
  const handler = (req, res, next) => {
    const raw = decodeURIComponent((req.url || "/").split("?")[0])
    const rel = raw.replace(/^\/+/, "")
    const file = path.resolve(runsRoot, rel)
    if (!file.startsWith(runsRoot) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
      next()
      return
    }
    res.setHeader("Content-Type", "application/json")
    fs.createReadStream(file).pipe(res)
  }
  return {
    name: "serve-runs",
    configureServer(server) {
      server.middlewares.use("/runs", handler)
    },
    configurePreviewServer(server) {
      server.middlewares.use("/runs", handler)
    },
  }
}

export default {
  plugins: [react(), serveRuns()],
  server: { fs: { allow: [path.resolve(root, "..")] } },
}
