#!/usr/bin/env python3
import subprocess
import sys
import argparse
import os
from pathlib import Path
from datetime import datetime

COMPOSE_FILE = "docker-compose.yml"
PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
BACKUP_DIR = PROJECT_DIR / "backups"

def run_compose(*args):
    cmd = ["docker-compose", "-f", COMPOSE_FILE] + list(args)
    subprocess.run(cmd, check=True)

def cmd_start(args):
    run_compose("up", "-d")

def cmd_stop(args):
    run_compose("down")

def cmd_update(args):
    # Stop, run SteamCMD update, leave stopped
    cmd_stop(args)
    
    # We use a similar logic as in server.py to see real-time output
    # The volumes should match what is in docker-compose.yml
    cmd = [
        "docker-compose", "-f", COMPOSE_FILE, "run", "--rm", "asa",
        "/home/steam/steamcmd/steamcmd.sh",
        "+force_install_dir", "/home/steam/asa",
        "+login", "anonymous",
        "+app_update", "2430930", "validate",
        "+quit"
    ]
    print(f"Running update: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("Update finished. Server is stopped. Use 'start' to relaunch.")

def cmd_backup(args):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"asa_{timestamp}.tar.gz"
    BACKUP_DIR.mkdir(exist_ok=True)
    subprocess.run([
        "tar", "-czf", str(backup_file),
        "-C", str(PROJECT_DIR),
        "data/saves", "data/config"
    ], check=True)
    print(f"Backup created: {backup_file}")

def cmd_rcon(args):
    # Use docker exec to call mcrcon inside the container
    rcon_port = os.environ.get("RCON_PORT", "27020")
    admin_password = os.environ.get("ADMIN_PASSWORD", "adminpass")

    cmd = [
        "docker", "exec", "-i", "asa-server",
        "mcrcon", "-H", "localhost", "-P", rcon_port,
        "-p", admin_password, args.command
    ]
    subprocess.run(cmd)

def main():
    parser = argparse.ArgumentParser(description="ASA Server Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start", help="Start the server")
    subparsers.add_parser("stop", help="Stop the server")
    subparsers.add_parser("update", help="Update server (stops first, leaves stopped)")
    subparsers.add_parser("backup", help="Backup saves and config")
    rcon_parser = subparsers.add_parser("rcon", help="Send RCON command")
    rcon_parser.add_argument("command", help="RCON command (e.g., 'saveworld')")

    args = parser.parse_args()
    if args.command == "start":
        cmd_start(args)
    elif args.command == "stop":
        cmd_stop(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "backup":
        cmd_backup(args)
    elif args.command == "rcon":
        cmd_rcon(args)

if __name__ == "__main__":
    main()