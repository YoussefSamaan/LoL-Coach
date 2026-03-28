import importlib.util
from pathlib import Path


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_core_package_shim_sets_src_path():
    repo_root = Path(__file__).resolve().parents[1]
    module = _load_module("test_core_package_shim", repo_root / "core" / "__init__.py")

    assert module.__path__ == [str(repo_root / "core" / "src" / "core")]


def test_ml_package_shim_sets_src_path():
    repo_root = Path(__file__).resolve().parents[1]
    module = _load_module("test_ml_package_shim", repo_root / "ml" / "__init__.py")

    assert module.__path__ == [str(repo_root / "ml" / "src" / "ml")]


def test_backend_package_shim_sets_src_path():
    repo_root = Path(__file__).resolve().parents[1]
    module = _load_module(
        "test_backend_package_shim", repo_root / "backend" / "__init__.py"
    )

    assert module.__path__ == [str(repo_root / "backend" / "src" / "backend")]
