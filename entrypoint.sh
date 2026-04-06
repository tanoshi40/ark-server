#!/bin/bash
set -e

STEAM_HOME=${STEAM_HOME:-/home/steam}
ASA_HOME="$STEAM_HOME/asa"
ASA_EXE="$ASA_HOME/ShooterGame/Binaries/Win64/ArkAscendedServer.exe"
CONFIG_DIR="$ASA_HOME/ShooterGame/Saved/Config/WindowsServer"
DEFAULT_CONFIG_DIR="$ASA_HOME/default_config"

SESSION_NAME=${SESSION_NAME:-MyASA}
SERVER_PASSWORD=${SERVER_PASSWORD:-password}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-adminpass}
GAME_PORT=${GAME_PORT:-7777}
QUERY_PORT=${QUERY_PORT:-27015}
RCON_PORT=${RCON_PORT:-27020}
MAP_NAME=${MAP_NAME:-TheIsland_WP}

# Function to cleanly shut down the server
graceful_shutdown() {
    echo "[INFO] SIGTERM received – saving world via RCON..."
    sleep 2
    if /usr/local/bin/mcrcon -H localhost -P "$RCON_PORT" -p "$ADMIN_PASSWORD" "saveworld"; then
        echo "[INFO] Save command sent successfully."
    else
        echo "[WARN] RCON save failed – server may be unresponsive."
    fi
    echo "[INFO] Waiting 10 seconds for save to complete..."
    sleep 10
    echo "[INFO] Sending SIGINT to the server process..."
    kill -INT "$ASA_PID" 2>/dev/null || true
    sleep 10
    echo "[INFO] Shutdown complete."
    exit 0
}

# Function to set or add a key under [ServerSettings]
CONFIG_FILE="$CONFIG_DIR/GameUserSettings.ini"
set_ini_value() {
    local file="$1"
    local section="$2"
    local key="$3"
    local value="$4"
    if ! grep -q "^${key}=" "$file"; then
        # Key doesn't exist – add it under the section
        sed -i "/^\[${section}\]/a ${key}=${value}" "$file"
    else
        # Key exists – replace it
        sed -i "s/^${key}=.*/${key}=${value}/" "$file"
    fi
}

mkdir -p "$ASA_HOME" "$CONFIG_DIR" "$WINE_PREFIX"
chown steam:steam -R $STEAM_HOME

# ----------------------------------------
# 1. Install ASA if missing
# ----------------------------------------
if [ ! -f "$ASA_EXE" ]; then
    echo "[INFO] Installing ASA..."
    su - steam -c "\"$STEAMCMD_HOME/steamcmd.sh\" +force_install_dir \"$ASA_HOME\" +login anonymous +app_update 2430930 validate +quit"
    if [ ! -f "$ASA_EXE" ]; then
        echo "[ERROR] Installation failed"
        exit 1
    fi
fi

# ----------------------------------------
# 2. Initialise Wine prefix (as steam user)
# ----------------------------------------
echo "[INFO] Initialising Wine prefix (may take a moment)..."
su - steam -c "wineboot --init" 2>/dev/null || true

# ----------------------------------------
# 3. Copy default configs if missing
# ----------------------------------------
for file in Game.ini GameUserSettings.ini; do
    if [ ! -f "$CONFIG_DIR/$file" ]; then
        if [ -f "$DEFAULT_CONFIG_DIR/$file" ]; then
            cp "$DEFAULT_CONFIG_DIR/$file" "$CONFIG_DIR/$file"
        else
            touch "$CONFIG_DIR/$file"
        fi
    fi
done

# Ensure the [ServerSettings] section exists
if ! grep -q "^\[ServerSettings\]" "$CONFIG_FILE"; then
    echo >> "$CONFIG_FILE"
    echo "[ServerSettings]" >> "$CONFIG_FILE"
fi

# Set the required RCON values
set_ini_value "$CONFIG_FILE" "ServerSettings" "RCONEnabled" "True"
set_ini_value "$CONFIG_FILE" "ServerSettings" "RCONPort" "$RCON_PORT"
set_ini_value "$CONFIG_FILE" "ServerSettings" "ServerAdminPassword" "$ADMIN_PASSWORD"

echo "[INFO] RCON settings written to $CONFIG_FILE"

# ----------------------------------------
# 4. Launch ASA via Wine with virtual X11
# ----------------------------------------
# Register graceful_shutdown hook
trap graceful_shutdown SIGTERM

RUN_ASA_SCRIPT="$STEAM_HOME/run_asa.sh"
echo "[INFO] Launching ASA with Wine..."
# Make sure wrapper exists and is executable
if [ ! -x "$RUN_ASA_SCRIPT" ]; then
    echo "[ERROR] Wrapper script not found or not executable"
    chmod +x "$RUN_ASA_SCRIPT"
fi

# Run the wrapper as steam user in the background
su - steam -c "$RUN_ASA_SCRIPT \
    \"$MAP_NAME\" \
    \"$SESSION_NAME\" \
    \"$SERVER_PASSWORD\" \
    \"$ADMIN_PASSWORD\" \
    \"$GAME_PORT\" \
    \"$QUERY_PORT\" \
    \"$RCON_PORT\"" &
ASA_PID=$!


# Wait for server process
wait "$ASA_PID"

