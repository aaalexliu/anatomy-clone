import { useEffect, useMemo, useState } from "react"
import { ROLE_HEX } from "./scene"
import { StageView } from "./StageView"

const ROLE_ORDER = ["prime_mover", "synergist", "stabilizer", "antagonist"]

export function Reference() {
  const [playback, setPlayback] = useState(null)
  const [body, setBody] = useState(null)
  const [error, setError] = useState("")
  const [frame, setFrame] = useState(0)
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      fetch("/reference/playback.json").then((response) => {
        if (!response.ok) throw new Error(`playback.json returned ${response.status}`)
        return response.json()
      }),
      fetch("/reference/body.json").then((response) => {
        if (!response.ok) throw new Error(`body.json returned ${response.status}`)
        return response.json()
      }),
    ])
      .then(([motion, meshes]) => {
        if (!cancelled) {
          setPlayback(motion)
          setBody(meshes)
        }
      })
      .catch((exc) => {
        if (!cancelled) setError(String(exc.message || exc))
      })
    return () => {
      cancelled = true
    }
  }, [])

  const frames = playback?.frames?.length || 1
  useEffect(() => {
    if (!playing || !playback?.motion_recovered) return undefined
    const fps = playback.fps || 6
    const timer = setInterval(() => setFrame((current) => (current + 1) % frames), 1000 / fps)
    return () => clearInterval(timer)
  }, [playing, frames, playback])

  const sample = playback?.frames?.[Math.min(frame, frames - 1)]
  const listed = useMemo(() => listRoles(sample), [sample])
  const shownTime = Number.isFinite(sample?.t) ? sample.t.toFixed(2) : "0.00"

  return (
    <>
      <div className="detail-head">
        <div>
          <p className="kicker"><a href="#/">Exam card</a></p>
          <h1>{playback?.title || "Reference clip"}</h1>
          <p className="muted">
            Full-body bone meshes and shoulder muscle volumes. This view is not on the exam card, and nothing here writes a score.
          </p>
        </div>
      </div>
      {error ? <p>{error}</p> : null}
      {!playback && !error ? <p className="muted">Loading the reference body…</p> : null}
      {playback ? (
        <section className="panel">
          <StageView playback={playback} frame={frame} body={body} fullBody tall />
          <p className="meta">{playback.method}</p>
          {playback.blocker ? <p className="meta">{playback.blocker}</p> : null}
          {playback.note ? <p className="meta">{playback.note}</p> : null}
          <ul className="roles">
            {listed.map((row) => (
              <li key={row.name}>
                <i className="swatch" style={{ background: ROLE_HEX[row.role] }} />
                {pretty(row.role)} · {row.label}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {playback ? (
        <div className="transport">
          <button type="button" onClick={() => setPlaying((value) => !value)} disabled={!playback.motion_recovered}>
            {playing && playback.motion_recovered ? "Pause" : "Play"}
          </button>
          <input
            type="range"
            min="0"
            max={Math.max(frames - 1, 0)}
            value={Math.min(frame, frames - 1)}
            onChange={(event) => {
              setPlaying(false)
              setFrame(Number(event.target.value))
            }}
            aria-label="Reference timeline"
          />
          <span className="muted">{shownTime}s</span>
        </div>
      ) : null}
      <div className="legend">
        {ROLE_ORDER.map((role) => (
          <span key={role}><i className="swatch" style={{ background: ROLE_HEX[role] }} />{pretty(role)}</span>
        ))}
      </div>
    </>
  )
}

function listRoles(sample) {
  if (!sample?.muscles) return []
  return Object.entries(sample.muscles)
    .map(([name, muscle]) => ({ name, role: muscle.role, label: muscle.label || name }))
    .filter((row) => ROLE_ORDER.includes(row.role))
    .sort((a, b) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role) || a.label.localeCompare(b.label))
}

function pretty(value) {
  return String(value || "").replaceAll("_", " ")
}
