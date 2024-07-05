from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def set_seed():
    np.random.seed(42)  # noqa: NPY002


pytest.importorskip("sella")
pytest.importorskip("mace")
from pathlib import Path

import numpy as np
from ase import Atoms
from ase.build import molecule

from quacc import _internally_set_settings
from quacc.recipes.mace.core import freq_job, relax_job, static_job
from quacc.recipes.mace.ts import (
    geodesic_job,
    geodesic_ts_job,
    irc_job,
    neb_job,
    neb_ts_job,
    quasi_irc_job,
    ts_job,
)

current_file_path = Path(__file__).parent


def setup_module():
    _internally_set_settings(
        {
            # "NEWTONNET_CONFIG_PATH": current_file_path / "config0.yml",
            # "NEWTONNET_MODEL_PATH": current_file_path / "best_model_state.tar",
            "CHECK_CONVERGENCE": False,
        }
    )


def teardown_module():
    _internally_set_settings(reset=True)


def test_static_job(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    atoms = molecule("H2O")
    output = static_job(atoms)
    assert output["spin_multiplicity"] == 1
    assert output["natoms"] == len(atoms)
    assert output["results"]["energy"] == pytest.approx(-2081.11639716893)
    assert np.array_equal(output["atoms"].get_positions(), atoms.get_positions())


def test_relax_job(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    atoms = molecule("H2O")
    output = relax_job(atoms)
    assert output["spin_multiplicity"] == 1
    assert output["natoms"] == len(atoms)
    assert output["results"]["energy"] == pytest.approx(-2081.1213729010956)
    assert not np.array_equal(output["atoms"].get_positions(), atoms.get_positions())
    assert np.max(np.linalg.norm(output["results"]["forces"], axis=1)) < 0.01


def test_freq_job(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    atoms = molecule("H2O")
    output = freq_job(atoms)
    assert output["atoms"] == molecule("H2O")
    assert len(output["results"]["vib_freqs_raw"]) == 9
    assert len(output["results"]["vib_freqs"]) == 3
    assert output["results"]["vib_freqs_raw"][-1] == pytest.approx(3808.944484676018)
    assert output["results"]["vib_freqs"][0] == pytest.approx(1660.1454432991443)
    assert output["results"]["vib_freqs"][-1] == pytest.approx(3808.944484676018)
    assert output["results"]["n_imag"] == 0
    assert output["results"]["imag_vib_freqs"] == []

    assert output["symmetry"]["point_group"] == "C2v"
    assert output["symmetry"]["rotation_number"] == 2
    assert output["symmetry"]["linear"] is False
    assert output["results"]["energy"] == pytest.approx(-2081.11639716893)
    assert output["results"]["enthalpy"] == pytest.approx(-2080.4434696224343)
    assert output["results"]["entropy"] == pytest.approx(0.0019584038251916733)
    assert output["results"]["gibbs_energy"] == pytest.approx(-2081.027367722915)

    atoms = molecule("CH3")
    output = freq_job(atoms, temperature=1000, pressure=20)
    assert output["atoms"] == molecule("CH3")
    assert len(output["results"]["vib_freqs_raw"]) == 12
    assert len(output["results"]["vib_freqs"]) == 6
    assert output["results"]["vib_energies_raw"][0] == pytest.approx(
        -0.005371676195057368
    )


def test_ts_job_with_default_args(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # Define test inputs
    atoms = molecule("H2O")

    # Call the function
    output = ts_job(atoms)

    # Perform assertions on the result
    assert isinstance(output, dict)

    assert "freq_job" in output
    assert output["results"]["energy"] == pytest.approx(-2077.4843066212175)
    assert output["freq_job"]["results"]["imag_vib_freqs"][0] == pytest.approx(
        -8581.247638101131, abs=1e-6
    )


def test_ts_job_with_custom_hessian(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Define test inputs
    atoms = molecule("H2O")
    use_custom_hessian = True
    opt_params = {"max_steps": 4}
    # Call the function
    output = ts_job(atoms, use_custom_hessian=use_custom_hessian, opt_params=opt_params)

    # Perform assertions on the result
    assert isinstance(output, dict)
    assert "results" in output["freq_job"]


def test_irc_job_with_default_args(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Define test inputs
    atoms = molecule("H2O")

    # Call the function
    output = irc_job(atoms)

    # Perform assertions on the result
    assert isinstance(output, dict)

    assert output["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["freq_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)


def test_irc_job_with_custom_fmax(tmp_path, monkeypatch):
    from ase.build import molecule

    from quacc.recipes.mace.ts import irc_job

    monkeypatch.chdir(tmp_path)
    # Define test inputs
    atoms = molecule("H2O")
    fmax = 0.001

    # Call the function
    output = irc_job(atoms, opt_params={"fmax": fmax})

    # Perform assertions on the result
    assert isinstance(output, dict)

    assert output["results"]["energy"] == pytest.approx(-2081.1213729036917)
    assert output["freq_job"]["results"]["energy"] == pytest.approx(-2081.1213729036917)


def test_irc_job_with_custom_max_steps(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Define test inputs
    atoms = molecule("H2O")
    max_steps = 500

    # Call the function
    output = irc_job(atoms, opt_params={"max_steps": max_steps})

    # Perform assertions on the result
    assert isinstance(output, dict)

    assert output["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["freq_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)


def test_irc_job_with_custom_temperature_and_pressure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Define test inputs
    atoms = molecule("H2O")
    temperature = 500.0
    pressure = 10.0

    # Call the function
    output = irc_job(
        atoms, freq_job_kwargs={"temperature": temperature, "pressure": pressure}
    )

    # Perform assertions on the result
    assert isinstance(output, dict)

    assert output["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["freq_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)


def test_irc_job_with_custom_opt_params(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Define test inputs
    atoms = molecule("H2O")
    opt_params = {"run_kwargs": {"direction": "reverse"}}

    # Call the function
    output = irc_job(atoms, opt_params=opt_params)

    # Perform assertions on the result
    assert isinstance(output, dict)

    assert output["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["freq_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)


def test_quasi_irc_job_with_default_args(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Define test inputs
    atoms = molecule("H2O")

    # Call the function
    output = quasi_irc_job(atoms)

    # Perform assertions on the result
    assert isinstance(output, dict)

    assert output["irc_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["freq_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)


def test_quasi_irc_job_with_custom_direction(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Define test inputs
    atoms = molecule("H2O")
    direction = "reverse"

    # Call the function
    output = quasi_irc_job(atoms, direction=direction)

    # Perform assertions on the result
    assert isinstance(output, dict)
    assert "irc_job" in output

    assert output["irc_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["irc_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["freq_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)


def test_quasi_irc_job_with_custom_temperature_and_pressure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Define test inputs
    atoms = molecule("H2O")
    temperature = 500.0
    pressure = 10.0

    # Call the function
    output = quasi_irc_job(
        atoms, freq_job_kwargs={"temperature": temperature, "pressure": pressure}
    )

    # Perform assertions on the result
    assert isinstance(output, dict)
    assert "irc_job" in output

    assert output["irc_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["freq_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)


def test_quasi_irc_job_with_custom_irc_swaps(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # Define test inputs
    atoms = molecule("H2O")
    irc_job_kwargs = {"run_kwargs": {"direction": "reverse"}}

    # Call the function
    output = quasi_irc_job(atoms, irc_job_kwargs=irc_job_kwargs)

    # Perform assertions on the result
    assert isinstance(output, dict)
    assert "irc_job" in output

    assert output["irc_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["results"]["energy"] == pytest.approx(-2081.121372886602)
    assert output["freq_job"]["results"]["energy"] == pytest.approx(-2081.121372886602)


@pytest.fixture()
def setup_test_environment(tmp_path):
    reactant = Atoms(
        symbols="CCHHCHH",
        positions=[
            [1.4835950817281542, -1.0145410211301968, -0.13209027203235943],
            [0.8409564131524673, 0.018549610257914483, -0.07338809662321308],
            [-0.6399757891931867, 0.01763740851518944, 0.0581573443268891],
            [-1.0005576455546672, 1.0430257532387608, 0.22197240310602892],
            [1.402180736662139, 0.944112416574632, -0.12179540364365492],
            [-1.1216961389434357, -0.3883639833876232, -0.8769102842015071],
            [-0.9645026578514683, -0.6204201840686793, 0.9240543090678239],
        ],
    )

    product = Atoms(
        symbols="CCHHCHH",
        positions=[
            [1.348003553501624, 0.4819311116778978, 0.2752537177143993],
            [0.2386618286631742, -0.3433222966734429, 0.37705518940917926],
            [-0.9741307940518336, 0.07686022294949588, 0.08710778043683955],
            [-1.8314843503320921, -0.5547344604780035, 0.1639037492534953],
            [0.3801391040059668, -1.3793340533058087, 0.71035902765307],
            [1.9296265384257907, 0.622088341468767, 1.0901733942191298],
            [-1.090815880212625, 1.0965111343610956, -0.23791518420660265],
        ],
    )

    return reactant, product


def test_neb_job(setup_test_environment, tmp_path):
    reactant, product = setup_test_environment

    neb_summary = neb_job(reactant, product)

    assert len(neb_summary["neb_results"]["trajectory_results"]) == 20
    assert neb_summary["relax_reactant"]["atoms"].positions[0, 0] == pytest.approx(
        1.6959156598553338, abs=1e-3
    )
    assert neb_summary["relax_product"]["atoms"].positions[0, 0] == pytest.approx(
        1.117689, abs=1e-3
    )

    assert neb_summary["neb_results"]["trajectory_results"][1][
        "energy"
    ] == pytest.approx(-24.895280838012695, abs=0.01)


def test_geodesic_job(setup_test_environment, tmp_path):
    reactant, product = setup_test_environment
    calc_kwargs = {}

    geodesic_summary = geodesic_job(reactant, product, calc_kwargs=calc_kwargs)
    assert geodesic_summary["highest_e_atoms"].get_potential_energy() == pytest.approx(
        -3157.169858218544, abs=1e-6
    )