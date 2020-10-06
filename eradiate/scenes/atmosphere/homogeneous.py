import warnings
from copy import deepcopy

import attr
import numpy as np
from scipy.constants import physical_constants

import eradiate
from .base import Atmosphere
from ..core import Factory
from ...util.units import config_default_units as cdu
from ...util.units import kernel_default_units as kdu
from ...util.units import ureg

# Physical constants
#: Loschmidt constant [km^-3].
_LOSCHMIDT = ureg.Quantity(
    *physical_constants["Loschmidt constant (273.15 K, 101.325 kPa)"][:2]).to(
    "km^-3")
#: Refractive index of dry air [dimensionless].
_IOR_DRY_AIR = ureg.Quantity(1.0002932, "")


def kf(ratio=0.0279):
    """Compute the King correction factor.

    Parameter ``ratio`` (float):
        Depolarisation ratio [dimensionless].
        The default value is the mean depolarisation ratio for dry air given by
        :cite:`Young1980RevisedDepolarizationCorrections`.

    Returns → float:
        King correction factor [dimensionless].
    """

    return (6.0 + 3.0 * ratio) / (6.0 - 7.0 * ratio)


@ureg.wraps(ureg.km ** -1,
            (ureg.nm,
             ureg.km ** -3,
             ureg.dimensionless, None, None),
            strict=False)
def sigma_s_single(wavelength=550.,
                   number_density=_LOSCHMIDT.magnitude,
                   refractive_index=_IOR_DRY_AIR.magnitude,
                   king_factor=1.049,
                   depolarisation_ratio=None):
    """Compute the Rayleigh scattering coefficient for one type of scattering
    particles.

    When default values are used, this provides the Rayleigh scattering
    coefficient for air at 550 nm in standard temperature and pressure
    conditions.

    Parameter ``wavelength`` (float):
        Wavelength [nm].

    Parameter ``number_density`` (float):
        Number density of the scattering particles [km^-3].

    Parameter ``refractive_index`` (float):
        Refractive index of scattering particles [dimensionless].
        Default value is the air refractive index at 550 nm as
        given by :cite:`Bates1984RayleighScatteringAir`.

    Parameter ``king_factor`` (float):
        King correction factor of the scattering particles [dimensionless].
        Default value is the air effective King factor at 550 nm as given by
        :cite:`Bates1984RayleighScatteringAir`. Overridden by a call to
        :func:`kf` if ``depolarisation_ratio`` is set.

    Parameter ``depolarisation_ratio`` (float or None):
        Depolarisation ratio [dimensionless].
        If this parameter is set, then its value is used to compute the value of
        the corresponding King factor and supersedes ``king_factor``.

    Returns → float:
        Scattering coefficient [km^-1].
    """
    if depolarisation_ratio is not None:
        king_factor = kf(depolarisation_ratio)

    return \
        8. * np.power(np.pi, 3) / (3. * np.power((wavelength * 1e-12), 4)) / \
        number_density * \
        np.square(np.square(refractive_index) - 1.) * king_factor


@attr.s()
@Factory.register("rayleigh_homogeneous")
class RayleighHomogeneousAtmosphere(Atmosphere):
    """Rayleigh homogeneous atmosphere scene generation helper
    [:factorykey:`rayleigh_homogeneous`].

    This class builds an atmosphere consisting of a non-absorbing
    homogeneous medium. Scattering uses the Rayleigh phase function and the
    Rayleigh scattering coefficient of a single gas.

    .. admonition:: Configuration example
        :class: hint

        Default:
            .. code:: python

               {
                   "height": 100.,
                   "width": "auto",
               }

    .. admonition:: Configuration format
        :class: hint

        ``height`` (float):
            Height of the atmosphere [km].

            Default: 100.

        ``width`` (float or string)
            Width of the atmosphere [km].
            If the string ``"auto"`` is passed, a value will be estimated to
            ensure that the medium is optically thick.

            Default: auto.

        ``sigma_s`` (float or dict):
            Atmosphere scattering coefficient value [km^-1] or keyword argument
            dictionary to be passed to
            :func:`~eradiate.scenes.atmosphere.rayleigh.sigma_s_single`.
            If a dictionary is passed and misses arguments,
            :func:`~eradiate.scenes.atmosphere.rayleigh.sigma_s_single`'s
            defaults apply as usual.

            Note that :func:`~eradiate.scenes.atmosphere.rayleigh.sigma_s_single`
            will always be evaluated according to mode configuration,
            regardless any value which could be passed as the ``wavelength``
            argument of :func:`~eradiate.scenes.atmosphere.rayleigh.sigma_s_single`.

            Default: {}.
    """

    # Class attributes
    @classmethod
    def config_schema(cls):
        d = super(RayleighHomogeneousAtmosphere, cls).config_schema()
        d.update({
            "height": {
                "type": "number",
                "min": 0.,
                "default": 1.e+2
            },
            "height_unit": {
                "type": "string",
                "default": cdu.get_str("length")
            },
            "width": {
                "anyof": [{
                    "type": "number",
                    "min": 0.
                }, {
                    "type": "string",
                    "allowed": ["auto"]
                }],
                "default": "auto"
            },
            "width_unit": {
                "type": "string",
                "required": False,
                "nullable": True,
                "default_setter": lambda doc:
                None if isinstance(doc["width"], str)
                else cdu.get_str("length")
            },
            "sigma_s": {
                "anyof": [{
                    "type": "number",
                    "min": 0.
                }, {
                    "type": "string",
                    "allowed": ["auto"]
                }],
                "default": "auto"
            },
            "sigma_s_unit": {
                "type": "string",
                "default": f"{cdu.get_str('length')}^-1"
            }
        })
        return d

    @property
    def _albedo(self):
        """Return albedo."""
        return 1.

    @property
    def _width(self):
        """Return scene width based on configuration."""

        # If width is not set, compute a value corresponding to an optically
        # thick layer (10x scattering mean free path)
        width = self.config.get_quantity("width")

        if width == "auto":
            return 10. / self._sigma_s
        else:
            return width

    @property
    def _sigma_s(self):
        """Return scattering coefficient based on configuration."""
        sigma_s = self.config.get("sigma_s")

        if sigma_s == "auto":
            wavelength = eradiate.mode.config["wavelength"]
            return sigma_s_single(wavelength=wavelength)
        else:
            sigma_s_unit = self.config.get("sigma_s_unit")
            return ureg.Quantity(sigma_s, sigma_s_unit)

    def phase(self):
        return {f"phase_{self.id}": {"type": "rayleigh"}}

    def media(self, ref=False):
        if ref:
            phase = {"type": "ref", "id": f"phase_{self.id}"}
        else:
            phase = self.phase()[f"phase_{self.id}"]

        return {
            f"medium_{self.id}": {
                "type": "homogeneous",
                "phase": phase,
                "sigma_t": {
                    "type": "uniform",
                    "value": self._sigma_s.to(f"{kdu.get('length')}^-1").magnitude
                },
                "albedo": {
                    "type": "uniform",
                    "value": self._albedo
                },
            }
        }

    def shapes(self, ref=False):
        from eradiate.kernel.core import ScalarTransform4f

        if ref:
            medium = {"type": "ref", "id": f"medium_{self.id}"}
        else:
            medium = self.media(ref=False)[f"medium_{self.id}"]

        width = self._width.to(kdu.get("length")).magnitude
        height = self.config.get_quantity("height").to(kdu.get("length")).magnitude
        height_offset = height * 0.01

        return {
            f"shape_{self.id}": {
                "type":
                    "cube",
                "to_world":
                    ScalarTransform4f([
                        [0.5 * width, 0., 0., 0.],
                        [0., 0.5 * width, 0., 0.],
                        [0., 0., 0.5 * (height + height_offset), 0.5 * (height - height_offset)],
                        [0., 0., 0., 1.],
                    ]),
                "bsdf": {
                    "type": "null"
                },
                "interior":
                    medium
            }
        }
