"""Core recipes for the NewtonNet code."""

from __future__ import annotations

from importlib.util import find_spec
from typing import TYPE_CHECKING

import numpy as np
from ase.vibrations.data import VibrationsData
from monty.dev import requires

from quacc import get_settings, job
from quacc.runners.ase import Runner
from quacc.runners.thermo import ThermoRunner
from quacc.schemas.ase import summarize_opt_run, summarize_run, summarize_vib_and_thermo
from quacc.utils.dicts import recursive_dict_merge

has_sella = bool(find_spec("sella"))
has_mace = bool(find_spec("mace"))

if has_sella:
    from sella import Sella
if has_mace:
    from mace.calculators import MACECalculator, mace_off

if TYPE_CHECKING:
    from typing import Any

    from ase.atoms import Atoms

    from quacc.types import (
        Filenames,
        OptParams,
        OptSchema,
        RunSchema,
        SourceDirectory,
        VibThermoSchema,
    )


@job
@requires(
    has_mace, "MACE must be installed. Refer to the quacc documentation."
)
def static_job(
    atoms: Atoms,
    copy_files: SourceDirectory | dict[SourceDirectory, Filenames] | None = None,
    **calc_kwargs,
) -> RunSchema:
    """
    Carry out a single-point calculation.

    Parameters
    ----------
    atoms
        Atoms object
    copy_files
        Files to copy (and decompress) from source to the runtime directory.
    **calc_kwargs
        Custom kwargs for the mace_off calculator. Set a value to
        `quacc.Remove` to remove a pre-existing key entirely.

    Returns
    -------
    RunSchema
        Dictionary of results, specified in [quacc.schemas.ase.summarize_run][].
        See the type-hint for the data structure.
    """
    settings = get_settings()
    calc_defaults = {
        # "model_path": settings.NEWTONNET_MODEL_PATH,
        # "settings_path": settings.NEWTONNET_CONFIG_PATH,
    }
    calc_flags = recursive_dict_merge(calc_defaults, calc_kwargs)

    calc = mace_off(default_dtype="float64", **calc_flags)
    final_atoms = Runner(atoms, calc, copy_files=copy_files).run_calc()

    return summarize_run(
        final_atoms, atoms, additional_fields={"name": "mace_off Static"}
    )


@job
@requires(
    has_mace, "MACE must be installed. Refer to the quacc documentation."
)
def relax_job(
    atoms: Atoms,
    opt_params: OptParams | None = None,
    copy_files: SourceDirectory | dict[SourceDirectory, Filenames] | None = None,
    **calc_kwargs,
) -> OptSchema:
    """
    Relax a structure.

    Parameters
    ----------
    atoms
        Atoms object
    opt_params
        Dictionary of custom kwargs for the optimization process. For a list
        of available keys, refer to [quacc.runners.ase.Runner.run_opt][].
    copy_files
        Files to copy (and decompress) from source to the runtime directory.
    **calc_kwargs
        Dictionary of custom kwargs for the mace_off calculator. Set a value to
        `quacc.Remove` to remove a pre-existing key entirely.

    Returns
    -------
    OptSchema
        Dictionary of results, specified in [quacc.schemas.ase.summarize_opt_run][].
        See the type-hint for the data structure.
    """
    settings = get_settings()
    calc_defaults = {
        # "model_path": settings.NEWTONNET_MODEL_PATH,
        # "settings_path": settings.NEWTONNET_CONFIG_PATH,
    }
    opt_defaults = {"optimizer": Sella} if has_sella else {}

    calc_flags = recursive_dict_merge(calc_defaults, calc_kwargs)
    opt_flags = recursive_dict_merge(opt_defaults, opt_params)

    calc = mace_off(default_dtype="float64", **calc_flags)
    dyn = Runner(atoms, calc, copy_files=copy_files).run_opt(**opt_flags)
    return summarize_opt_run(dyn, additional_fields={"name": "mace_off Relax"})


@job
@requires(
    has_mace, "MACE must be installed. Refer to the quacc documentation."
)
def freq_job(
    atoms: Atoms,
    temperature: float = 298.15,
    pressure: float = 1.0,
    copy_files: SourceDirectory | dict[SourceDirectory, Filenames] | None = None,
    **calc_kwargs,
) -> VibThermoSchema:
    """
    Perform a frequency calculation using the given atoms object.

    Parameters
    ----------
    atoms
        The atoms object representing the system.
    temperature
        The temperature for the thermodynamic analysis.
    pressure
        The pressure for the thermodynamic analysis.
    copy_files
        Files to copy (and decompress) from source to the runtime directory.
    **calc_kwargs
        Custom kwargs for the mace_off calculator. Set a value to
        `quacc.Remove` to remove a pre-existing key entirely.

    Returns
    -------
    VibThermoSchema
        Dictionary of results. See the type-hint for the data structure.
    """
    settings = get_settings()
    calc_defaults = {
        # "model_path": settings.NEWTONNET_MODEL_PATH,
        # "settings_path": settings.NEWTONNET_CONFIG_PATH,
        "hess_method": "autograd",
    }
    calc_flags = recursive_dict_merge(calc_defaults, calc_kwargs)

    calc = mace_off(default_dtypes='float64', **calc_flags)
    final_atoms = Runner(atoms, calc, copy_files=copy_files).run_calc()

    summary = summarize_run(
        final_atoms, atoms, additional_fields={"name": "mace_off Hessian"}
    )

    hessian = calc.get_hessian(final_atoms)
    n_atoms = np.shape(hessian)[1]
    vib = VibrationsData(final_atoms, np.reshape(hessian, (n_atoms, 3, n_atoms, 3)))
    igt = ThermoRunner(
        final_atoms, vib.get_frequencies(), energy=summary["results"]["energy"]
    ).run_ideal_gas()

    return summarize_vib_and_thermo(
        vib,
        igt,
        temperature=temperature,
        pressure=pressure,
        additional_fields={"name": "ASE Vibrations and Thermo Analysis"},
    )


def _add_stdev_and_hess(summary: dict[str, Any], **calc_kwargs) -> dict[str, Any]:
    """
    Calculate and add standard deviation values and Hessians to the summary.

    This function takes a summary dictionary containing information about a
    molecular trajectory and calculates the standard deviation of various
    properties using the mace_off machine learning calculator. It adds the
    calculated standard deviation values and Hessians to each configuration in
    the trajectory.

    Parameters
    ----------
    summary
        A dictionary containing information about the molecular trajectory.
    **calc_kwargs
        Custom kwargs for the mace_off calculator. Set a value to
        `quacc.Remove` to remove a pre-existing key entirely.

    Returns
    -------
    dict[str, Any]
        The modified summary dictionary with added standard deviation and
        Hessian values.
    """
    settings = get_settings()
    calc_defaults = {
        # "model_path": settings.NEWTONNET_MODEL_PATH,
        # "settings_path": settings.NEWTONNET_CONFIG_PATH,
    }
    calc_flags = recursive_dict_merge(calc_defaults, calc_kwargs)
    for i, atoms in enumerate(summary["trajectory"]):
        calc = mace_off(default_dtype='float64', **calc_flags)
        summary["trajectory_results"][i]["hessian"] = calc.get_hessian(atoms)

    return summary
