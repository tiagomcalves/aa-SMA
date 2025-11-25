import importlib
import pkgutil
import pathlib
from core.logger import log

def import_agents():
    package_name = "agent"
    package_path = pathlib.Path(package_name)

    for module_info in pkgutil.iter_modules([str(package_path)]):
        module_name = module_info.name
        full_name = f"{package_name}.{module_name}"

        log().vprint(f"Importing {full_name}")
        importlib.import_module(full_name)

def import_sensor_handlers():
    package_name = "component.sensor.request_handler"
    package_path = pathlib.Path(package_name)

    for module_info in pkgutil.iter_modules([str(package_path)]):
        module_name = module_info.name
        full_name = f"{package_name}.{module_name}"

        print(f"Importing {full_name}")
        importlib.import_module(full_name)
