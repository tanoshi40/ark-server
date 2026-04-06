# ASA Docker Server Setup – Implementation Plan

## 1. Goals

We want a setup that is:

* Portable (Docker-based)
* Maintainable (clean separation of concerns)
* Operable (manual lifecycle control: start/stop/update/backup)
* Persistent (no data loss across restarts)
* Scriptable (cron-friendly automation)

---

## 2. High-Level Architecture

### Separation of Responsibilities

| Component         | Responsibility                                  |
| ----------------- | ----------------------------------------------- |
| Docker Image      | Runtime (SteamCMD, Wine, dependencies)        |
| Volumes (`data/`) | Server install, saves, configs, mods            |
| Host Scripts      | Lifecycle management (start/stop/update/backup) |

---

## 3. Directory Structure

```
~/asa-server/
├── docker-compose.yml
├── .env
├── data/
│   ├── server/          # ASA installation (SteamCMD target)
│   ├── saves/           # Worlds + player data
│   ├── config/          # Game.ini + GameUserSettings.ini
│   ├── logs/
├── backups/
└── scripts/
    ├── start
    ├── stop
    ├── update
    ├── backup
    ├── rcon
    └── manage
```

---

## 4. Environment Configuration

### `.env` (single source of truth)

```
SESSION_NAME=MyASA
SERVER_PASSWORD=yourpassword
ADMIN_PASSWORD=youradminpassword
RCON_PASSWORD=yourrconpassword
PORT=7777
QUERY_PORT=27015
RCON_PORT=27020
MAP_NAME=TheIsland_WP
MOD_IDS=
```

✔ All credentials defined once
✔ Referenced by docker-compose + scripts

---

## 5. Docker Container Design

### Responsibilities

* Provide SteamCMD
* Provide Wine
* Run ASA server
* Expose ports

### ❗ Important Rules

* No ASA installation baked into image
* No credentials inside image
* No lifecycle logic inside container

---

## 6. Volume Mapping

| Host            | Container                                                |
| --------------- | -------------------------------------------------------- |
| `./data/server` | `/home/steam/asa`                                        |
| `./data/saves`  | `/home/steam/asa/ShooterGame/Saved`                      |
| `./data/config` | `/home/steam/asa/ShooterGame/Saved/Config/WindowsServer` |

---

## 7. Server Lifecycle

### 7.1 Start

**Command:**

```
scripts/start
```

**Flow:**

1. Start container
2. Inside container:

   * If server not installed → install via SteamCMD
   * Load config
   * Start ASA via Wine

---

### 7.2 Stop

**Command:**

```
scripts/stop
```

**Flow:**

1. Send RCON broadcast (optional)
2. Trigger save (`saveworld`)
3. Wait
4. Stop container

---

### 7.3 Update (Manual Only)

**Command:**

```
scripts/update
```

**Flow:**

1. Ensure server is stopped
2. Run SteamCMD update
3. Do NOT restart automatically (user controls flow)

---

### 7.4 Backup

**Command:**

```
scripts/backup
```

**Flow:**

1. Assume server is stopped (or warn)
2. Archive:

   * saves
   * config
3. Store in `backups/`

---

## 8. Config Management

### Behavior

* On first run:

  * ASA generates default config
* If config missing:

  * Auto-copy defaults OR use template

### Files

```
data/config/Game.ini
data/config/GameUserSettings.ini
```

### Strategy

* Always mounted externally
* Editable without container rebuild

---

## 9. Mods

### Configuration

Defined via environment:

```
MOD_IDS=123456,789012
```

### Usage

Passed to config

---

## 10. RCON

### Enabled via config

```
RCONEnabled=True
RCONPort=27020
ServerAdminPassword=<ADMIN_PASSWORD>
```

### Usage

```
scripts/rcon "broadcast Hello players"
scripts/rcon "saveworld"
```

---

## 11. Backup Strategy

### Command

```
scripts/backup.sh
```

### Implementation

```
tar -czf backups/asa-<timestamp>.tar.gz \
    data/saves \
    data/config
```

---

## 12. Restore Strategy

```
rm -rf data/saves/*
tar -xzf backup.tar.gz -C data/
```

---

## 13. Cron Automation

### Daily restart + update

```
0 5 * * * scripts/stop.sh && scripts/update.sh && scripts/start.sh
```

### Backup every 6 hours

```
0 */6 * * * scripts/backup.sh
```

---

## 14. Optional: Python Management CLI

Instead of many shell scripts:

### `scripts/manage.py`

Example commands:

```
python manage.py start
python manage.py stop
python manage.py update
python manage.py backup
python manage.py rcon "message"
```

Advantages:

* Cleaner logic
* Easier argument parsing
* Better error handling

---

## 15. Key Principles to Keep

* Never bake large game installs into image
* Always persist state via volumes
* Keep runtime and lifecycle separate
* Make everything scriptable
* Prefer explicit manual control over automation

---

## 16. Future Extensions (Optional)

* Multi-map cluster support
* Metrics / monitoring
* Health checks + auto-restart
* Remote management API
* Backup rotation / retention policy

---

## End of Plan

