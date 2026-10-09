"""`beranda` command line entry point."""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

import uvicorn

from . import __version__, config, system
from .admin import write_config
from .app import create_app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="beranda", description="Smart mirror dashboard server")
    parser.add_argument("command", nargs="?", choices=["serve", "doctor"], default="serve",
                        help="serve (default) or doctor: check the installation")
    parser.add_argument("--config", type=Path, help="path to config.toml")
    parser.add_argument("--demo", action="store_true", help="show invented weather and agenda")
    parser.add_argument("--host", help="address to listen on (default from config)")
    parser.add_argument("--port", type=int, help="port to listen on (default from config)")
    parser.add_argument("--version", action="version", version=f"beranda {__version__}")
    args = parser.parse_args(argv)

    if args.command == "doctor":
        from .doctor import run

        raise SystemExit(run())

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config_path = args.config or config.find_config_path() or config.DEFAULT_CONFIG_PATH
    cfg = config.load(config_path if config_path.is_file() else None)
    overrides = {}
    if args.demo:
        overrides["demo"] = True
    if args.host:
        overrides["host"] = args.host
    if args.port:
        overrides["port"] = args.port
    if overrides:
        cfg = replace(cfg, **overrides)

    if not args.port and cfg.port != system.DEFAULT_PORT and not system.port_is_free(cfg.host, cfg.port):
        # The port chosen in the settings page is taken by something else: go back to the usual
        # one (and remember it, the full-screen display reads it too) rather than never starting.
        logging.getLogger("beranda").error(
            "port %s is already in use, going back to %s", cfg.port, system.DEFAULT_PORT
        )
        cfg = replace(cfg, port=system.DEFAULT_PORT)
        try:
            write_config(config_path, cfg)
        except OSError:
            pass

    uvicorn.run(create_app(cfg, config_path=config_path), host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
