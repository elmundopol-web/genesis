"""Ventana de GENESIS AUTODEV. No requiere dependencias de pip."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import AgentError, MODEL_DEFAULT, Ollama, Session


BG = "#101724"
CARD = "#192337"
INPUT = "#202e45"
WHITE = "#eff5ff"
MUTED = "#9caec8"
BLUE = "#61b8fa"
GREEN = "#71d8b4"


class AutoDevApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("GENESIS · AutoDev")
        root.geometry("1060x790")
        root.minsize(820, 640)
        root.configure(bg=BG)
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.stop = threading.Event()
        self.session: Session | None = None
        self.folder_var = tk.StringVar(value=str(Path(__file__).resolve().parent.parent))
        self.model_var = tk.StringVar(value=MODEL_DEFAULT)
        self.minutes_var = tk.StringVar(value="120")
        self.status_var = tk.StringVar(value="Esperando una tarea")
        self.session_var = tk.StringVar(value="Todavía no hay una sesión activa")
        self._build()
        self.root.after(120, self._pump)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _label(self, parent, content: str, *, size: int = 11, fg: str = MUTED, bold: bool = False):
        return tk.Label(parent, text=content, bg=parent.cget("bg"), fg=fg,
                        font=("Segoe UI", size, "bold" if bold else "normal"), anchor="w")

    def _button(self, parent, content: str, action, *, strong: bool = False):
        button = tk.Button(parent, text=content, command=action, relief="flat", cursor="hand2",
                           bg=BLUE if strong else INPUT, fg=BG if strong else WHITE,
                           activebackground="#a2d7ff" if strong else "#2b3b55",
                           font=("Segoe UI", 11, "bold"), padx=18, pady=10, bd=0)
        return button

    def _build(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=34, pady=(25, 18))
        self._label(top, "G E N E S I S   /   A U T O D E V", size=11, fg=BLUE, bold=True).pack(anchor="w")
        self._label(top, "Tu programador local", size=27, fg=WHITE, bold=True).pack(anchor="w", pady=(5, 2))
        self._label(top, "Crea una rama de trabajo, cambia el código y comprueba las pruebas.", size=11).pack(anchor="w")

        settings = tk.Frame(self.root, bg=CARD, padx=22, pady=18)
        settings.pack(fill="x", padx=34)
        self._label(settings, "PROYECTO GÉNESIS", size=10, fg=BLUE, bold=True).pack(anchor="w", pady=(0, 7))
        folder_row = tk.Frame(settings, bg=CARD)
        folder_row.pack(fill="x")
        tk.Entry(folder_row, textvariable=self.folder_var, font=("Segoe UI", 11), bg=INPUT, fg=WHITE,
                 insertbackground=WHITE, relief="flat").pack(side="left", fill="x", expand=True, ipady=8)
        self._button(folder_row, "Elegir carpeta", self._choose).pack(side="left", padx=(9, 0))

        values = tk.Frame(settings, bg=CARD)
        values.pack(fill="x", pady=(14, 0))
        self._label(values, "Modelo local", fg=WHITE).pack(side="left", padx=(0, 8))
        tk.Entry(values, textvariable=self.model_var, width=26, font=("Segoe UI", 11),
                 bg=INPUT, fg=WHITE, insertbackground=WHITE, relief="flat").pack(side="left", ipady=7)
        self._label(values, "Duración máxima (min)", fg=WHITE).pack(side="left", padx=(22, 8))
        tk.Entry(values, textvariable=self.minutes_var, width=7, font=("Segoe UI", 11),
                 bg=INPUT, fg=WHITE, insertbackground=WHITE, relief="flat").pack(side="left", ipady=7)
        self._button(values, "Comprobar Ollama", self._check_ollama).pack(side="right")

        task_card = tk.Frame(self.root, bg=CARD, padx=22, pady=18)
        task_card.pack(fill="x", padx=34, pady=16)
        self._label(task_card, "NUEVA TAREA", size=10, fg=BLUE, bold=True).pack(anchor="w", pady=(0, 9))
        self.task = tk.Text(task_card, height=5, wrap="word", bg=INPUT, fg=WHITE,
                            font=("Segoe UI", 11), insertbackground=WHITE, padx=12, pady=10,
                            relief="flat", selectbackground="#41617c")
        self.task.pack(fill="x")
        self.task.insert("1.0", "Describe aquí una mejora pequeña y verificable de Génesis...")
        controls = tk.Frame(task_card, bg=CARD)
        controls.pack(fill="x", pady=(13, 0))
        self.start_btn = self._button(controls, "▶  Iniciar desarrollo", self._start, strong=True)
        self.start_btn.pack(side="left")
        self.resume_btn = self._button(controls, "↺  Reanudar sesión", self._resume)
        self.resume_btn.pack(side="left", padx=(10, 0))
        self.stop_btn = self._button(controls, "■  Detener", self._stop)
        self.stop_btn.pack(side="right")
        self.stop_btn.configure(state="disabled")

        run = tk.Frame(self.root, bg=CARD, padx=22, pady=18)
        run.pack(fill="both", expand=True, padx=34, pady=(0, 26))
        self._label(run, "ACTIVIDAD", size=10, fg=BLUE, bold=True).pack(anchor="w")
        tk.Label(run, textvariable=self.status_var, bg=CARD, fg=GREEN, font=("Segoe UI", 13, "bold"),
                 anchor="w").pack(fill="x", pady=(8, 2))
        tk.Label(run, textvariable=self.session_var, bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9), anchor="w", wraplength=920).pack(fill="x", pady=(0, 12))
        logs = tk.Frame(run, bg=CARD)
        logs.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(logs)
        scrollbar.pack(side="right", fill="y")
        self.log = tk.Text(logs, bg="#0c1422", fg="#c9d8ed", font=("Consolas", 10),
                           insertbackground=WHITE, relief="flat", wrap="word", state="disabled",
                           padx=12, pady=12, yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.log.yview)
        self._append("Listo. Ollama debe estar instalado y el modelo descargado. No se usa ninguna API de pago.")

    def _append(self, value: str):
        self.log.configure(state="normal")
        self.log.insert("end", value.strip() + "\n\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _choose(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta raíz de GENESIS")
        if folder:
            self.folder_var.set(folder)

    def _check_ollama(self):
        def work():
            try:
                import json
                import urllib.request
                with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=8) as response:
                    models = [item["name"] for item in json.load(response).get("models", [])]
                self.events.put(("message", "Ollama conectado. Modelos instalados: " + (", ".join(models) or "ninguno")))
            except Exception as exc:
                self.events.put(("message", "No se detecta Ollama. Instálalo y descarga el modelo. Detalle: " + str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        goal = self.task.get("1.0", "end").strip()
        try:
            if goal.startswith("Describe aquí"):
                raise AgentError("Escribe una tarea concreta para empezar.")
            session = Session.create(Path(self.folder_var.get()), goal, self.model_var.get().strip(),
                                     int(self.minutes_var.get()))
        except (AgentError, ValueError, OSError, FileNotFoundError) as exc:
            messagebox.showerror("No se puede iniciar", str(exc))
            return
        self._launch(session)

    def _resume(self):
        if self.worker and self.worker.is_alive():
            return
        state_file = filedialog.askopenfilename(title="Selecciona state.json de una sesión anterior",
                                                filetypes=[("Estado de sesión", "*.json")])
        if not state_file:
            return
        try:
            session = Session.open(Path(state_file))
        except (AgentError, OSError, ValueError, KeyError) as exc:
            messagebox.showerror("Sesión no válida", str(exc))
            return
        self._launch(session)

    def _launch(self, session: Session):
        self.session = session
        self.stop.clear()
        self.start_btn.configure(state="disabled")
        self.resume_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.status_var.set("Trabajando en una rama aislada…")
        self.session_var.set(f"Rama {session.state['branch']}  ·  Carpeta {session.state['worktree']}")
        self._append("Nueva sesión: " + session.state["id"] + ". Estado: " + str(session.state_file))

        def work():
            try:
                outcome = session.run(lambda message: self.events.put(("message", message)), self.stop, Ollama())
                self.events.put(("ended", outcome))
            except Exception as exc:
                self.events.put(("ended", "error: " + str(exc)))

        self.worker = threading.Thread(target=work, daemon=True)
        self.worker.start()

    def _stop(self):
        self.stop.set()
        self.status_var.set("Solicitada la parada (puede esperar a Ollama)…")

    def _pump(self):
        try:
            while True:
                kind, content = self.events.get_nowait()
                if kind == "message":
                    self._append(content)
                elif kind == "ended":
                    self.status_var.set({"done": "Completado y validado", "paused": "Pausado · puedes reanudar",
                                         "done_unverified": "Terminado sin cambios"}.get(content, "Finalizado: " + content))
                    self.start_btn.configure(state="normal")
                    self.resume_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(120, self._pump)

    def _close(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Sesión activa", "Pulsa Detener y espera a que se pause antes de cerrar.")
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    AutoDevApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
