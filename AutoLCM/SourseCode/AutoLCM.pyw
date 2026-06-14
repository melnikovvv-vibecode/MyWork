import threading
import time
import tkinter as tk
from tkinter import ttk

from pynput.mouse import Button, Controller as MouseController
import keyboard


class AutoClickerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AutoLCM by Melnikov")
        self.root.resizable(False, False)

        self.mouse = MouseController()

        # State
        self._clicking = False
        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Hotkeys (default)
        self.on_key = "page up"
        self.off_key = "page down"
        self._hotkey_handles: list[int] = []

        # --- GUI ---
        main = ttk.Frame(root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")

        # Status
        self.status_var = tk.StringVar(value="ВЫКЛЮЧЕН")
        self.status_label = ttk.Label(main, textvariable=self.status_var, font=("Segoe UI", 13, "bold"))
        self.status_label.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        self._apply_status_style()

        # Key mapping inputs
        ttk.Label(main, text="Кнопка включения (ON):").grid(row=1, column=0, sticky="w")
        self.on_key_var = tk.StringVar(value=self.on_key)
        self.on_key_entry = ttk.Entry(main, width=18, textvariable=self.on_key_var)
        self.on_key_entry.grid(row=1, column=1, sticky="e")

        ttk.Label(main, text="Кнопка выключения (OFF):").grid(row=2, column=0, sticky="w")
        self.off_key_var = tk.StringVar(value=self.off_key)
        self.off_key_entry = ttk.Entry(main, width=18, textvariable=self.off_key_var)
        self.off_key_entry.grid(row=2, column=1, sticky="e")

        # Delay
        ttk.Label(main, text="Интервал клика (мс):").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.delay_var = tk.StringVar(value="50")
        self.delay_entry = ttk.Entry(main, width=18, textvariable=self.delay_var)
        self.delay_entry.grid(row=3, column=1, sticky="e", pady=(8, 0))

        # Apply
        self.apply_btn = ttk.Button(main, text="Применить", command=self.apply_settings)
        self.apply_btn.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))

        # Manual controls
        controls = ttk.Frame(main)
        controls.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        self.btn_on = ttk.Button(controls, text="Включить", command=self.turn_on)
        self.btn_on.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.btn_off = ttk.Button(controls, text="Выключить", command=self.turn_off)
        self.btn_off.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Footer hint
        hint = ttk.Label(
            main,
            text="Глобальные горячие клавиши требуют прав.",
            foreground="#666"
        )
        hint.grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 0))

        # Close handling
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Register hotkeys
        self.register_hotkeys()

    def _apply_status_style(self):
        # Simple color change
        if self._clicking:
            self.status_label.configure(foreground="#0a7d0a")
        else:
            self.status_label.configure(foreground="#8a1f1f")

    def set_status(self, clicking: bool):
        with self._lock:
            self._clicking = clicking
            self.status_var.set("ВКЛЮЧЕН" if clicking else "ВЫКЛЮЧЕН")
            self._apply_status_style()

    def parse_delay_ms(self) -> int:
        try:
            ms = int(self.delay_var.get().strip())
        except Exception:
            ms = 50
        # Safety clamp
        if ms < 1:
            ms = 1
        if ms > 1000:
            ms = 1000
        return ms

    def click_loop(self):
        # Runs in background thread
        while not self._stop_event.is_set():
            # Clicking
            delay_ms = self.parse_delay_ms()
            with self._lock:
                if not self._clicking:
                    # Sleep lightly to avoid busy loop while OFF
                    time.sleep(0.05)
                    continue

            self.mouse.press(Button.left)
            self.mouse.release(Button.left)
            time.sleep(delay_ms / 1000.0)

    def turn_on(self):
        if self._clicking:
            return

        self._stop_event.clear()
        self.set_status(True)

        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(target=self.click_loop, daemon=True)
            self._worker_thread.start()

    def turn_off(self):
        if not self._clicking:
            return
        self.set_status(False)

    def apply_settings(self):
        # Normalize key names for keyboard library
        new_on = self.on_key_var.get().strip().lower()
        new_off = self.off_key_var.get().strip().lower()

        # keyboard library accepts strings like "page up", "page down"
        if not new_on or not new_off:
            return

        self.on_key = new_on
        self.off_key = new_off

        # Re-register hotkeys
        self.register_hotkeys()

    def _unregister_hotkeys(self):
        for handle in self._hotkey_handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:
                pass
        self._hotkey_handles.clear()

    def register_hotkeys(self):
        # Remove old
        self._unregister_hotkeys()

        # Register new
        try:
            h1 = keyboard.add_hotkey(self.on_key, lambda: self.turn_on(), suppress=False)
            h2 = keyboard.add_hotkey(self.off_key, lambda: self.turn_off(), suppress=False)
            self._hotkey_handles = [h1, h2]
        except Exception as e:
            # If hotkeys cannot be registered, we keep UI functional.
            self.status_var.set(f"ГОРЯЧИЕ КЛАВИШИ: ошибка")
            self._apply_status_style()

    def on_close(self):
        try:
            self._unregister_hotkeys()
        except Exception:
            pass
        try:
            self._stop_event.set()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    # force custom window icon (tk)
    try:
        root.iconbitmap('Click.ico')
    except Exception:
        pass

    # Use ttk theme if available
    try:
        style = ttk.Style(root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass

    app = AutoClickerApp(root)
    root.mainloop()


if __name__ == "__main__":
    # Важно: Tk берёт иконку из ресурсов приложения, а не из EXE-иконки PyInstaller.
    main()


