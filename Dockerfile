FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

ENV STEAM_HOME=/home/steam
ENV ASA_HOME=$STEAM_HOME/asa
ENV STEAMCMD_HOME=$STEAM_HOME/steamcmd
ENV WINE_PREFIX=$STEAM_HOME/wineprefix
ENV WINEPREFIX=$WINE_PREFIX
ENV WINEARCH=win64
ENV DISPLAY=:0
ENV PATH=$PATH:$STEAMCMD_HOME

ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Install dependencies
RUN dpkg --add-architecture i386 && \
    apt update && \
    apt install -y \
        wget curl tar unzip \
        lib32gcc-s1 lib32stdc++6 libgl1-mesa-dri:i386 \
        procps ca-certificates \
        python3 python3-pip locales dbus \
        wine64 wine32 && \
     apt clean && \
     rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8 && \
    dbus-uuidgen > /etc/machine-id 

# Install mcrcon for RCON communication
RUN wget -qO /tmp/mcrcon.tar.gz https://github.com/Tiiffi/mcrcon/releases/download/v0.7.2/mcrcon-0.7.2-linux-x86-64.tar.gz && \
    tar -xzf /tmp/mcrcon.tar.gz -C /usr/local/bin && \
    chmod +x /usr/local/bin/mcrcon && \
    rm /tmp/mcrcon.tar.gz

# Create users and directories
RUN useradd -m steam
RUN mkdir -p $ASA_HOME $STEAMCMD_HOME $WINE_PREFIX && \
    chown -R steam:steam $STEAM_HOME

USER steam
WORKDIR $STEAMCMD_HOME

# Install SteamCMD
RUN wget -qO- https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz | tar -xvz -C $STEAMCMD_HOME

# Back to root for permissions management
USER root
WORKDIR $STEAM_HOME

# Copy scripts and helpers
COPY --chmod=755 entrypoint.py /entrypoint.py

# Expose default ports
EXPOSE 7777/udp 27015/udp 27020/tcp

ENTRYPOINT ["python3", "/entrypoint.py"]