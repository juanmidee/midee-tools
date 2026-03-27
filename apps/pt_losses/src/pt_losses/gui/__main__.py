from __future__ import annotations

from pathlib import Path
import sys
import tkinter as tk


def _find_splash_path() -> Path | None:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    candidates = [
        base / "splash-screen.png",
        base / "assets" / "splash-screen.png",
        base / "pt_losses" / "gui" / "assets" / "splash-screen.png",
        Path(__file__).resolve().parent / "assets" / "splash-screen.png",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _build_early_splash() -> tuple[tk.Tk, tk.Toplevel | None]:
    root = tk.Tk()
    root.withdraw()

    splash_path = _find_splash_path()
    if splash_path is None:
        return root, None

    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg="#e8edf3")
    splash.attributes("-topmost", True)

    splash_image = tk.PhotoImage(file=str(splash_path))
    splash._splash_image = splash_image  # type: ignore[attr-defined]
    label = tk.Label(splash, image=splash_image, bd=0, highlightthickness=0)
    label.pack()

    splash.update_idletasks()
    width = splash.winfo_width()
    height = splash.winfo_height()
    x = max(0, (splash.winfo_screenwidth() - width) // 2)
    y = max(0, (splash.winfo_screenheight() - height) // 2)
    splash.geometry(f"{width}x{height}+{x}+{y}")
    splash.update()
    return root, splash


if __name__ == "__main__":
    root, splash = _build_early_splash()
    from pt_losses.gui.app import run

    run(root=root, splash=splash)
