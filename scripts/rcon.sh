#!/bin/bash
# /rcon.sh - Send RCON commands to the ASA server inside the container

if [ $# -eq 0 ]; then
    echo "Usage: $0 '<command>'"
    exit 1
fi

# Join all arguments into a single command string
RCON_COMMAND="$*"

# Use environment variables for RCON authentication (should be set in the container)
/usr/local/bin/mcrcon -H localhost -P "$RCON_PORT" -p "$ADMIN_PASSWORD" "$RCON_COMMAND"
