# PBC Plume Tracker — Android v1 MVP

Kotlin MVVM Android app for the Palm Beach Plume Tracker backend.

## Prerequisites

- **Android Studio Hedgehog** (2023.1.1) or newer
- **Android SDK** API 26+
- **Mapbox account** (free) — https://account.mapbox.com
- **Backend** running (see )

## Quick Setup

### 1. Mapbox tokens

You need two tokens from https://account.mapbox.com/access-tokens/

**Secret token** (SDK download) — add to :


**Public token** (map rendering) — copy  to 
in this  folder and fill in:


 is git-ignored and never committed.

### 2. Open in Android Studio

- File > Open > select this  folder
- Let Gradle sync complete
- Connect a device or start an emulator (API 26+)
- Run the  configuration

### 3. Point the app at your backend

**Default backend URL:** `http://10.0.2.2:8000` (Android emulator localhost).

For a real device on the same Wi-Fi:

1. Start the backend on the PC so it listens on all interfaces:
   ```powershell
   cd "C:\Users\chuck\PBC-Current-Tracker\backend"
   py -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. Find the PC's local IP address:
   ```powershell
   Get-NetIPAddress -AddressFamily IPv4 |
       Where-Object {$_.IPAddress -like "192.168*" -or $_.IPAddress -like "10.*" -or $_.IPAddress -like "172.*"} |
       Select-Object IPAddress, InterfaceAlias
   ```
3. Open the app → **Settings → Data source → Live** and enter:
   ```
   http://<pc-ip>:8000
   ```
   Example: `http://192.168.1.249:8000`
4. Tap Save and pull down to refresh.

If the phone still cannot connect, allow Python through Windows Firewall for private networks.

## Project Structure



## Key Behaviours

| Behaviour | Detail |
|-----------|--------|
| Null fields | Shown as N/A, never crash |
| Partial backend data | Each section renders independently |
| Refresh | FAB = immediate; WorkManager = 30-min background |
| Snorkel badge | Green (>=80) / Olive (>=60) / Amber (>=40) / Orange (>=20) / Red (<20) |
| Clarity overlay | Semi-transparent teal->brown circle centred on inlet |
| Current arrow | Blue arrow rotated to direction_deg, speed in knots |

## v2 Notes (not in this build)

Sargassum map layer and details panel are Android v2.
The  field in  will always be null until
Backend Phase 4 ships.

## Build Variants

- **debug** — Timber logging enabled, debug screen accessible
- **release** — logging off (add signing config before distributing)
