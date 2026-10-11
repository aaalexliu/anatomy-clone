import * as THREE from "three"
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js"

const ROLE_COLOR = {
  prime_mover: 0xc23b3b,
  synergist: 0xd4762c,
  stabilizer: 0x2f6f9f,
  antagonist: 0x7a6a8a,
  inactive: 0xd5cfc6,
}

export function mountScene(element) {
  const renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setClearColor(0xefeae3)
  element.appendChild(renderer.domElement)
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(35, 1, 0.05, 20)
  camera.position.set(1.15, 1.15, 2.55)
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(0.0, 0.95, 0.1)
  controls.update()
  scene.add(new THREE.HemisphereLight(0xfff8ef, 0xc8bfb4, 1.1))
  const sun = new THREE.DirectionalLight(0xffffff, 1.3)
  sun.position.set(1.5, 3, 2)
  scene.add(sun)
  const group = new THREE.Group()
  scene.add(group)

  const resize = () => {
    const width = element.clientWidth || 1
    const height = element.clientHeight || 1
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)
  }
  resize()
  const observer = new ResizeObserver(resize)
  observer.observe(element)
  let frame = requestAnimationFrame(function tick() {
    controls.update()
    renderer.render(scene, camera)
    frame = requestAnimationFrame(tick)
  })

  return {
    setFrame(playback, index) {
      clear(group)
      if (!playback || !playback.frames.length) return
      const sample = playback.frames[Math.max(0, Math.min(index, playback.frames.length - 1))]
      drawBones(group, playback.bones, sample.joints)
      drawMuscles(group, sample.muscles)
    },
    dispose() {
      cancelAnimationFrame(frame)
      observer.disconnect()
      controls.dispose()
      clear(group)
      renderer.dispose()
      renderer.domElement.remove()
    },
  }
}

function drawBones(group, bones, joints) {
  for (const [start, end] of bones || []) {
    if (!joints[start] || !joints[end]) continue
    group.add(segment(joints[start], joints[end], 0.012, 0x2c2824))
    group.add(sphere(joints[start], 0.02, 0x1c1915))
    group.add(sphere(joints[end], 0.02, 0x1c1915))
  }
}

function drawMuscles(group, muscles) {
  for (const muscle of Object.values(muscles || {})) {
    const points = muscle.polyline || []
    if (points.length < 2) continue
    const inactive = muscle.role === "inactive"
    for (let i = 0; i < points.length - 1; i += 1) {
      group.add(segment(points[i], points[i + 1], inactive ? 0.0035 : 0.007, ROLE_COLOR[muscle.role] || ROLE_COLOR.inactive))
    }
  }
}

function segment(a, b, radius, color) {
  const start = new THREE.Vector3(...a)
  const end = new THREE.Vector3(...b)
  const length = Math.max(start.distanceTo(end), 1e-4)
  const mesh = new THREE.Mesh(
    new THREE.CylinderGeometry(radius, radius, length, 7),
    new THREE.MeshStandardMaterial({ color, roughness: 0.55 }),
  )
  mesh.position.copy(start).add(end).multiplyScalar(0.5)
  mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), end.clone().sub(start).normalize())
  return mesh
}

function sphere(point, radius, color) {
  const mesh = new THREE.Mesh(
    new THREE.SphereGeometry(radius, 12, 10),
    new THREE.MeshStandardMaterial({ color, roughness: 0.45 }),
  )
  mesh.position.set(point[0], point[1], point[2])
  return mesh
}

function clear(group) {
  for (const child of [...group.children]) {
    child.geometry?.dispose()
    child.material?.dispose()
    group.remove(child)
  }
}

export const ROLE_HEX = {
  prime_mover: "#c23b3b",
  synergist: "#d4762c",
  stabilizer: "#2f6f9f",
  antagonist: "#7a6a8a",
  inactive: "#d5cfc6",
}
