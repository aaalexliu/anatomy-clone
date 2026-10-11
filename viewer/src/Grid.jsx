import { useState } from "react"

const SCORE_LABEL = {
  legality: "legality",
  joint_path: "joint path",
  muscle_role: "muscle role",
  negative_control: "negative control",
  force_couple: "force couple",
}

export function Grid({ index }) {
  const [tip, setTip] = useState(null)
  const cells = new Map(index.cells.map((cell) => [`${cell.prototype_id}/${cell.item_id}`, cell]))

  return (
    <>
      <p className="kicker">anatomy-clone</p>
      <h1>Exam card</h1>
      <p className="lede">
        Each cell is the harness score for that prototype on that item. Hover for the reason. Click to play the motion and compare the other prototype. This page only reads the scores.
      </p>
      <div className="board">
        <table className="grid">
          <thead>
            <tr>
              <th className="corner">Prototype</th>
              {index.items.map((item) => (
                <th key={item.id}>
                  {item.name}
                  {item.negative_control ? <span className="note">{item.note}</span> : null}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {index.prototypes.map((prototype) => (
              <tr key={prototype.id}>
                <th className="proto-name">{prototype.name}</th>
                {index.items.map((item) => {
                  const cell = cells.get(`${prototype.id}/${item.id}`)
                  if (!cell) return <td key={item.id}><div className="empty">no run</div></td>
                  return (
                    <td key={item.id}>
                      <button
                        className="cell"
                        onClick={() => {
                          window.location.hash = `#/item/${encodeURIComponent(item.id)}/${encodeURIComponent(prototype.id)}`
                        }}
                        onMouseEnter={(event) => setTip(place(event, cell, prototype, item))}
                        onMouseMove={(event) => setTip(place(event, cell, prototype, item))}
                        onMouseLeave={() => setTip(null)}
                      >
                        <span className={`tag ${cell.status}`}>{cell.status}</span>
                        <div className="pills">
                          {Object.entries(cell.scores)
                            .filter(([, score]) => score.status !== "not_applicable")
                            .map(([key, score]) => (
                              <span className="pill" key={key}>{SCORE_LABEL[key]} {score.status}</span>
                            ))}
                        </div>
                      </button>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {tip ? (
        <div className="tip" style={{ left: tip.x, top: tip.y }}>
          <strong>{tip.title}</strong>
          {tip.lines.map((line) => <p key={line}>{line}</p>)}
        </div>
      ) : null}
    </>
  )
}

function place(event, cell, prototype, item) {
  const pad = 14
  const width = 360
  let x = event.clientX + pad
  let y = event.clientY + pad
  if (x + width > window.innerWidth - 8) x = event.clientX - width - pad
  if (y + 180 > window.innerHeight - 8) y = Math.max(48, event.clientY - 160)
  const lines = [cell.reason]
  for (const [key, score] of Object.entries(cell.scores)) {
    if (score.status === "not_applicable") continue
    lines.push(`${SCORE_LABEL[key]}: ${score.status}. ${score.reason}`)
  }
  if (cell.muscle_role?.predicted_top5) {
    lines.push(`Predicted top: ${cell.muscle_role.predicted_top5.join(", ") || "none"}.`)
  }
  return { x, y, title: `${prototype.name} · ${item.name}`, lines }
}
