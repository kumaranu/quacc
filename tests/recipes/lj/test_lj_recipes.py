import os
from shutil import rmtree

import numpy as np
import pytest
from ase.build import molecule

from quacc.recipes.lj.core import relax_job, static_job


def teardown_module():
    for f in os.listdir(os.getcwd()):
        if (
            f.endswith(".log")
            or f.endswith(".pckl")
            or f.endswith(".traj")
            or f.endswith(".out")
            or ".gz" in f
        ):
            os.remove(f)
        if "quacc-tmp" in f or f == "tmp_dir":
            rmtree(f)


def test_static_Job():
    atoms = molecule("H2O")

    output = static_job(atoms)
    assert output["natoms"] == len(atoms)
    assert output["parameters"]["epsilon"] == 1.0
    assert output["parameters"]["sigma"] == 1.0
    assert output["parameters"]["rc"] == 3
    assert output["parameters"]["ro"] == 0.66 * 3
    assert output["results"]["energy"] == pytest.approx(1.772068860679255)

    output = static_job(atoms, lj_kwargs={"epsilon": 2.0, "rc": 0.5})
    assert output["natoms"] == len(atoms)
    assert output["parameters"]["epsilon"] == 2.0
    assert output["parameters"]["sigma"] == 1.0
    assert output["parameters"]["rc"] == 0.5
    assert output["parameters"]["ro"] == 0.66 * 0.5
    assert output["results"]["energy"] == pytest.approx(0.0)


def test_relax_Job():
    atoms = molecule("H2O")

    output = relax_job(atoms)
    assert output["natoms"] == len(atoms)
    assert output["parameters"]["epsilon"] == 1.0
    assert output["parameters"]["sigma"] == 1.0
    assert output["parameters"]["rc"] == 3
    assert output["parameters"]["ro"] == 0.66 * 3
    assert output["results"]["energy"] == pytest.approx(-2.983561029599189)
    assert np.max(np.linalg.norm(output["results"]["forces"], axis=1)) < 0.01

    output = relax_job(atoms, fmax=0.03, lj_kwargs={"epsilon": 2.0, "rc": 0.5})
    assert output["natoms"] == len(atoms)
    assert output["parameters"]["epsilon"] == 2.0
    assert output["parameters"]["sigma"] == 1.0
    assert output["parameters"]["rc"] == 0.5
    assert output["parameters"]["ro"] == 0.66 * 0.5
    assert output["results"]["energy"] == pytest.approx(0.0)
    assert np.max(np.linalg.norm(output["results"]["forces"], axis=1)) < 0.03