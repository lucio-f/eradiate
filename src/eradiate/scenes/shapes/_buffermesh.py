from __future__ import annotations

import typing as t

import attrs
import mitsuba as mi
import numpy as np
import pint
import pinttr

from ._core import Shape
from ..core import InstanceSceneElement, Param, traverse
from ...attrs import documented, parse_docs
from ...contexts import KernelDictContext
from ...units import unit_context_config as ucc
from ...units import unit_context_kernel as uck


@parse_docs
@attrs.define(eq=False, slots=False)
class BufferMeshShape(Shape, InstanceSceneElement):
    """
    Buffer mesh shape [``buffer_mesh``].

    This shape represents a triangulated mesh directly defined by lists of vertex
    positions and faces.
    """

    vertices: pint.Quantity = documented(
        pinttr.field(
            validator=pinttr.validators.has_compatible_units,
            units=ucc.deferred("length"),
            kw_only=True,
        ),
        doc="List of vertex positions. The passed list must contain a (n, 3) list"
        "of three dimensional points.\n\nUnit-enabled field (default: ucc['length']).",
        type="quantity",
        init_type="array-like",
    )

    faces: np.ndarray = documented(
        attrs.field(
            kw_only=True,
            converter=np.array,
        ),
        doc="List of face definitions. The passed list must contain a (n, 3) list"
        "of three vertex indices defining triangles.",
        type="ndarray",
        init_type="array-like",
    )

    @vertices.validator
    @faces.validator
    def _vertex_face_validator(self, attribute, value):
        if value.ndim != 2 or value.shape[0] == 0 or value.shape[1] != 3:
            raise ValueError(
                f"while validating {attribute.name}, must be an array of shape "
                f"(n, 3), got {value.shape}"
            )

    @property
    def instance(self) -> "mitsuba.Object":
        if self.bsdf is not None:
            template, _ = traverse(self.bsdf)
            bsdf = mi.load_dict(template.render(ctx=KernelDictContext()))
        else:
            bsdf = None

        props = mi.Properties()
        props["mesh_bsdf"] = bsdf

        mesh = mi.Mesh(
            name=self.id,
            face_count=self.faces.shape[0],
            vertex_count=self.vertices.shape[0],
            has_vertex_normals=False,
            has_vertex_texcoords=False,
            props=props,
        )

        vertices = self.vertices.m_as(uck.get("length"))
        mesh_params = mi.traverse(mesh)
        mesh_params["vertex_positions"] = vertices.ravel()
        mesh_params["faces"] = self.faces.ravel()
        mesh_params.update()

        return mesh

    @property
    def params(self) -> t.Optional[t.Dict[str, Param]]:
        if self.bsdf is None:
            return None

        _, params = traverse(self.bsdf)
        return {f"bsdf.{k}": v for k, v in params.items()}
