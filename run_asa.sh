#!/bin/bash
ASA_EXE="/home/steam/asa/ShooterGame/Binaries/Win64/ArkAscendedServer.exe"

MAP_NAME="$1"
SESSION_NAME="$2"
SERVER_PASSWORD="$3"
ADMIN_PASSWORD="$4"
GAME_PORT="$5"
QUERY_PORT="$6"
RCON_PORT="$7"
MAX_PLAYERS="${8:-70}"

# Main ?-separated arguments (no RCONEnabled, no ports)
MAIN_ARGS="${MAP_NAME}?SessionName=${SESSION_NAME}?ServerPassword=${SERVER_PASSWORD}?ServerAdminPassword=${ADMIN_PASSWORD}"

exec wine "$ASA_EXE" "$MAIN_ARGS" \
    -Port="$GAME_PORT" \
    -QueryPort="$QUERY_PORT" \
    -RCONPort="$RCON_PORT" \
    -WinLiveMaxPlayers="$MAX_PLAYERS"

