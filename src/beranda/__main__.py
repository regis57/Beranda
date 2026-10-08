"""`beranda` command line entry point."""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from pathlib import Path

import uvicorn

from . import __version__, config
from .app import create_app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="beranda", description="Smart mirror dashboard server")
    parser.add_argument("--config", type=Path, help="path to config.toml")
    parser.add_argument("--demo", action="store_true", help="show invented weather and agenda")
    parser.add_argument("--host", help="address to listen on (default from config)")
    parser.add_argument("--port", type=int, help="port to listen on (default from config)")
    parser.add_argument("--version", action="version", version=f"beranda {__version__}")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = config.load(args.config)
    overrides = {}
    if args.demo:
        overrides["demo"] = True
    if args.host:
        overrides["host"] = args.host
    if args.port:
        overrides["port"] = args.port
    if overrides:
        cfg = replace(cfg, **overrides)

    uvicorn.run(create_app(cfg), host=cfg.host, port=cfg.port, log_level="info")


if __name__ == "__main__":
    main()
