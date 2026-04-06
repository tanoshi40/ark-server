#!/bin/bash
set -e

STEAM_HOME="/home/steam"
ASA_HOME="$STEAM_HOME/asa"
STEAMCMD_HOME="$STEAM_HOME/steamcmd"
WINE_PREFIX="$STEAM_HOME/wineprefix"

echo "[PRE] Ensuring expected directories exist and fixing permissions on mounted volumes..."
mkdir -p "$ASA_HOME" "$STEAMCMD_HOME" "$WINE_PREFIX"
chown -R steam:steam "$STEAM_HOME" 2>/dev/null || true

echo "[PRE] Dropping to steam user and starting Python entrypoint..."
exec su - steam -c "python3 $STEAM_HOME/server.py"