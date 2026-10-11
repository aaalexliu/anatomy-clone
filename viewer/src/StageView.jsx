import { useEffect, useRef } from "react"
import { mountScene } from "./scene"

export function StageView({ playback, frame }) {
  const mountRef = useRef(null)
  const apiRef = useRef(null)

  useEffect(() => {
    const api = mountScene(mountRef.current)
    apiRef.current = api
    return () => api.dispose()
  }, [])

  useEffect(() => {
    apiRef.current?.setFrame(playback, frame)
  }, [playback, frame])

  return <div className="stage" ref={mountRef} />
}
