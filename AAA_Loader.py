import inspect
import os
import sys
from collections import defaultdict, namedtuple
from importlib import import_module
from importlib.abc import Loader, MetaPathFinder
from importlib.util import spec_from_loader
from types import ModuleType
from typing import Dict, List

HELLO_MY_NAME_IS = "Loader"
MODS_FLAG = "loadmods"

Mod = namedtuple("Mod", "name path module_path")


# Readonly list type for stopping duplicate mod list entries in crashlogs
class ReadOnlyList(list):
    def append(*args, **kwargs):
        pass


class AssetLoader:
    def __init__(self, path):
        self.base_path = path

    def get_asset(self, path):
        assert path
        assert isinstance(path, list)
        assert isinstance(path[0], str)

        desired_path = os.path.join(self.base_path, *path)
        relative_path = os.path.relpath(desired_path, os.path.abspath("rl_data"))

        return relative_path.split(os.sep)


# This is a fix for the inability to import RiftWizard directly without using a stack inspection.

stack = inspect.stack()

frm = stack[-1]
RiftWizard = inspect.getmodule(frm[0])
frm = stack[0]
AAA_Loader = inspect.getmodule(frm[0])


class ConstantImporter(MetaPathFinder, Loader):
    def __init__(self, fullname, module):
        self.fullname = fullname
        self.module = module

    def find_spec(cls, fullname, path=None, target=None):
        if fullname == cls.fullname:
            spec = spec_from_loader(fullname, cls, origin=cls.fullname)
            return spec
        return None

    def create_module(cls, spec):
        return cls.module

    def exec_module(cls, module=None):
        pass

    def get_code(cls, fullname):
        return None

    def get_source(cls, fullname):
        return None

    def is_package(cls, fullname):
        return False


sys.meta_path.insert(0, ConstantImporter("RiftWizard", RiftWizard))
sys.meta_path.insert(0, ConstantImporter("mods.AAA_Loader.AAA_Loader", AAA_Loader))


def discover_mods(mods_path):
    for f in os.listdir(mods_path):
        if not os.path.isdir(os.path.join(mods_path, f)):
            continue

        if not os.path.exists(os.path.join(mods_path, f, f + ".py")):
            continue

        yield Mod(f, os.path.join(mods_path, f), ".".join(["mods", f, f]))


class ModLoader:
    # TODO: Would be good to have a late loading functionality that runs with a customized negotiated order
    def __init__(self):
        # List of all discovered mods
        self.all_mods: List[Mod] = []
        # Lookup from module name -> path for loaded mods
        self.imported_mods: Dict[str, Mod] = {}

    def is_mod_active(self, modname: str):
        return modname in self.imported_mods

    def get_asset_loader(self, modname):
        return AssetLoader(self.imported_mods[modname].path)

    def discover_mods_in_path(self, path):
        print(f"Checking mod path: {path}")
        for package in os.listdir(path):
            print(f"Checking {package} for mods...")

            mods_path = os.path.join(path, package, "mods")

            if not os.path.isdir(mods_path):
                print(f"{mods_path} is not a valid directory, skipping")
                continue

            sys.path.append(os.path.join(path, package))  # TODO: maybe deduplicate?

            for mod in discover_mods(mods_path):
                print(f"Found {mod.name} ({mod.path})")
                self.all_mods.append(mod)

    def discover_base_mods(self):
        print("Checking base game mod folder for mods...")
        for mod in discover_mods("mods"):
            print(f"Found {mod.name} ({mod.path})")
            self.all_mods.append(mod)

    def complain_about_duplicates(self):
        check_set = defaultdict(list)
        for mod in self.all_mods:
            check_set[mod.module_path].append(mod)
        for key, group in check_set.items():
            if len(group) > 1:
                print(
                    f"WARNING: Found duplicate module path {key} ({len(group)} duplicates). Only one will be loaded."
                )
        # We could also just crash at this point.

    def import_mod(self, mod: Mod) -> ModuleType:
        print(f"Loading {mod.name} ({mod.path})")
        self.imported_mods[mod.name] = mod
        module = sys.modules.get(mod.module_path)
        if module:
            print("Already loaded, not reloading")
            return module
        return import_module(mod.module_path)

    def import_all_mods(self):
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
    RiftWizard.loaded_mods = ReadOnlyList(list(loader.imported_mods))
    print(f"{HELLO_MY_NAME_IS} Loaded")


main()  # TODO: does this need to be guarded with the usual `if main` stanza?
