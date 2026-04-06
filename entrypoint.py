#!/usr/bin/env python3
import os
import subprocess
import signal
import sys
import time
from pathlib import Path

# ----------------------------------------------------------------------
# Configuration (read from environment)
# ----------------------------------------------------------------------
STEAM_HOME = Path(os.environ.get("STEAM_HOME", "/home/steam"))
ASA_HOME = STEAM_HOME / "asa"
STEAMCMD_HOME = STEAM_HOME / "steamcmd"
WINE_PREFIX = STEAM_HOME / "wineprefix"
ASA_EXE = ASA_HOME / "ShooterGame/Binaries/Win64/ArkAscendedServer.exe"
CONFIG_DIR = ASA_HOME / "ShooterGame/Saved/Config/WindowsServer"

SESSION_NAME = os.environ.get("SESSION_NAME", "MyASA")
SERVER_PASSWORD = os.environ.get("SERVER_PASSWORD", "password")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")
GAME_PORT = os.environ.get("GAME_PORT", "7777")
QUERY_PORT = os.environ.get("QUERY_PORT", "27015")
RCON_PORT = os.environ.get("RCON_PORT", "27020")
MAP_NAME = os.environ.get("MAP_NAME", "TheIsland_WP")
MAX_PLAYERS = os.environ.get("MAX_PLAYERS", "70")

# Paths
os.environ["WINEPREFIX"] = str(WINE_PREFIX)
os.environ["WINEARCH"] = "win64"
os.environ["DISPLAY"] = ":0"

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def log(msg: str):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def run_cmd(cmd, check=True, cwd=None):
    log(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        log(f"ERROR: {result.stderr}")
        sys.exit(result.returncode)
    return result

def set_ini_value(file_path: Path, section: str, key: str, value: str):
    """Ensure the key exists under the given section, replacing if present."""
    if not file_path.exists():
        file_path.touch()
    lines = file_path.read_text().splitlines()
    section_header = f"[{section}]"
    in_section = False
    key_found = False
    new_lines = []
    for line in lines:
        if line.strip() == section_header:
            in_section = True
            new_lines.append(line)
            continue
        if in_section and line.startswith("["):
            in_section = False
        if in_section and line.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            key_found = True
            continue
        new_lines.append(line)
    if not key_found:
        # Add after section header, or create section at end
        for i, line in enumerate(new_lines):
            if line.strip() == section_header:
                new_lines.insert(i+1, f"{key}={value}")
                break
        else:
            new_lines.append(section_header)
            new_lines.append(f"{key}={value}")
    file_path.write_text("\n".join(new_lines))

def install_asa():
    log("Installing ASA via SteamCMD...")
    cmd = f'"{STEAMCMD_HOME}/steamcmd.sh" +force_install_dir "{ASA_HOME}" +login anonymous +app_update 2430930 validate +quit'
    run_cmd(cmd, check=True)
    if not ASA_EXE.exists():
        log("ERROR: ASA executable not found after installation.")
        sys.exit(1)

def ensure_configs():
    """Create default config files if missing, and inject RCON settings."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    game_user_settings = CONFIG_DIR / "GameUserSettings.ini"
    if not game_user_settings.exists():
        game_user_settings.touch()
    # Ensure [ServerSettings] section exists and RCON values are set
    set_ini_value(game_user_settings, "ServerSettings", "RCONEnabled", "True")
    set_ini_value(game_user_settings, "ServerSettings", "RCONPort", RCON_PORT)
    set_ini_value(game_user_settings, "ServerSettings", "ServerAdminPassword", ADMIN_PASSWORD)
    log("RCON settings applied.")

def start_asa():
    """Launch ASA via wine and return the subprocess Popen object."""
    main_args = (
        f"{MAP_NAME}?SessionName={SESSION_NAME}?"
        f"ServerPassword={SERVER_PASSWORD}?"
        f"ServerAdminPassword={ADMIN_PASSWORD}"
    )
    cmd = [
        "wine", str(ASA_EXE),
        main_args,
        f"-Port={GAME_PORT}",
        f"-QueryPort={QUERY_PORT}",
        f"-RCONPort={RCON_PORT}",
        f"-WinLiveMaxPlayers={MAX_PLAYERS}"
    ]
    log(f"Launching server: {' '.join(cmd)}")
    # Use subprocess.Popen with process group so we can send signals properly
    proc = subprocess.Popen(cmd, preexec_fn=os.setsid)
    return proc

def graceful_shutdown(proc):
    log("SIGTERM received – saving world via RCON...")
    # Give the server a moment to be ready (adjust if needed)
    time.sleep(2)
    # Use mcrcon to send saveworld
    rcon_cmd = [
        "/usr/local/bin/mcrcon",
        "-H", "localhost",
        "-P", RCON_PORT,
        "-p", ADMIN_PASSWORD,
        "saveworld"
    ]
    try:
        subprocess.run(rcon_cmd, timeout=10, check=False)
        log("Save command sent.")
    except Exception as e:
        log(f"RCON save failed (server may be unresponsive): {e}")
    log("Waiting 10 seconds for save to complete...")
    time.sleep(10)
    log("Sending SIGINT to the server process...")
    os.killpg(os.getpgid(proc.pid), signal.SIGINT)
    proc.wait(timeout=30)
    log("Shutdown complete.")

def main():
    # 1. Prepare Wine prefix
    log("Initializing Wine prefix...")
    run_cmd("wineboot --init", check=False)

    # 2. Install ASA if missing
    if not ASA_EXE.exists():
        install_asa()

    # 3. Ensure config files exist and RCON is enabled
    ensure_configs()

    # 4. Start the server
    proc = start_asa()

    # 5. Register signal handler for SIGTERM (docker stop)
    def handler(signum, frame):
        graceful_shutdown(proc)
        sys.exit(0)
    signal.signal(signal.SIGTERM, handler)

    # 6. Wait for the process to finish naturally
    try:
        proc.wait()
    except KeyboardInterrupt:
        graceful_shutdown(proc)
    log("Server exited.")

if __name__ == "__main__":
    main()