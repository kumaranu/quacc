import os
import shlex
import subprocess
import yaml
import logging
from pathlib import Path
from custodian import Custodian
from custodian.vasp.handlers import (
    FrozenJobErrorHandler,
    IncorrectSmearingHandler,
    LargeSigmaHandler,
    MeshSymmetryErrorHandler,
    NonConvergingErrorHandler,
    PositiveEnergyErrorHandler,
    PotimErrorHandler,
    ScanMetalHandler,
    StdErrHandler,
    UnconvergedErrorHandler,
    VaspErrorHandler,
    WalltimeHandler,
)
from custodian.vasp.jobs import VaspJob
from custodian.vasp.validators import VaspFilesValidator, VasprunXMLValidator

# Adapted from https://github.com/materialsproject/atomate2/blob/main/src/atomate2/vasp/run.py

FILE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)

# Read in default settings
if "VASP_CUSTODIAN_SETTINGS" in os.environ:
    settings_path = os.environ["VASP_CUSTODIAN_SETTINGS"]
else:
    raise EnvironmentError("Missing environment variable VASP_CUSTODIAN_SETTINGS.")
config = yaml.safe_load(open(settings_path))

# If $ is the first character, get from the environment variable
for k, v in config.items():
    if isinstance(v, str) and v[0] == "$":
        if v[1:] in os.environ:
            config[k] = os.environ[v[1:]]
        else:
            raise EnvironmentError(f"Missing environment variable {v[1:]}")

# Handlers for VASP
handlers = []
handlers_dict = {
    "VaspErrorHandler": VaspErrorHandler(vtst_fixes=config["vtst_swaps"]),
    "FrozenJobErrorHandler": FrozenJobErrorHandler(),
    "IncorrectSmearingHandler": IncorrectSmearingHandler(),
    "LargeSigmaHandler": LargeSigmaHandler(),
    "MeshSymmetryErrorHandler": MeshSymmetryErrorHandler(),
    "NonConvergingErrorHandler": NonConvergingErrorHandler(),
    "PositiveEnergyErrorHandler": PositiveEnergyErrorHandler(),
    "PotimErrorHandler": PotimErrorHandler(),
    "StdErrHandler": StdErrHandler(),
    "UnconvergedErrorHandler": UnconvergedErrorHandler(),
    "WalltimeHandler": WalltimeHandler(),
    "ScanMetalHandler": ScanMetalHandler(),
}
validators_dict = {
    "VaspFilesValidator": VaspFilesValidator(),
    "VasprunXMLValidator": VasprunXMLValidator(),
}

handlers = []
for handler_flag in config["handlers"]:
    if handler_flag not in handlers_dict.keys():
        raise ValueError(f"Unknown VASP error handler: {handler_flag}")
    handlers.append(handlers_dict[handler_flag])

validators = []
for validator_flag in config["validators"]:
    if validator_flag not in validators_dict.keys():
        raise ValueError(f"Unknown VASP validator: {validator_flag}")
    validators.append(validators_dict[validator_flag])

# Populate settings
custodian_enabled = config.get("custodian_enabled", True)
parallel_cmd = config.get("vasp_parallel_cmd", "") + " "
vasp_cmd = parallel_cmd + config.get("vasp_cmd", "vasp_std")
vasp_gamma_cmd = parallel_cmd + config.get("vasp_gamma_cmd", "vasp_gam")
max_errors = config.get("max_errors", 5)
wall_time = config.get("custodian_wall_time", None)
scratch_dir = config.get("scratch_dir", None)
vasp_job_kwargs = config.get("vasp_job_kwargs", None)
custodian_kwargs = config.get("custodian_kwargs", None)
vasp_job_kwargs["auto_npar"] = False

# Run VASP
vasp_job_kwargs = {} if vasp_job_kwargs is None else vasp_job_kwargs
custodian_kwargs = {} if custodian_kwargs is None else custodian_kwargs
vasp_cmd = os.path.expandvars(vasp_cmd)
vasp_gamma_cmd = os.path.expandvars(vasp_gamma_cmd)
split_vasp_cmd = shlex.split(vasp_cmd)
split_vasp_gamma_cmd = shlex.split(vasp_gamma_cmd)

if "auto_npar" not in vasp_job_kwargs:
    vasp_job_kwargs["auto_npar"] = False

vasp_job_kwargs.update({"gamma_vasp_cmd": split_vasp_gamma_cmd})

if custodian_enabled:

    # Run with Custodian
    jobs = [VaspJob(split_vasp_cmd, **vasp_job_kwargs)]

    if wall_time is not None:
        handlers = list(handlers) + [WalltimeHandler(wall_time=wall_time)]

    c = Custodian(
        handlers,
        jobs,
        validators=validators,
        max_errors=max_errors,
        scratch_dir=scratch_dir,
        **custodian_kwargs,
    )

    logger.info("Running VASP using custodian.")
    c.run()

else:

    # Run VASP without custodian
    logger.info(f"Running command: {vasp_cmd}")
    return_code = subprocess.call(vasp_cmd, shell=True)
    logger.info(f"{vasp_cmd} finished running with returncode: {return_code}")
