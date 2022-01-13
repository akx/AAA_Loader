import importlib
import inspect
import logging
import os.path

import AAA_Loader

tests_dir = os.path.dirname(__file__)
root1 = os.path.join(tests_dir, "root1")
root2 = os.path.join(tests_dir, "root2")


def test_patch_imports():
    AAA_Loader.patch_imports(inspect.stack())
    assert importlib.import_module("RiftWizard")


def test_loader(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    monkeypatch.chdir(root1)
    ldr = AAA_Loader.main([AAA_Loader.MODS_FLAG, root2])
    # Check we got both mods we wanted
    assert len(ldr.imported_mods) == 2

    # Check we got a warning about Johannes
    assert any(
        "duplicate module path mods.johannes.johannes" in r.message
        for r in caplog.records
    )
