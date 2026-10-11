import { useEffect, useRef } from "react"
import { mountScene } from "./scene"

export function StageView({ playback, frame, body, fullBody = false, tall = false }) {
  const mountRef = useRef(null)
  const apiRef = useRef(null)

  useEffect(() => {
    const api = mountScene(mountRef.current, { fullBody })
    apiRef.current = api
    return () => api.dispose()
  }, [fullBody])

  useEffect(() => {
    apiRef.current?.setBody(body || null)
  }, [body])

  useEffect(() => {
    apiRef.current?.setFrame(playback, frame)
  }, [playback, frame, body])

  return <div className={tall ? "stage stage-tall" : "stage"} ref={mountRef} />
}
