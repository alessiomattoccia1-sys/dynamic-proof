# Copyright 2026 Alessio Mattoccia
# SPDX-License-Identifier: Apache-2.0
"""Install or remove the local login service for this Dynamic Proof workspace."""
from argparse import ArgumentParser
import os
from pathlib import Path
import plistlib
import subprocess
import sys


LABEL = "it.dynamiclabs.dynamicproof.public"
ROOT = Path(__file__).resolve().parent.parent
PROGRAM = ROOT / ".venv/bin/python"
STATE = ROOT / "state"
PLIST = Path.home() / "Library/LaunchAgents" / f"{LABEL}.plist"
DOMAIN = f"gui/{os.getuid()}"
SERVICE = f"{DOMAIN}/{LABEL}"


def launch(*args, check=True):
    return subprocess.run(["/bin/launchctl", *args], check=check)


def loaded():
    result = subprocess.run(["/bin/launchctl", "print", SERVICE],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return result.returncode == 0


def verify_owner():
    if PLIST.is_file():
        current = plistlib.loads(PLIST.read_bytes())
        if current.get("WorkingDirectory") != str(ROOT):
            raise RuntimeError("the launchd identifier belongs to a different directory")


def install():
    if not PROGRAM.is_file():
        raise RuntimeError("project Python environment is missing")
    verify_owner()
    STATE.mkdir(mode=0o700, exist_ok=True)
    PLIST.parent.mkdir(mode=0o700, exist_ok=True)
    if loaded():
        launch("bootout", SERVICE)
    content = {"Label": LABEL, "ProgramArguments": [str(PROGRAM), "-m", "dynamic_proof", "serve"],
               "WorkingDirectory": str(ROOT), "RunAtLoad": True, "KeepAlive": True,
               "ThrottleInterval": 15, "Nice": 8,
               "StandardOutPath": str(STATE / "service.log"), "StandardErrorPath": str(STATE / "service-error.log")}
    temp = PLIST.with_suffix(".tmp")
    temp.write_bytes(plistlib.dumps(content))
    temp.chmod(0o600)
    temp.replace(PLIST)
    launch("bootstrap", DOMAIN, str(PLIST))
    launch("print", SERVICE)


def remove():
    verify_owner()
    if loaded():
        launch("bootout", SERVICE)
    PLIST.unlink(missing_ok=True)


def main():
    parser = ArgumentParser()
    parser.add_argument("action", choices=("install", "status", "remove", "restart"))
    action = parser.parse_args().action
    if sys.platform != "darwin":
        parser.error("this service requires macOS launchd")
    if action == "install":
        install()
    elif action == "status":
        launch("print", SERVICE)
    elif action == "remove":
        remove()
    else:
        verify_owner()
        launch("kickstart", "-k", SERVICE)


if __name__ == "__main__":
    main()
