"""Port inspector: list listening TCP ports and map PIDs to managed apps."""
from __future__ import annotations

import psutil


def list_listening_ports() -> list[dict]:
    seen = set()
    items = []
    for conn in psutil.net_connections(kind="inet"):
        if conn.status != psutil.CONN_LISTEN or conn.laddr is None:
            continue
        key = (conn.laddr.ip, conn.laddr.port, conn.pid)
        if key in seen:
            continue
        seen.add(key)
        pname = ""
        try:
            if conn.pid:
                pname = psutil.Process(conn.pid).name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        items.append({
            "address": conn.laddr.ip,
            "port": conn.laddr.port,
            "pid": conn.pid,
            "process": pname,
        })
    items.sort(key=lambda x: x["port"])
    return items


def ports_by_pids() -> dict[int, list[dict]]:
    result: dict[int, list[dict]] = {}
    for item in list_listening_ports():
        if item["pid"]:
            result.setdefault(item["pid"], []).append(item)
    return result


def _descendants(root_pid: int) -> set[int]:
    """Return the pid plus all descendant pids."""
    result = {root_pid}
    try:
        for child in psutil.Process(root_pid).children(recursive=True):
            result.add(child.pid)
    except psutil.Error:
        pass
    return result


def app_port_map(managed: list[dict]) -> dict[int, str]:
    """Map port -> app name. Matches app pid AND its child processes
    (on Windows the app is started via shell, so the real listener
    is a child of the tracked pid)."""
    root_pids = {m["pid"] for m in managed if m.get("pid")}
    if not root_pids:
        return {}
    tree = set()
    for pid in root_pids:
        tree |= _descendants(pid)
    pid_name = {m["pid"]: m["name"] for m in managed if m.get("pid")}
    mapping: dict[int, str] = {}
    for item in list_listening_ports():
        if item["pid"] in tree:
            for pid, name in pid_name.items():
                if item["pid"] in _descendants(pid):
                    mapping[item["port"]] = name
                    break
    return mapping
