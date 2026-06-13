import os
import shutil
import subprocess
import sys
from pathlib import Path
from rich.console import Console

console = Console()


def run_uninstall() -> None:
    """Completely uninstall EgoShell, configs, services, and repository files."""
    console.print("\n  [bold red]⚠ WARNING: You are about to completely uninstall EgoShell.[/bold red]")
    console.print("  This action will permanently delete:")
    console.print("    • The background system service (systemd or launchd)")
    console.print("    • The 'egoshell' global command launcher")
    console.print("    • All configurations, memories, and databases in ~/.egoshell")
    console.print("    • The cloned EgoShell code repository directory")
    
    try:
        ans = input("\n  Are you sure you want to uninstall EgoShell? (y/N): ").strip().lower()
    except KeyboardInterrupt:
        console.print("\n  Uninstall cancelled.")
        return

    if ans not in ("y", "yes"):
        console.print("  Uninstall cancelled.")
        return

    console.print("\n  [cyan]Starting uninstallation...[/cyan]")

    # 1. Systemd Service cleanup (Linux)
    service_name = "egoshell.service"
    systemd_path = Path.home() / ".config" / "systemd" / "user" / service_name
    if systemd_path.exists():
        console.print("  Stopping and disabling systemd service...")
        try:
            subprocess.run(["systemctl", "--user", "stop", service_name], capture_output=True)
            subprocess.run(["systemctl", "--user", "disable", service_name], capture_output=True)
            systemd_path.unlink()
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            console.print("  [green]✓[/green] Removed systemd background service.")
        except Exception as e:
            console.print(f"  [red]✗[/red] Failed to stop systemd service: {e}")

    # 2. Launchd Service cleanup (macOS)
    label = "com.egoshell.agent"
    launchd_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    if launchd_path.exists():
        console.print("  Stopping and removing launchd service...")
        try:
            try:
                uid_res = subprocess.run(["id", "-u"], capture_output=True, text=True)
                uid = uid_res.stdout.strip()
                subprocess.run(
                    ["launchctl", "bootout", f"gui/{uid}", str(launchd_path)],
                    capture_output=True
                )
            except Exception:
                subprocess.run(["launchctl", "unload", str(launchd_path)], capture_output=True)
            launchd_path.unlink()
            console.print("  [green]✓[/green] Removed launchd background service.")
        except Exception as e:
            console.print(f"  [red]✗[/red] Failed to stop launchd service: {e}")

    # 3. Remove global command launcher
    global_bin = Path.home() / ".local" / "bin" / "egoshell"
    if global_bin.exists():
        try:
            global_bin.unlink()
            console.print("  [green]✓[/green] Removed 'egoshell' launcher from ~/.local/bin.")
        except Exception as e:
            console.print(f"  [red]✗[/red] Failed to remove command launcher: {e}")

    # 4. Remove configuration & databases
    data_dir = Path.home() / ".egoshell"
    if data_dir.exists():
        try:
            shutil.rmtree(data_dir)
            console.print("  [green]✓[/green] Removed configuration and database directory (~/.egoshell).")
        except Exception as e:
            console.print(f"  [red]✗[/red] Failed to delete data directory: {e}")

    # 5. Remove project repository directory
    project_dir = Path(__file__).resolve().parent.parent
    if project_dir.exists() and project_dir.name == "EGOSHELL":
        try:
            console.print(f"  [green]✓[/green] Scheduling project repository removal ({project_dir})...")
            # Detach a background shell job to remove project_dir after we exit
            cmd = f"sleep 0.5 && rm -rf '{project_dir}'"
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            console.print(f"  [red]✗[/red] Failed to schedule repository removal: {e}")
            console.print(f"  Please manually delete: {project_dir}")

    console.print("\n  [bold green]✓ EgoShell has been successfully uninstalled.[/bold green]")
    sys.exit(0)
