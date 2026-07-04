# system.py — MyBuddy System Commands
# Handles volume control, time/date queries, and application launching.

import datetime
import logging
import os
import platform
import re
import subprocess

import config

log  = logging.getLogger(__name__)
OS   = platform.system()   # "Windows" | "Darwin" | "Linux"


# ════════════════════════════════════════════════════════════════════════════
# TIME & DATE
# ════════════════════════════════════════════════════════════════════════════

def tell_time() -> str:
    now = datetime.datetime.now()
    return f"It's {now.strftime('%I:%M %p').lstrip('0')}."


def tell_date() -> str:
    now = datetime.datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}."


def tell_datetime() -> str:
    now = datetime.datetime.now()
    return (
        f"It's {now.strftime('%I:%M %p').lstrip('0')} "
        f"on {now.strftime('%A, %B %d, %Y')}."
    )


# ════════════════════════════════════════════════════════════════════════════
# VOLUME CONTROL
# ════════════════════════════════════════════════════════════════════════════

def _volume_windows(direction: str):
    """
    Uses nircmd (free utility) for Windows volume control.
    Download from https://www.nirsoft.net/utils/nircmd.html and add to PATH.
    """
    step = 65535 * config.VOLUME_STEP_PERCENT // 100  # nircmd uses 0-65535 range
    cmds = {
        "up":   ["nircmd.exe", "changesysvolume", str(step)],
        "down": ["nircmd.exe", "changesysvolume", str(-step)],
        "mute": ["nircmd.exe", "mutesysvolume", "1"],
        "unmute": ["nircmd.exe", "mutesysvolume", "0"],
    }
    subprocess.call(cmds[direction], stderr=subprocess.DEVNULL)


def _volume_mac(direction: str):
    if direction in ("up", "down"):
        current_bytes = subprocess.check_output(
            ["osascript", "-e", "output volume of (get volume settings)"]
        )
        current = int(current_bytes.strip())
        step = config.VOLUME_STEP_PERCENT
        new_vol = min(100, current + step) if direction == "up" else max(0, current - step)
        subprocess.call(["osascript", "-e", f"set volume output volume {new_vol}"])
    elif direction == "mute":
        subprocess.call(["osascript", "-e", "set volume with output muted"])
    elif direction == "unmute":
        subprocess.call(["osascript", "-e", "set volume without output muted"])


def _volume_linux(direction: str):
    step = f"{config.VOLUME_STEP_PERCENT}%"
    cmds = {
        "up":     ["amixer", "-q", "sset", "Master", f"{step}+"],
        "down":   ["amixer", "-q", "sset", "Master", f"{step}-"],
        "mute":   ["amixer", "-q", "sset", "Master", "mute"],
        "unmute": ["amixer", "-q", "sset", "Master", "unmute"],
    }
    subprocess.call(cmds[direction], stderr=subprocess.DEVNULL)


def _change_volume(direction: str) -> str:
    try:
        if OS == "Windows":
            _volume_windows(direction)
        elif OS == "Darwin":
            _volume_mac(direction)
        else:
            _volume_linux(direction)

        labels = {
            "up":     "Volume turned up.",
            "down":   "Volume turned down.",
            "mute":   "Muted.",
            "unmute": "Unmuted.",
        }
        return labels.get(direction, "Volume changed.")
    except FileNotFoundError:
        hint = " Make sure nircmd is installed and on your PATH." if OS == "Windows" else ""
        return f"Sorry, I couldn't change the volume.{hint}"
    except Exception as e:
        log.error(f"Volume error: {e}")
        return "Sorry, I ran into a problem changing the volume."


def volume_up()     -> str: return _change_volume("up")
def volume_down()   -> str: return _change_volume("down")
def volume_mute()   -> str: return _change_volume("mute")
def volume_unmute() -> str: return _change_volume("unmute")


# ════════════════════════════════════════════════════════════════════════════
# APPLICATION LAUNCHER
# ════════════════════════════════════════════════════════════════════════════

# Built-in app map: spoken name → command per OS
_BUILTIN_APPS: dict[str, dict[str, str]] = {
    "chrome":         {"Windows": "chrome",                    "Darwin": "open -a 'Google Chrome'",    "Linux": "google-chrome"},
    "google chrome":  {"Windows": "chrome",                    "Darwin": "open -a 'Google Chrome'",    "Linux": "google-chrome"},
    "firefox":        {"Windows": "firefox",                   "Darwin": "open -a Firefox",            "Linux": "firefox"},
    "edge":           {"Windows": "msedge",                    "Darwin": "open -a 'Microsoft Edge'",   "Linux": "microsoft-edge"},
    "notepad":        {"Windows": "notepad",                   "Darwin": "open -a TextEdit",           "Linux": "gedit"},
    "text editor":    {"Windows": "notepad",                   "Darwin": "open -a TextEdit",           "Linux": "gedit"},
    "calculator":     {"Windows": "calc",                      "Darwin": "open -a Calculator",         "Linux": "gnome-calculator"},
    "spotify":        {"Windows": "spotify",                   "Darwin": "open -a Spotify",            "Linux": "spotify"},
    "vscode":         {"Windows": "code",                      "Darwin": "open -a 'Visual Studio Code'","Linux": "code"},
    "vs code":        {"Windows": "code",                      "Darwin": "open -a 'Visual Studio Code'","Linux": "code"},
    "visual studio code": {"Windows": "code",                  "Darwin": "open -a 'Visual Studio Code'","Linux": "code"},
    "terminal":       {"Windows": "cmd",                       "Darwin": "open -a Terminal",           "Linux": "gnome-terminal"},
    "command prompt": {"Windows": "cmd",                       "Darwin": "open -a Terminal",           "Linux": "gnome-terminal"},
    "file manager":   {"Windows": "explorer",                  "Darwin": "open ~",                     "Linux": "nautilus"},
    "files":          {"Windows": "explorer",                  "Darwin": "open ~",                     "Linux": "nautilus"},
    "settings":       {"Windows": "ms-settings:",              "Darwin": "open -a 'System Preferences'","Linux": "gnome-control-center"},
    "task manager":   {"Windows": "taskmgr",                   "Darwin": "open -a 'Activity Monitor'", "Linux": "gnome-system-monitor"},
    "paint":          {"Windows": "mspaint",                   "Darwin": "open -a Paintbrush",         "Linux": "kolourpaint"},
    "word":           {"Windows": "winword",                   "Darwin": "open -a 'Microsoft Word'",   "Linux": "libreoffice --writer"},
    "excel":          {"Windows": "excel",                     "Darwin": "open -a 'Microsoft Excel'",  "Linux": "libreoffice --calc"},
    "powerpoint":     {"Windows": "powerpnt",                  "Darwin": "open -a 'Microsoft PowerPoint'","Linux": "libreoffice --impress"},
    "zoom":           {"Windows": "zoom",                      "Darwin": "open -a Zoom",               "Linux": "zoom"},
    "slack":          {"Windows": "slack",                     "Darwin": "open -a Slack",              "Linux": "slack"},
    "discord":        {"Windows": "discord",                   "Darwin": "open -a Discord",            "Linux": "discord"},
    "whatsapp":       {"Windows": "whatsapp",                  "Darwin": "open -a WhatsApp",           "Linux": "whatsapp-desktop"},
    "vlc":            {"Windows": "vlc",                       "Darwin": "open -a VLC",                "Linux": "vlc"},
    "steam":          {"Windows": "steam",                     "Darwin": "open -a Steam",              "Linux": "steam"},
}


def _extract_app_name(command: str) -> str:
    """Pull the app name that follows open / launch / start."""
    match = re.search(r"(?:open|launch|start|run)\s+(.+)", command, re.IGNORECASE)
    return match.group(1).strip().lower() if match else ""


def _find_app_command(app_name: str) -> str | None:
    """
    Look up the shell command for an app name.
    Checks user custom apps from config first, then the built-in map.
    """
    # Merge built-ins with user overrides (config wins)
    all_apps = {**_BUILTIN_APPS}
    for name, cmd in config.CUSTOM_APPS.items():
        all_apps[name.lower()] = {OS: cmd}

    # Exact match first
    if app_name in all_apps:
        return all_apps[app_name].get(OS)

    # Substring match (e.g. "vs code" matches "visual studio code")
    for key, paths in all_apps.items():
        if app_name in key or key in app_name:
            return paths.get(OS)

    return None


def open_app(command: str) -> str:
    app_name = _extract_app_name(command)
    if not app_name:
        return "Which application would you like me to open?"

    cmd = _find_app_command(app_name)
    if cmd:
        try:
            subprocess.Popen(cmd, shell=True, stderr=subprocess.DEVNULL)
            display = app_name.title()
            return f"Opening {display}."
        except Exception as e:
            log.error(f"Failed to open '{app_name}': {e}")
            return f"Sorry, I couldn't open {app_name}."
    else:
        # Last resort — try running the name directly
        try:
            subprocess.Popen(app_name, shell=True, stderr=subprocess.DEVNULL)
            return f"Trying to open {app_name}."
        except Exception:
            return (
                f"I don't know how to open '{app_name}'. "
                "You can add it to CUSTOM_APPS in config.py."
            )


# ════════════════════════════════════════════════════════════════════════════
# SYSTEM UTILITIES
# ════════════════════════════════════════════════════════════════════════════

def shutdown_system() -> str:
    """Initiate OS shutdown (asks for confirmation before running)."""
    if OS == "Windows":
        subprocess.call(["shutdown", "/s", "/t", "10"])
    elif OS == "Darwin":
        subprocess.call(["sudo", "shutdown", "-h", "+1"])
    else:
        subprocess.call(["shutdown", "-h", "+1"])
    return "Shutting down in one minute."


def restart_system() -> str:
    if OS == "Windows":
        subprocess.call(["shutdown", "/r", "/t", "10"])
    elif OS == "Darwin":
        subprocess.call(["sudo", "shutdown", "-r", "+1"])
    else:
        subprocess.call(["shutdown", "-r", "+1"])
    return "Restarting in one minute."


def lock_screen() -> str:
    if OS == "Windows":
        subprocess.call(["rundll32.exe", "user32.dll,LockWorkStation"])
    elif OS == "Darwin":
        subprocess.call(["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"])
    else:
        subprocess.call(["xdg-screensaver", "lock"])
    return "Screen locked."
