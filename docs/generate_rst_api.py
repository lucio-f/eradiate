import glob
import os
from importlib import import_module
from pathlib import Path
from textwrap import dedent, indent

from eradiate._config import EradiateConfig, format_help_dicts_rst


# Auto-generation disclaimer text
HEADER = dedent(
    """
    ..
      This file was automatically generated by docs/generate_rst_api.py. The

          make docs-rst-api

      target automates this process.
    """
).strip()


def generate_env_vars_docs():
    outdir = Path(__file__).parent.absolute() / "rst/reference_api/generated/env_vars"
    os.makedirs(outdir, exist_ok=True)
    outfile = outdir / "env_vars.rst"
    print(f"Generating {outfile}")
    with open(outfile, "w") as f:
        f.write(
            dedent(
                """
                .. _sec-config-env_vars:

                Environment variables
                ---------------------
                """
            )
            + "\n"
        )
        f.write(
            EradiateConfig.generate_help(
                formatter=format_help_dicts_rst, display_defaults=True
            )
        )


# List of (module, variable) pairs
FACTORIES = [
    ("eradiate.radprops.rad_profile", "rad_profile_factory"),
    ("eradiate.scenes.atmosphere", "atmosphere_factory"),
    ("eradiate.scenes.atmosphere", "particle_distribution_factory"),
    ("eradiate.scenes.biosphere", "biosphere_factory"),
    ("eradiate.scenes.illumination", "illumination_factory"),
    ("eradiate.scenes.integrators", "integrator_factory"),
    ("eradiate.scenes.measure", "measure_factory"),
    ("eradiate.scenes.phase", "phase_function_factory"),
    ("eradiate.scenes.spectra", "spectrum_factory"),
    ("eradiate.scenes.surface", "surface_factory"),
]


def factory_data_docs(modname, varname, uline="="):
    """
    Return rst code for a factory instance located at modname.varname.
    """
    factory = getattr(import_module(modname), varname)
    fullname = f"{modname}.{varname}"
    underline = uline * len(fullname)

    table_header = ".. list-table::\n   :widths: 25 75"
    table_rows = "\n".join(
        [
            f"   * - ``{key}``\n     - :class:`{entry.cls.__name__}`"
            for key, entry in sorted(factory.registry.items())
        ]
    )
    table = "\n".join([table_header, "", table_rows])

    return f"""{fullname}
{underline}

.. data:: {modname}.{varname}
   :annotation:

   Instance of :class:`{factory.__class__.__module__}.{factory.__class__.__qualname__}`

   .. rubric:: Registered types

{indent(table, "   ")}

""".lstrip()


def generate_factory_docs(cli=False):
    """
    Generate rst documents to display factory documentation.
    """
    outdir = Path(__file__).parent.absolute() / "rst/reference_api/generated/factory"
    if cli:
        print(f"Generating factory docs in {outdir}")
    os.makedirs(outdir, exist_ok=True)

    for modname, varname in FACTORIES:
        outfname = outdir / f"{modname}.{varname}.rst"
        if cli:
            print(f"Writing {outfname.relative_to(outdir)}")

        with open(outfname, "w") as outfile:
            generated = factory_data_docs(modname, varname)
            outfile.write("\n".join([HEADER, "", generated]))


if __name__ == "__main__":
    generate_factory_docs(cli=True)
    generate_env_vars_docs()
