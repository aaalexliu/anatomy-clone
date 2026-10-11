import { useEffect, useMemo, useState } from "react"
import { ROLE_HEX } from "./scene"
import { StageView } from "./StageView"

const ROLE_ORDER = ["prime_mover", "synergist", "stabilizer", "antagonist"]
const SCORE_LABEL = {
  legality: "legality",
  joint_path: "joint path",
  muscle_role: "muscle role",
  negative_control: "negative control",
  force_couple: "force couple",
}

export function Detail({ index, itemId, leftId }) {
  const item = index.items.find((row) => row.id === itemId)
  const prototypes = index.prototypes
  const left = prototypes.some((row) => row.id === leftId) ? leftId : prototypes[0]?.id
  const rightDefault = prototypes.find((row) => row.id !== left)?.id || left
  const [right, setRight] = useState(rightDefault)
  const [frame, setFrame] = useState(0)
  const [playing, setPlaying] = useState(true)

  useEffect(() => {
    setRight(prototypes.find((row) => row.id !== left)?.id || left)
    setFrame(0)
  }, [itemId, left, prototypes])

  const leftCell = cellFor(index, left, itemId)
  const rightCell = cellFor(index, right, itemId)
  const leftRun = useRun(leftCell)
  const rightRun = useRun(rightCell)
  const frames = leftRun.playback?.frames?.length || rightRun.playback?.frames?.length || 1

  useEffect(() => {
    if (!playing) return undefined
    const fps = leftRun.playback?.fps || rightRun.playback?.fps || 30
    const timer = setInterval(() => setFrame((current) => (current + 1) % frames), 1000 / fps)
    return () => clearInterval(timer)
  }, [playing, frames, leftRun.playback, rightRun.playback])

  const time = leftRun.playback?.frames?.[Math.min(frame, frames - 1)]?.t
  const shownTime = Number.isFinite(time) ? time.toFixed(2) : "0.00"

  return (
    <>
      <div className="detail-head">
        <div>
          <p className="kicker"><a href="#/">Exam card</a></p>
          <h1>{item?.name || itemId}</h1>
          {item?.note ? <p className="muted">{item.note}</p> : null}
        </div>
        <label className="muted">
          Compare{" "}
          <select className="swap" value={right} onChange={(event) => setRight(event.target.value)}>
            {prototypes.map((row) => (
              <option key={row.id} value={row.id}>{row.name}</option>
            ))}
          </select>
        </label>
      </div>
      <div className="compare">
        <Panel prototype={prototypes.find((row) => row.id === left)} cell={leftCell} run={leftRun} frame={frame} />
        <Panel prototype={prototypes.find((row) => row.id === right)} cell={rightCell} run={rightRun} frame={frame} />
      </div>
      <div className="transport">
        <button type="button" onClick={() => setPlaying((value) => !value)}>{playing ? "Pause" : "Play"}</button>
        <input
          type="range"
          min="0"
          max={Math.max(frames - 1, 0)}
          value={Math.min(frame, frames - 1)}
          onChange={(event) => {
            setPlaying(false)
            setFrame(Number(event.target.value))
          }}
          aria-label="Shared timeline"
        />
        <span className="muted">{shownTime}s</span>
      </div>
      <div className="legend">
        {ROLE_ORDER.map((role) => (
          <span key={role}><i className="swatch" style={{ background: ROLE_HEX[role] }} />{pretty(role)}</span>
        ))}
      </div>
    </>
  )
}

function Panel({ prototype, cell, run, frame }) {
  const sample = run.playback?.frames?.[Math.min(frame, (run.playback?.frames?.length || 1) - 1)]
  const listed = useMemo(() => listRoles(sample), [sample])
  return (
    <section className="panel">
      <h2>{prototype?.name || "Prototype"}</h2>
      {cell ? (
        <div>
          <span className={`tag ${cell.status}`}>{cell.status}</span>
          {Object.entries(cell.scores)
            .filter(([, score]) => score.status !== "not_applicable")
            .map(([key, score]) => (
              <span className={`tag ${score.status}`} key={key}>{SCORE_LABEL[key]} {score.status}</span>
            ))}
          <p className="meta">{cell.reason}</p>
        </div>
      ) : <p className="meta">No score for this cell.</p>}
      <StageView playback={run.playback} frame={frame} />
      {run.emission ? (
        <p className="meta">
          {run.emission.provenance.estimator} · {run.emission.provenance.motion_source}
          {" · "}confidence {run.emission.confidence}
          {" · "}{run.emission.load.description}
        </p>
      ) : null}
      <ul className="roles">
        {listed.map((row) => (
          <li key={row.name}><i className="swatch" style={{ background: ROLE_HEX[row.role] }} />{pretty(row.role)} · {pretty(row.name)}</li>
        ))}
      </ul>
    </section>
  )
}

function listRoles(sample) {
  if (!sample) return []
  const rows = Object.entries(sample.muscles || {})
    .filter(([, muscle]) => muscle.role !== "inactive")
    .map(([name, muscle]) => ({ name, role: muscle.role }))
  rows.sort((a, b) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role) || a.name.localeCompare(b.name))
  return rows
}

function cellFor(index, prototypeId, itemId) {
  return index.cells.find((cell) => cell.prototype_id === prototypeId && cell.item_id === itemId)
}

function useRun(cell) {
  const [playback, setPlayback] = useState(null)
  const [emission, setEmission] = useState(null)
  useEffect(() => {
    if (!cell) {
      setPlayback(null)
      setEmission(null)
      return undefined
    }
    let cancelled = false
    Promise.all([
      fetch(`/runs/${cell.playback_path}`).then((response) => response.json()),
      fetch(`/runs/${cell.emission_path}`).then((response) => response.json()),
    ]).then(([play, emit]) => {
      if (!cancelled) {
        setPlayback(play)
        setEmission(emit)
      }
    })
    return () => {
      cancelled = true
    }
  }, [cell])
  return { playback, emission }
}

function pretty(value) {
  const text = String(value).replaceAll("_", " ")
  return text.charAt(0).toUpperCase() + text.slice(1)
}
