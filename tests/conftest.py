# Required for py.test
import os


def pytest_configure():
    os.environ["AAA_LOADER_MANUAL"] = "1"
