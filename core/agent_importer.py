import importlib
import pkgutil
import pathlib

def import_all_agents():
    package_name = "agent"
    package_path = pathlib.Path(package_name)

    for module_info in pkgutil.iter_modules([str(package_path)]):
        module_name = module_info.name
        full_name = f"{package_name}.{module_name}"

        print(f"Importing {full_name}")
        importlib.import_module(full_name)
