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
STEAM_HOME = Path(os.environ.get("STEAM_HOME", str(Path.home())))
ASA_HOME = STEAM_HOME / "asa"
STEAMCMD_HOME = STEAM_HOME / "steamcmd"
WINE_PREFIX = STEAM_HOME / "wineprefix"
ASA_EXE = ASA_HOME / "ShooterGame/Binaries/Win64/ArkAscendedServer.exe"
CONFIG_DIR = ASA_HOME / "ShooterGame/Saved/Config/WindowsServer"

SESSION_NAME = os.environ.get("SESSION_NAME", "MyASA").strip()
SERVER_PASSWORD = os.environ.get("SERVER_PASSWORD", "password").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass").strip()
GAME_PORT = os.environ.get("GAME_PORT", "7777").strip()
QUERY_PORT = os.environ.get("QUERY_PORT", "27015").strip()
RCON_PORT = os.environ.get("RCON_PORT", "27020").strip()
MAP_NAME = os.environ.get("MAP_NAME", "TheIsland_WP").strip()
MAX_PLAYERS = os.environ.get("MAX_PLAYERS", "70").strip()

MOD_IDS = os.environ.get("MOD_IDS", "").strip()
CUSTOM_START_PARAMS = os.environ.get("CUSTOM_START_PARAMS", "").strip()

# Wine environment
os.environ["WINEPREFIX"] = str(WINE_PREFIX)
os.environ["WINEARCH"] = "win64"
os.environ["DISPLAY"] = ":0"

# ----------------------------------------------------------------------
def log(msg: str):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def run_cmd(cmd, check=True, cwd=None):
    log(f"Running: {cmd}")
    process = subprocess.Popen(
        cmd,
        shell=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    for line in process.stdout:
        print(line, end="", flush=True)

    process.wait()
    if check and process.returncode != 0:
        log(f"ERROR: Command failed with return code {process.returncode}")
        sys.exit(process.returncode)

    return process

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
    steamcmd = STEAMCMD_HOME / "steamcmd.sh"
    if not steamcmd.exists():
        log(f"SteamCMD not found at {steamcmd}")
        sys.exit(1)
    cmd = f'"{steamcmd}" +force_install_dir "{ASA_HOME}" +login anonymous +app_update 2430930 validate +quit'
    run_cmd(cmd, check=True)
    if not ASA_EXE.exists():
        log("ERROR: ASA executable not found after installation.")
        sys.exit(1)

def setup_mods():
    """Add mod IDs to GameUserSettings.ini and prepare command-line args."""
    if not MOD_IDS:
        return ""

    # Clean the mod IDs: remove spaces, split by comma
    mod_list = [mod_id.strip() for mod_id in MOD_IDS.split(",") if mod_id.strip()]
    if not mod_list:
        return ""

    # Format the mod list for config and command line
    mods_str = ",".join(mod_list)
    log(f"Setting up mods: {mods_str}")

    # Add ActiveMods to GameUserSettings.ini under [ServerSettings]
    game_user_settings = CONFIG_DIR / "GameUserSettings.ini"
    if not game_user_settings.exists():
        game_user_settings.touch()

    # Use the existing set_ini_value function (or similar) to add/update ActiveMods
    set_ini_value(game_user_settings, "ServerSettings", "ActiveMods", mods_str)

    # Return the command-line argument for the server startup
    return f"-mods={mods_str}"

def ensure_configs():
    """Create default config files if missing, and inject RCON settings."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    game_user_settings = CONFIG_DIR / "GameUserSettings.ini"
    if not game_user_settings.exists():
        game_user_settings.touch()
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

    # Add mod command-line arguments if any mods are configured
    mod_arg = setup_mods()
    if mod_arg:
        cmd.append(mod_arg)

    # Add custom start parameters if any are configured
    if CUSTOM_START_PARAMS:
        # Split by space to handle multiple parameters if provided as a single string
        # though appending as a single string might also work if we use shell=True, 
        # but subprocess.Popen with a list is safer without shell=True.
        # Wait, server.py uses shell=True in run_cmd, but start_asa uses a list without shell=True.
        # So we should split by space.
        cmd.extend(CUSTOM_START_PARAMS.split())

    log(f"Launching server: {' '.join(cmd)}")
    # Start in a new process group so we can kill everything later
    proc = subprocess.Popen(cmd, preexec_fn=os.setsid)
    return proc

def graceful_shutdown(proc):
    log("SIGTERM received – saving world via RCON...")
    rcon_cmd = ["/rcon.sh", "saveworld"]
    try:
        # mcrcon usually waits for the command to complete and returns the server's response.
        # We can capture the output and log it for confirmation.
        result = subprocess.run(rcon_cmd, capture_output=True, text=True, timeout=30, check=False)
        if result.stdout:
            log(f"RCON output: {result.stdout.strip()}")
        log("Save command completed.")
    except Exception as e:
        log(f"RCON save failed: {e}")

    log("Sending SIGINT to server process group...")
    time.sleep(2)
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        log("Server did not exit gracefully, sending SIGKILL...")
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    log("Shutdown complete.")

def main():
    log("Running as steam user – starting server")
    log("Initializing Wine prefix...")
    run_cmd("wineboot --init", check=False)

    if not ASA_EXE.exists():
        install_asa()

    ensure_configs()
    proc = start_asa()

    # Register graceful shutdown
    def handler(signum, frame):
        graceful_shutdown(proc)
        sys.exit(0)
    signal.signal(signal.SIGTERM, handler)

    # Wait for exit
    try:
        proc.wait()
    except KeyboardInterrupt:
        graceful_shutdown(proc)
    log("Server exited.")

if __name__ == "__main__":
    main()