import importlib
import pkgutil
import pathlib
import os
from core.logger import log


def import_agents():
    """ Importa dinamicamente todos os agentes na pasta 'agent/' """
    package_name = "agent"
    package_path = pathlib.Path(package_name)

    if not package_path.exists():
        log().print(f"Warning: Agents directory '{package_name}' not found.")
        return

    for module_info in pkgutil.iter_modules([str(package_path)]):
        module_name = module_info.name
        # Ignora ficheiros __init__ ou ficheiros de sistema
        if module_name.startswith("__"):
            continue

        full_name = f"{package_name}.{module_name}"

        log().vprint(f"Importing agent module: {full_name}")
        try:
            importlib.import_module(full_name)
        except Exception as e:
            log().print(f"Failed to import {full_name}: {e}")


def import_sensor_handlers():
    """
    Importa explicitamente o ficheiro request_handler.py para ativar os registos.
    """
    try:
        import component.sensor.request_handler

        log().vprint("Sensor handlers imported successfully from 'component.sensor.request_handler'")

    except ImportError as e:
        log().print(f"CRITICAL: Could not import sensor handlers: {e}")