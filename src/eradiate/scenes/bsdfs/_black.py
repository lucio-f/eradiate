from __future__ import annotations

import attrs

from ._core import BSDF
from ...kernel import UpdateParameter


@attrs.define(eq=False, slots=False)
class BlackBSDF(BSDF):
    """
    Black BSDF [``black``].

    This BSDF models a perfectly absorbing surface. It is equivalent to a
    :class:`.DiffuseBSDF` with zero reflectance.
    """

    @property
    def template(self) -> dict:
        # Inherit docstring
        return {
            "type": "diffuse",
            "reflectance": {"type": "uniform", "value": 0.0},
        }

    @property
    def params(self) -> dict[str, UpdateParameter]:
        # Inherit docstring
        return {}
