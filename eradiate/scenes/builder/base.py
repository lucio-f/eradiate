""" Base classes used to build XML generators """

from abc import ABC, abstractmethod
from copy import deepcopy

import attr
import lxml.etree as etree
import numpy
from attr.validators import instance_of as is_instance, optional as is_optional

from ...util import ensure_array
from .util import seq_to_str, has_length, load


@attr.s
class Object(ABC):
    """
    Basic XML tree node object. It provides the basic XML node generation code,
    the facilities to recursively expend into an XML tree if needed and a method
    to convert to XML code.

    This class is not meant to be used directly and should rather be inherited
    by concrete types.
    """

    @property
    @classmethod
    @abstractmethod
    def _tag(cls):
        """
        The XML tag associated with the object
        """
        pass

    name = attr.ib(
        kw_only=True,
        default=None,
        validator=is_optional(is_instance(str))
    )  # An optional instance attribute used to specify parameter names in the scene language

    @classmethod
    def convert(cls, x):
        """
        Convert x to the current type. By default, implements a simple copy
        constructor.
        """
        if isinstance(x, cls):
            return deepcopy(x)
        else:
            raise TypeError(f"cannot convert '{type(x).__name__}' "
                            f"to '{cls.__name__}'")

    def to_etree(self):
        """
        Generate an XML tree node corresponding to the current object.
        """
        e = etree.Element(self._tag)
        if self.name is not None:
            e.set("name", self.name)
        return e

    def to_xml(self, pretty_print=False, add_version=False):
        """
        Emit the XML code corresponding to the tree of which the current object
        is the root node.

        :param (bool) pretty_print: If `True`, the emitted XML code will be
            indented for improved legibility.
        :param (bool) add_version: If `True`, the top-level node will be added
            the ``version`` attribute.
        :return (str): XML code.
        """
        e = self.to_etree()
        if add_version:
            e.set("version", "0.1.0")
        return etree.tostring(e, encoding="unicode",
                              pretty_print=pretty_print)


class Instantiable:
    """
    Mixin allowing an object to be instantiated.
    """

    def instantiate(self):
        return load(self)


@attr.s
class Plugin(Object, Instantiable):
    """
    This abstract class is to be used to write tree node classes used to 
    initialise plugins.
    """

    @property
    @classmethod
    @abstractmethod
    def _type(cls):
        """
        The type attribute is used to specify the actual plugin file to load.
        """
        pass

    _params = []  # Ordered list of parameters which will be added upon conversion to lxml Element

    def to_etree(self):
        e = super().to_etree()
        e.set("type", str(self._type))

        for param in self._params:
            x = getattr(self, param, None)
            if x is not None:
                e.append(x.to_etree())

        return e


@attr.s
class ReferablePlugin(Plugin):
    """
    This abstract class is to be used for plugins meant to be referenced in the
    XML scene language (e.g. bsdfs). It simply adds an optional keyword-only
    attribute ``id``.
    """
    _id = attr.ib(
        kw_only=True,
        default=None,
        validator=is_optional(is_instance(str))
    )  # Identifier string to be used later using a `Ref` object.

    def get_ref(self):
        """
        Returns a reference to itself if relevant.

        :return (Ref or None): `Ref` object pointing to current instance if
            the ID field is set; `None` otherwise.
        """
        if self._id is not None:
            return Ref(self._id)
        else:
            return None

    def to_etree(self):
        e = super().to_etree()
        if self._id is not None:
            e.set("id", self._id)
        return e


@attr.s
class Ref(Object):
    """
    A reference to another referable item.
    """

    _tag = "ref"
    _id = attr.ib(validator=is_instance(str))

    def to_etree(self):
        e = super().to_etree()
        e.set("id", self._id)
        return e


@attr.s
class Bool(Object):
    """
    An boolean.
    """
    _tag = "boolean"
    value = attr.ib(converter=bool)

    @classmethod
    def convert(cls, x):
        if isinstance(x, bool):
            return cls(value=x)
        else:
            return super().convert(x)

    def to_etree(self):
        e = super().to_etree()
        e.set("value", str(self.value).lower())
        return e


@attr.s
class Int(Object):
    """
    An integer number.
    """
    _tag = "integer"
    value = attr.ib(converter=int)

    @classmethod
    def convert(cls, x):
        if isinstance(x, int):
            return cls(value=x)
        else:
            return super().convert(x)

    def to_etree(self):
        e = super().to_etree()
        e.set("value", str(self.value))
        return e


@attr.s
class Float(Object):
    """
    A floating-point number.
    """
    _tag = "float"
    value = attr.ib(converter=float)

    @classmethod
    def convert(cls, x):
        if isinstance(x, float):
            return cls(value=x)
        else:
            return super().convert(x)

    def to_etree(self):
        e = super().to_etree()
        e.set("value", str(self.value))
        return e


@attr.s
class String(Object):
    """
    A string.
    """
    _tag = "string"
    value = attr.ib(converter=str)

    @classmethod
    def convert(cls, x):
        if isinstance(x, str):
            return cls(value=x)
        else:
            return super().convert(x)

    def to_etree(self):
        e = super().to_etree()
        e.set("value", self.value)
        return e


@attr.s
class Point(Object):
    """
    A point in the 3-dimensional space.
    """
    _tag = "point"
    value = attr.ib(default=(0., 0., 0.),
                    converter=ensure_array,
                    validator=has_length(3))

    @classmethod
    def convert(cls, x):
        if isinstance(x, (tuple, list, numpy.ndarray)):
            return cls(value=ensure_array(x))
        else:
            return super().convert(x)

    def to_etree(self):
        e = super().to_etree()
        e.set("value", seq_to_str(self.value))
        return e


@attr.s
class Vector(Object):
    """
    A vector of floating-point numbers.
    """
    # Implement comparison manually [https://github.com/python-attrs/attrs/issues/435]

    _tag = "vector"
    value = attr.ib(converter=ensure_array)

    @classmethod
    def convert(cls, x):
        if isinstance(x, (float, tuple, list, numpy.ndarray)):
            return cls(value=ensure_array(x))
        else:
            return super().convert(x)

    def to_etree(self):
        e = super().to_etree()
        e.set("value", seq_to_str(self.value))
        return e
