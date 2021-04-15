from eradiate.scenes.core import KernelDict
from eradiate.scenes.surface import BlackSurface, LambertianSurface


def test_black(mode_mono):
    # Default constructor
    bs = BlackSurface()

    # Check if produced scene can be instantiated
    kernel_dict = KernelDict.new(bs)
    assert kernel_dict.load() is not None

    # Check if the correct kernel dict is created
    ls = LambertianSurface(reflectance={"type": "uniform", "value": 0})

    assert KernelDict.new(ls) == KernelDict.new(bs)
