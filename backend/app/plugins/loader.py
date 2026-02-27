"""Plugin loader — scan /plugins/*/manifest.json, validate, and dynamically load."""

import importlib
import importlib.util
import json
import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from app.modules.registry import register_plugin_module

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path("/plugins")

# Loaded plugin metadata (filled at startup)
_loaded_plugins: list[dict[str, Any]] = []

REQUIRED_MANIFEST_FIELDS = {"id", "name", "route", "api_prefix"}


def _validate_manifest(manifest: dict, manifest_path: Path) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors = []
    for field in REQUIRED_MANIFEST_FIELDS:
        if not manifest.get(field):
            errors.append(f"missing required field: {field}")
    if manifest.get("id") and not manifest["id"].replace("-", "").replace("_", "").isalnum():
        errors.append(f"invalid id: {manifest['id']} (alphanumeric, hyphens, underscores only)")
    if manifest.get("api_prefix") and not manifest["api_prefix"].startswith("/api/plugins/"):
        errors.append(f"api_prefix must start with /api/plugins/, got: {manifest['api_prefix']}")
    return errors


def _import_module_from_path(module_name: str, file_path: Path):
    """Import a Python module from an arbitrary filesystem path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


def get_loaded_plugins() -> list[dict[str, Any]]:
    """Return list of loaded plugin metadata (manifest + status)."""
    return _loaded_plugins


async def load_plugins(app: FastAPI) -> None:
    """Scan plugins directory, validate manifests, load routers and models."""
    if not PLUGINS_DIR.is_dir():
        logger.info("[Plugins] plugins directory not found: %s", PLUGINS_DIR)
        return

    _loaded_plugins.clear()

    for plugin_dir in sorted(PLUGINS_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue

        manifest_path = plugin_dir / "manifest.json"
        if not manifest_path.is_file():
            logger.warning("[Plugins] skipping %s — no manifest.json", plugin_dir.name)
            continue

        # Parse manifest
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.error("[Plugins] failed to parse %s: %s", manifest_path, e)
            continue

        # Validate
        errors = _validate_manifest(manifest, manifest_path)
        if errors:
            logger.error("[Plugins] invalid manifest in %s: %s", plugin_dir.name, "; ".join(errors))
            continue

        plugin_id = manifest["id"]
        backend_dir = plugin_dir / "backend"

        # Import models.py if present (must be before router so models are registered)
        models_path = backend_dir / "models.py"
        if models_path.is_file():
            try:
                _import_module_from_path(f"plugin_{plugin_id}_models", models_path)
                logger.info("[Plugins] %s: models loaded", plugin_id)
            except Exception as e:
                logger.error("[Plugins] %s: failed to load models: %s", plugin_id, e)
                continue

        # Import router.py (required)
        router_path = backend_dir / "router.py"
        if not router_path.is_file():
            logger.error("[Plugins] %s: backend/router.py not found", plugin_id)
            continue

        try:
            router_mod = _import_module_from_path(f"plugin_{plugin_id}_router", router_path)
        except Exception as e:
            logger.error("[Plugins] %s: failed to load router: %s", plugin_id, e)
            continue

        # Find the APIRouter instance
        router_obj = getattr(router_mod, "router", None)
        if router_obj is None:
            logger.error("[Plugins] %s: router.py must export 'router' (APIRouter)", plugin_id)
            continue

        # Include the router in the FastAPI app
        app.include_router(router_obj, prefix=manifest["api_prefix"], tags=[f"plugin:{plugin_id}"])
        logger.info("[Plugins] %s: router mounted at %s", plugin_id, manifest["api_prefix"])

        # Register in module registry
        plugin_meta = {
            "id": plugin_id,
            "name": manifest.get("name", plugin_id),
            "name_en": manifest.get("name_en", manifest.get("name", plugin_id)),
            "icon": manifest.get("icon", "puzzle"),
            "route": manifest["route"],
            "api_prefix": manifest["api_prefix"],
            "type": "plugin",
            "requires": manifest.get("requires", []),
            "default_enabled": True,
            "version": manifest.get("version", "0.0.0"),
            "description": manifest.get("description", ""),
            "author": manifest.get("author", ""),
        }
        register_plugin_module(plugin_meta)
        _loaded_plugins.append(plugin_meta)

    logger.info("[Plugins] loaded %d plugin(s)", len(_loaded_plugins))
