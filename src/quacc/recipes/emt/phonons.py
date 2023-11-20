"""Phonon recipes for EMT"""
from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING

from quacc import flow
from quacc.recipes.common.phonons import phonon_flow as phonon_flow_
from quacc.recipes.emt.core import static_job

if TYPE_CHECKING:
    from typing import Any

    from ase import Atoms
    from numpy.typing import ArrayLike

    from quacc.recipes.phonons import PhononSchema


@flow
def phonon_flow(
    atoms: Atoms,
    supercell_matrix: ArrayLike = ((2, 0, 0), (0, 2, 0), (0, 0, 2)),
    atom_disp: float = 0.01,
    t_step: float = 10,
    t_min: float = 0,
    t_max: float = 1000,
    static_job_kwargs: dict[str, Any] | None = None,
) -> PhononSchema:
    """
    Carry out a phonon calculation.

    Parameters
    ----------
    atoms
        Atoms object
    supercell_matrix
        Supercell matrix to use. Defaults to 2x2x2 supercell.
    atom_disp
        Atomic displacement (A).
    t_step
        Temperature step (K).
    t_min
        Min temperature (K).
    t_max
        Max temperature (K).
    static_job_kwargs
        Additional keyword arguments for [quacc.recipes.emt.core.static_job][]
        for the force calculations.

    Returns
    -------
    PhononSchema
        Dictionary of results from [quacc.schemas.phonons.summarize_phonopy][]
    """
    static_job_kwargs = static_job_kwargs or {}

    return phonon_flow_(
        atoms,
        partial(static_job, **static_job_kwargs),
        supercell_matrix=supercell_matrix,
        atom_disp=atom_disp,
        t_step=t_step,
        t_min=t_min,
        t_max=t_max,
        additional_fields={"name": "EMT Phonons"},
    )