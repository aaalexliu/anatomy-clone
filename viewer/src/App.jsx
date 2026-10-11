import { useEffect, useMemo, useState } from "react"
import { Detail } from "./Detail"
import { Grid } from "./Grid"

export function App() {
  const [index, setIndex] = useState(null)
  const [error, setError] = useState("")
  const [hash, setHash] = useState(window.location.hash || "#/")

  useEffect(() => {
    const onHash = () => setHash(window.location.hash || "#/")
    window.addEventListener("hashchange", onHash)
    return () => window.removeEventListener("hashchange", onHash)
  }, [])

  useEffect(() => {
    let cancelled = false
    fetch("/runs/index.json")
      .then((response) => {
        if (!response.ok) throw new Error(`index.json returned ${response.status}`)
        return response.json()
      })
      .then((payload) => {
        if (!cancelled) setIndex(payload)
      })
      .catch((exc) => {
        if (!cancelled) setError(String(exc.message || exc))
      })
    return () => {
      cancelled = true
    }
  }, [])

  const route = useMemo(() => parseHash(hash), [hash])

  return (
    <>
      <div className="banner">model estimate, not EMG</div>
      <main className="app">
        {error ? <p>{error}</p> : null}
        {!index && !error ? <p className="muted">Loading scores…</p> : null}
        {index && route.item ? <Detail index={index} itemId={route.item} leftId={route.left} /> : null}
        {index && !route.item ? <Grid index={index} /> : null}
      </main>
    </>
  )
}

function parseHash(hash) {
  const [path] = hash.replace(/^#/, "").split("?")
  const parts = path.split("/").filter(Boolean)
  if (parts[0] === "item" && parts[1]) {
    return { item: decodeURIComponent(parts[1]), left: parts[2] ? decodeURIComponent(parts[2]) : "" }
  }
  return { item: "", left: "" }
}
