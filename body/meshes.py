"""Read Rajagopal bone meshes from the OpenSim ASCII VTP files.

Vertices stay in the body frame the .osim attaches them to. The viewer
moves each body with the solved pose.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


def load_body_meshes(model_path: Path, geometry_dir: Path) -> list[dict]:
    """Return [{body, file, vertices, indices}] for every mesh the model attaches."""
    root = ET.parse(model_path).getroot()
    meshes = []
    for body in root.iter("Body"):
        body_name = body.get("name")
        if not body_name:
            continue
        for mesh in body.iter("Mesh"):
            file_node = mesh.find("mesh_file")
            if file_node is None or not (file_node.text or "").strip():
                continue
            scale_node = mesh.find("scale_factors")
            scale = _vec(scale_node.text if scale_node is not None else None, (1.0, 1.0, 1.0))
            file_name = file_node.text.strip()
            path = geometry_dir / file_name
            vertices, indices = read_vtp(path)
            if scale != (1.0, 1.0, 1.0):
                vertices = [[v[0] * scale[0], v[1] * scale[1], v[2] * scale[2]] for v in vertices]
            meshes.append(
                {
                    "body": body_name,
                    "file": file_name,
                    "vertices": vertices,
                    "indices": indices,
                }
            )
    if not meshes:
        raise RuntimeError(f"No meshes found in {model_path}")
    return meshes


def read_vtp(path: Path) -> tuple[list[list[float]], list[int]]:
    root = ET.parse(path).getroot()
    piece = root.find("./PolyData/Piece")
    if piece is None:
        raise ValueError(f"{path} has no PolyData piece")
    points = _array(piece.find("./Points/DataArray"))
    if len(points) % 3 != 0:
        raise ValueError(f"{path} point array is not xyz triples")
    vertices = [points[i : i + 3] for i in range(0, len(points), 3)]
    polys = piece.find("Polys")
    if polys is None:
        raise ValueError(f"{path} has no polygons")
    connectivity = [int(v) for v in _array(polys.find("./DataArray[@Name='connectivity']"))]
    offsets = [int(v) for v in _array(polys.find("./DataArray[@Name='offsets']"))]
    indices: list[int] = []
    start = 0
    for offset in offsets:
        face = connectivity[start:offset]
        start = offset
        if len(face) < 3:
            continue
        for i in range(1, len(face) - 1):
            indices.extend((face[0], face[i], face[i + 1]))
    if not indices:
        raise ValueError(f"{path} produced no triangles")
    return vertices, indices


def _array(node) -> list[float]:
    if node is None or node.text is None:
        raise ValueError("Missing VTK DataArray")
    if (node.get("format") or "ascii") != "ascii":
        raise ValueError(f"Only ASCII VTP arrays are supported, got {node.get('format')}")
    return [float(part) for part in node.text.split()]


def _vec(text: str | None, default: tuple[float, float, float]) -> tuple[float, float, float]:
    if not text:
        return default
    parts = [float(part) for part in text.split()]
    if len(parts) != 3:
        return default
    return parts[0], parts[1], parts[2]
