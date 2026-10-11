import * as THREE from "three"
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js"

const ROLE_COLOR = {
  prime_mover: 0xc23b3b,
  synergist: 0xd4762c,
  stabilizer: 0x2f6f9f,
  antagonist: 0x7a6a8a,
  inactive: 0xd5cfc6,
}

export function mountScene(element, { fullBody = false } = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setClearColor(0xefeae3)
  element.appendChild(renderer.domElement)
  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(32, 1, 0.05, 40)
  if (fullBody) {
    // Front-left, so the clip's left arm is toward the camera.
    camera.position.set(1.55, 1.15, -2.35)
  } else {
    camera.position.set(1.15, 1.15, 2.55)
  }
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.target.set(0.0, fullBody ? 1.15 : 0.95, fullBody ? -0.05 : 0.1)
  controls.update()
  scene.add(new THREE.HemisphereLight(0xfff8ef, 0xc8bfb4, 1.1))
  const sun = new THREE.DirectionalLight(0xffffff, 1.3)
  sun.position.set(1.5, 3, 2)
  scene.add(sun)
  const group = new THREE.Group()
  const stick = new THREE.Group()
  const bones = new THREE.Group()
  const muscles = new THREE.Group()
  group.add(stick, bones, muscles)
  scene.add(group)
  let bodyCatalog = null

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
    setBody(catalog) {
      bodyCatalog = catalog
      clear(bones)
      if (!catalog) return
      for (const mesh of catalog.meshes || []) {
        bones.add(boneMesh(mesh))
      }
    },
    setFrame(playback, index) {
      clear(stick)
      clear(muscles)
      if (!playback || !playback.frames.length) return
      const sample = playback.frames[Math.max(0, Math.min(index, playback.frames.length - 1))]
      if (sample.bodies && bodyCatalog) {
        poseBones(bones, sample.bodies)
        drawMuscleVolumes(muscles, sample.muscles)
        return
      }
      drawBones(stick, playback.bones, sample.joints)
      drawMuscles(stick, sample.muscles)
    },
    dispose() {
      cancelAnimationFrame(frame)
      observer.disconnect()
      controls.dispose()
      clear(stick)
      clear(bones)
      clear(muscles)
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

function boneMesh(spec) {
  const geometry = new THREE.BufferGeometry()
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(spec.vertices.flat(), 3))
  geometry.setIndex(spec.indices)
  geometry.computeVertexNormals()
  const mesh = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({ color: 0xe4d5c4, roughness: 0.72, metalness: 0.02, side: THREE.DoubleSide }),
  )
  mesh.matrixAutoUpdate = false
  mesh.userData.body = spec.body
  return mesh
}

function poseBones(group, bodies) {
  for (const mesh of group.children) {
    const matrix = bodies[mesh.userData.body]
    if (!matrix) continue
    mesh.matrix.fromArray(matrix)
  }
}

function drawMuscleVolumes(group, muscles) {
  for (const muscle of Object.values(muscles || {})) {
    const points = muscle.polyline || []
    const radius = muscle.role === "prime_mover" ? 0.014 : muscle.role === "synergist" ? 0.011 : 0.008
    for (let i = 0; i < points.length - 1; i += 1) {
      group.add(segment(points[i], points[i + 1], radius, ROLE_COLOR[muscle.role] || ROLE_COLOR.inactive))
    }
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
