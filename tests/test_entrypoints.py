"""Ensure Vercel/ASGI entry modules export FastAPI app."""


def test_main_exports_app():
    import main

    assert hasattr(main, "app")
    assert main.app.title


def test_app_py_exports_app():
    import importlib

    mod = importlib.import_module("app")
    assert hasattr(mod, "app")


def test_api_index_exports_app():
    from api.index import app

    assert app is not None
