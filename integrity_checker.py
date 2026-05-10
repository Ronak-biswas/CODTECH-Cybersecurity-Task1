# Project: File Integrity Checker
# Internship: CODTECH IT SOLUTIONS
# Name: Ronak Biswas
# Task: Task 1
#!/usr/bin/env python3
import hashlib
import json
import os
import sys
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────
DB_FILENAME    = ".integrity_db.json"
LOG_FILENAME   = "integrity_log.txt"
DEFAULT_ALGO   = "sha256"
SUPPORTED_ALGOS = ["md5", "sha1", "sha256", "sha512", "blake2b"]
CHUNK_SIZE     = 65536  # 64 KB

# ANSI colors setup
_use_color = sys.stdout.isatty() and os.name != "nt"
def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _use_color else text

RED    = lambda t: _c("91", t)
GREEN  = lambda t: _c("92", t)
YELLOW = lambda t: _c("93", t)
CYAN   = lambda t: _c("96", t)
BOLD   = lambda t: _c("1",  t)
DIM    = lambda t: _c("2",  t)

# ─────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILENAME, encoding="utf-8"),
    ],
)
log = logging.getLogger("integrity")

# ─────────────────────────────────────────────
#  Core hashing
# ─────────────────────────────────────────────
def compute_hash(filepath: Path, algorithm: str = DEFAULT_ALGO) -> Optional[str]:
    try:
        h = hashlib.new(algorithm)
        with open(filepath, "rb") as fh:
            while chunk := fh.read(CHUNK_SIZE):
                h.update(chunk)
        return h.hexdigest()
    except Exception as exc:
        log.warning(f"Cannot read {filepath}: {exc}")
        return None

def scan_directory(directory: Path, algorithm: str, extensions: Optional[list]) -> Dict[str, dict]:
    snapshot: Dict[str, dict] = {}
    for root, dirs, files in os.walk(directory):
        # Hidden folders skip karein
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        
        for name in files:
            # Database aur Log file ko scan nahi karna hai
            if name in [DB_FILENAME, LOG_FILENAME]:
                continue
                
            path = Path(root) / name
            if extensions and path.suffix.lower() not in extensions:
                continue
                
            rel = str(path.relative_to(directory))
            h = compute_hash(path, algorithm)
            if h is not None:
                snapshot[rel] = {
                    "hash":  h,
                    "size":  path.stat().st_size,
                    "mtime": path.stat().st_mtime,
                }
    return snapshot

# ─────────────────────────────────────────────
#  Database helpers
# ─────────────────────────────────────────────
def _db_path(directory: Path) -> Path:
    return directory / DB_FILENAME

def save_snapshot(directory: Path, snapshot: dict, algorithm: str) -> None:
    db = {
        "metadata": {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "directory":  str(directory.resolve()),
            "algorithm":  algorithm,
            "file_count": len(snapshot),
        },
        "files": snapshot,
    }
    with open(_db_path(directory), "w", encoding="utf-8") as fh:
        json.dump(db, fh, indent=2)
    log.info(f"Snapshot saved: {len(snapshot)} files.")

def load_snapshot(directory: Path) -> Optional[dict]:
    db_file = _db_path(directory)
    if not db_file.exists():
        return None
    with open(db_file, "r", encoding="utf-8") as fh:
        return json.load(fh)

# ─────────────────────────────────────────────
#  Comparison Engine
# ─────────────────────────────────────────────
def compare_snapshots(old_db: dict, new_snap: dict) -> dict:
    old_files = old_db.get("files", {})
    new_files = new_snap

    added     = {p: new_files[p] for p in new_files if p not in old_files}
    removed   = {p: old_files[p] for p in old_files if p not in new_files}
    modified  = {
        p: {"old": old_files[p], "new": new_files[p]}
        for p in old_files
        if p in new_files and old_files[p]["hash"] != new_files[p]["hash"]
    }
    unchanged = [p for p in old_files if p in new_files and old_files[p]["hash"] == new_files[p]["hash"]]
    
    return {"added": added, "removed": removed, "modified": modified, "unchanged_count": len(unchanged)}

# FIX: n ko float liya taaki division ke baad type error na aaye
def _fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024: 
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"

def print_report(diff: dict):
    print(BOLD("\n" + "="*50))
    print(BOLD("            FILE INTEGRITY REPORT"))
    print(BOLD("="*50))

    if diff["added"]:
        print(GREEN(f"\n[+] ADDED ({len(diff['added'])} files):"))
        for p in diff["added"]: print(f"    - {p}")

    if diff["removed"]:
        print(RED(f"\n[-] REMOVED ({len(diff['removed'])} files):"))
        for p in diff["removed"]: print(f"    - {p}")

    if diff["modified"]:
        print(YELLOW(f"\n[!] MODIFIED ({len(diff['modified'])} files):"))
        for p, v in diff["modified"].items():
            # FIX: Yahan _fmt_size call kiya hai taaki output sahi dikhe
            delta = v['new']['size'] - v['old']['size']
            print(f"    - {p} (Size change: {_fmt_size(delta)})")

    print(DIM(f"\n[.] UNCHANGED: {diff['unchanged_count']} files"))
    
    status = GREEN("STATUS: OK") if not (diff["added"] or diff["removed"] or diff["modified"]) else RED("STATUS: CHANGES DETECTED")
    print(BOLD(f"\n{status}"))
    print(BOLD("="*50 + "\n"))

# ─────────────────────────────────────────────
#  Commands
# ─────────────────────────────────────────────
def cmd_init(args):
    directory = Path(args.directory).resolve()
    if not directory.is_dir():
        print(RED(f"Error: {directory} is not a directory.")); return
    
    snap = scan_directory(directory, args.algorithm, args.extensions)
    save_snapshot(directory, snap, args.algorithm)
    print(GREEN(f"Initialized baseline for {len(snap)} files."))

def cmd_check(args):
    directory = Path(args.directory).resolve()
    db = load_snapshot(directory)
    if not db:
        print(RED("No baseline found. Run 'init' command first.")); return False
    
    new_snap = scan_directory(directory, db["metadata"]["algorithm"], args.extensions)
    diff = compare_snapshots(db, new_snap)
    print_report(diff)
    return bool(diff["added"] or diff["removed"] or diff["modified"])

def cmd_watch(args):
    print(CYAN(f"Watching {args.directory} every {args.interval}s... (Ctrl+C to stop)"))
    try:
        while True:
            cmd_check(args)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(YELLOW("\nStopped watcher."))

# ─────────────────────────────────────────────
#  Main CLI
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="File Integrity Checker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common args
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("directory", help="Directory to monitor")
    parent.add_argument("-e", "--extensions", nargs="+", help="Filter by extensions (e.g. .txt .py)")
    parent.add_argument("-a", "--algorithm", default="sha256", choices=SUPPORTED_ALGOS)

    subparsers.add_parser("init", parents=[parent])
    subparsers.add_parser("check", parents=[parent])
    
    watch_p = subparsers.add_parser("watch", parents=[parent])
    watch_p.add_argument("-i", "--interval", type=int, default=10, help="Seconds between checks")

    args = parser.parse_args()
    
    if args.command == "init": cmd_init(args)
    elif args.command == "check": cmd_check(args)
    elif args.command == "watch": cmd_watch(args)

if __name__ == "__main__":
    main()