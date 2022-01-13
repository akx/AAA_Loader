import inspect
import os
import sys
from collections import defaultdict, namedtuple
from importlib import import_module
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from importlib.util import spec_from_loader
from types import ModuleType
from typing import Dict, List, Optional, Iterable

__version__ = "0.1"
HELLO_MY_NAME_IS = "Loader"
MODS_FLAG = "loadmods"

Mod = namedtuple("Mod", "name path module_path")


# Readonly list type for stopping duplicate mod list entries in crashlogs
class ReadOnlyList(list):  # type: ignore[type-arg]
    def append(*args, **kwargs):  # type: ignore[no-untyped-def]
        pass


class AssetLoader:
    def __init__(self, path: str) -> None:
        self.base_path = path

    def get_asset(self, path: List[str]) -> List[str]:
        assert path
        assert isinstance(path, list)
        assert isinstance(path[0], str)

        desired_path = os.path.join(self.base_path, *path)
        relative_path = os.path.relpath(desired_path, os.path.abspath("rl_data"))

        return relative_path.split(os.sep)


class ConstantImporter(MetaPathFinder, Loader):
    def __init__(self, fullname: str, module: ModuleType):
        self.fullname = fullname
        self.module = module

    def find_spec(cls, fullname: str, path=None, target=None) -> Optional[ModuleSpec]:  # type: ignore[no-untyped-def]
        if fullname == cls.fullname:
            return spec_from_loader(fullname, cls, origin=cls.fullname)
        return None

    def create_module(cls, spec: ModuleSpec) -> ModuleType:
        return cls.module

    def exec_module(cls, module=None):  # type: ignore[no-untyped-def]
        pass

    def get_code(cls, fullname):  # type: ignore[no-untyped-def]
        return None

    def get_source(cls, fullname):  # type: ignore[no-untyped-def]
        return None

    def is_package(cls, fullname):  # type: ignore[no-untyped-def]
        return False


# This is a fix for the inability to import RiftWizard directly without using a stack inspection.

stack = inspect.stack()

frm = stack[-1]
RiftWizard = inspect.getmodule(frm[0])
frm = stack[0]
AAA_Loader = inspect.getmodule(frm[0])

if RiftWizard:
    sys.meta_path.insert(0, ConstantImporter("RiftWizard", RiftWizard))
if AAA_Loader:
    sys.meta_path.insert(0, ConstantImporter("mods.AAA_Loader.AAA_Loader", AAA_Loader))


def discover_mods(mods_path: str) -> Iterable[Mod]:
    for name in os.listdir(mods_path):
        base_path = os.path.join(mods_path, name)
        if not os.path.isfile(os.path.join(base_path, f"{name}.py")):
            continue
        yield Mod(name=name, path=base_path, module_path=f"mods.{name}.{name}")


def ensure_module_package_on_path(mod: Mod) -> None:
    """
    Ensure the parent directory of the mod's `path` (which is `mods/X`) is on sys.path.
    """

    pkg_path = os.path.normpath(os.path.dirname(mod.path))
    if pkg_path not in sys.path:
        sys.path.append(pkg_path)


class ModLoader:
    # TODO: Would be good to have a late loading functionality that runs with a customized negotiated order
    def __init__(self) -> None:
        # List of all discovered mods
        self.all_mods: List[Mod] = []
        # Lookup from module name -> path for loaded mods
        self.imported_mods: Dict[str, Mod] = {}

    def is_mod_active(self, modname: str) -> bool:
        return modname in self.imported_mods

    def get_asset_loader(self, modname: str) -> AssetLoader:
        return AssetLoader(self.imported_mods[modname].path)

    def discover_mods_in_path(self, path: str) -> None:
        print(f"Checking mod path: {path}")
        for package in os.listdir(path):
            pkg_path = os.path.join(path, package)
            print(f"Checking {pkg_path} for mods...")
            mods_path = os.path.join(pkg_path, "mods")

            if not os.path.isdir(mods_path):
                print(f"{mods_path} is not a valid directory, skipping")
                continue

            for mod in discover_mods(mods_path):
                print(f"Found {mod.name} ({mod.path})")
                self.all_mods.append(mod)

    def discover_base_mods(self) -> None:
        print("Checking base game mod folder for mods...")
        for mod in discover_mods("mods"):
            print(f"Found {mod.name} ({mod.path})")
            self.all_mods.append(mod)

    def complain_about_duplicates(self) -> None:
        check_set = defaultdict(list)
        for mod in self.all_mods:
            check_set[mod.module_path].append(mod)
        for key, group in check_set.items():
            if len(group) > 1:
                print(
                    f"WARNING: Found duplicate module path {key} ({len(group)} duplicates). Only one will be loaded."
                )
        # We could also just crash at this point.

    def import_mod(self, mod: Mod) -> None:
        print(f"Loading {mod.name} ({mod.path})")
        module = sys.modules.get(mod.module_path)
        if module:
            print(f"Module with name {mod.module_path} already loaded: {module}")
            return
        ensure_module_package_on_path(mod)
        import_module(mod.module_path)
        self.imported_mods[mod.name] = mod

    def import_all_mods(self) -> None:
        for mod in self.all_mods:
            self.import_mod(mod)


def main() -> None:
    print(f"Starting up {HELLO_MY_NAME_IS}")
    loader = ModLoader()
    loader.discover_base_mods()
    if MODS_FLAG in sys.argv:
        mods_path = sys.argv[sys.argv.index(MODS_FLAG) + 1]
        loader.discover_mods_in_path(mods_path)
    loader.complain_about_duplicates()
    loader.import_all_mods()
    print(f"{HELLO_MY_NAME_IS} Loaded")
    if RiftWizard:
        RiftWizard.loaded_mods = ReadOnlyList(list(loader.imported_mods))  # type: ignore[attr-defined]
    else:
        print("Warning: could not set RiftWizard.loaded_mods")


main()  # TODO: does this need to be guarded with the usual `if main` stanza?
