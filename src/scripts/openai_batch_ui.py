import json
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_DIR = ROOT_DIR / "src" / "scripts"
JOBS_PATH = ROOT_DIR / "docs" / "translations" / "openai_batch_jobs.json"
ENV_PATH = ROOT_DIR / ".env"
OPENAI_API_BASE = "https://api.openai.com/v1"
MODEL_OPTIONS = (
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-4o",
    "gpt-4o-mini",
)


class BatchUi(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MachineTranslated OpenAI Batch")
        self.geometry("1120x720")
        self.minsize(900, 600)

        self.output_queue = queue.Queue()
        self.running = False

        self.api_key_var = tk.StringVar()
        self.project_var = tk.StringVar()
        self.url_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.model_var = tk.StringVar(value="gpt-5-mini")
        self.skip_existing_var = tk.BooleanVar(value=True)
        self.submit_batch_var = tk.BooleanVar(value=True)
        self.fix_lines_var = tk.BooleanVar(value=False)

        self.load_env_values()
        self.create_widgets()
        self.load_jobs()
        self.after(100, self.drain_output_queue)
        if self.api_key_var.get().strip():
            self.after(400, self.test_api_key)

    def create_widgets(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        api_frame = ttk.LabelFrame(self, text="OpenAI API")
        api_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        api_frame.columnconfigure(1, weight=1)

        ttk.Label(api_frame, text="API key").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(api_frame, textvariable=self.api_key_var, show="*").grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(api_frame, text="Project").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(api_frame, textvariable=self.project_var).grid(row=1, column=1, sticky="ew", padx=8, pady=6)

        api_buttons = ttk.Frame(api_frame)
        api_buttons.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=8, pady=6)
        self.save_api_button = ttk.Button(api_buttons, text="Save .env", command=self.save_env_values)
        self.save_api_button.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        self.test_api_button = ttk.Button(api_buttons, text="Test API Key", command=self.test_api_key)
        self.test_api_button.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        self.save_test_api_button = ttk.Button(api_buttons, text="Save + Test", command=self.save_and_test_api_key)
        self.save_test_api_button.grid(row=2, column=0, sticky="ew")

        self.api_status_var = tk.StringVar(value="API key: not set")
        self.api_status_label = ttk.Label(api_frame, textvariable=self.api_status_var, foreground="#7a1f1f")
        self.api_status_label.grid(row=2, column=1, sticky="w", padx=8, pady=(0, 6))
        self.update_api_status_from_env()

        setup_frame = ttk.LabelFrame(self, text="Create / Submit Batch")
        setup_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=6)
        setup_frame.columnconfigure(1, weight=1)

        ttk.Label(setup_frame, text="Syosetsu URL").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(setup_frame, textvariable=self.url_var).grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(setup_frame, text="Series name").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(setup_frame, textvariable=self.name_var).grid(row=1, column=1, sticky="ew", padx=8, pady=6)

        ttk.Label(setup_frame, text="Model").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        model_box = ttk.Combobox(setup_frame, textvariable=self.model_var, values=MODEL_OPTIONS, state="readonly", width=18)
        model_box.grid(row=2, column=1, sticky="w", padx=8, pady=6)

        options = ttk.Frame(setup_frame)
        options.grid(row=3, column=1, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(options, text="Skip existing chapters", variable=self.skip_existing_var).grid(row=0, column=0, padx=(0, 16))
        ttk.Checkbutton(options, text="Submit OpenAI batch", variable=self.submit_batch_var).grid(row=0, column=1, padx=(0, 16))
        ttk.Checkbutton(options, text="Fix line counts before finalize", variable=self.fix_lines_var).grid(row=0, column=2)

        self.run_setup_button = ttk.Button(setup_frame, text="Run Setup Script", command=self.run_setup_script)
        self.run_setup_button.grid(row=0, column=2, rowspan=4, sticky="nsew", padx=8, pady=6)

        body = ttk.Frame(self)
        body.grid(row=2, column=0, sticky="nsew", padx=10, pady=6)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(1, weight=1)

        jobs_header = ttk.Frame(body)
        jobs_header.grid(row=0, column=0, sticky="ew", padx=(0, 6), pady=(0, 6))
        jobs_header.columnconfigure(0, weight=1)
        ttk.Label(jobs_header, text="Tracked Jobs").grid(row=0, column=0, sticky="w")
        self.reload_button = ttk.Button(jobs_header, text="Reload List", command=self.load_jobs)
        self.reload_button.grid(row=0, column=1, padx=(6, 0))
        self.refresh_button = ttk.Button(jobs_header, text="Check All Waiting", command=self.run_finalize_all)
        self.refresh_button.grid(row=0, column=2, padx=(6, 0))
        self.finalize_selected_button = ttk.Button(jobs_header, text="Check Selected", command=self.run_finalize_selected)
        self.finalize_selected_button.grid(row=0, column=3, padx=(6, 0))

        columns = ("series", "batch", "workflow", "openai", "output")
        self.jobs_tree = ttk.Treeview(body, columns=columns, show="headings", selectmode="browse")
        self.jobs_tree.heading("series", text="Series")
        self.jobs_tree.heading("batch", text="Batch ID")
        self.jobs_tree.heading("workflow", text="Workflow")
        self.jobs_tree.heading("openai", text="OpenAI")
        self.jobs_tree.heading("output", text="Output File")
        self.jobs_tree.column("series", width=110, minwidth=90, stretch=False)
        self.jobs_tree.column("batch", width=260, minwidth=180)
        self.jobs_tree.column("workflow", width=100, minwidth=90, stretch=False)
        self.jobs_tree.column("openai", width=110, minwidth=90, stretch=False)
        self.jobs_tree.column("output", width=220, minwidth=160)
        self.jobs_tree.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.jobs_tree.yview)
        self.jobs_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=1, column=0, sticky="nse", padx=(0, 6))

        output_frame = ttk.LabelFrame(body, text="Script Output")
        output_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(6, 0))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        self.output = scrolledtext.ScrolledText(output_frame, wrap="word", height=16)
        self.output.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, anchor="w").grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 8))

    def load_env_values(self):
        values = self.read_env_file()
        self.api_key_var.set(values.get("OPENAI_API_KEY", ""))
        self.project_var.set(values.get("OPENAI_PROJECT", ""))

    def read_env_file(self):
        if not ENV_PATH.exists():
            return {}

        values = {}
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
        return values

    def save_env_values(self):
        api_key = self.api_key_var.get().strip()
        project = self.project_var.get().strip()
        if not api_key:
            messagebox.showwarning("Missing API key", "Enter an OpenAI API key before saving.")
            return

        self.write_env_value("OPENAI_API_KEY", api_key)
        if project:
            self.write_env_value("OPENAI_PROJECT", project)
        else:
            self.remove_env_value("OPENAI_PROJECT")

        self.update_api_status_from_env()
        self.log("\nSaved OpenAI settings to .env\n")

    def save_and_test_api_key(self):
        self.save_env_values()
        if self.api_key_var.get().strip():
            self.test_api_key()

    def write_env_value(self, key, value):
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
        found = False
        for index, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[index] = f"{key}={value}"
                found = True
                break
        if not found:
            lines.append(f"{key}={value}")
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def remove_env_value(self, key):
        if not ENV_PATH.exists():
            return
        lines = [
            line for line in ENV_PATH.read_text(encoding="utf-8").splitlines()
            if not line.strip().startswith(f"{key}=")
        ]
        ENV_PATH.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def update_api_status_from_env(self):
        if ENV_PATH.exists() and self.api_key_var.get().strip():
            self.set_api_status("API key: saved, not tested", "#8a6d1d")
        else:
            self.set_api_status("API key: not set", "#7a1f1f")

    def set_api_status(self, text, color):
        self.api_status_var.set(text)
        self.api_status_label.configure(foreground=color)

    def test_api_key(self):
        api_key = self.api_key_var.get().strip()
        if not api_key:
            self.set_api_status("API key: not set", "#7a1f1f")
            messagebox.showwarning("Missing API key", "Enter or save an OpenAI API key first.")
            return

        self.set_api_status("API key: testing...", "#8a6d1d")
        self.log("\nTesting OpenAI API key...\n")
        thread = threading.Thread(target=self.test_api_key_worker, args=(api_key, self.project_var.get().strip()), daemon=True)
        thread.start()

    def test_api_key_worker(self, api_key, project):
        headers = {"Authorization": f"Bearer {api_key}"}
        if project:
            headers["OpenAI-Project"] = project

        request = Request(f"{OPENAI_API_BASE}/models", headers=headers, method="GET")
        try:
            with urlopen(request, timeout=20) as response:
                response.read()
            self.output_queue.put(("api_ok", "API key: OK"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            self.output_queue.put(("api_error", f"API key failed with HTTP {exc.code}: {body}"))
        except URLError as exc:
            self.output_queue.put(("api_error", f"API key test failed: {exc.reason}"))
        except Exception as exc:
            self.output_queue.put(("api_error", f"API key test failed: {exc}"))

    def load_jobs(self):
        selected_batch_id = self.selected_batch_id()
        self.jobs_tree.delete(*self.jobs_tree.get_children())

        jobs = []
        if JOBS_PATH.exists():
            try:
                jobs = json.loads(JOBS_PATH.read_text(encoding="utf-8")).get("jobs", [])
            except json.JSONDecodeError as exc:
                self.log(f"Could not read {JOBS_PATH}: {exc}\n")

        waiting = 0
        for index, job in enumerate(jobs):
            batch_id = job.get("batch_id", "")
            workflow = job.get("workflow_status", "")
            if workflow == "waiting":
                waiting += 1
            item_id = batch_id or f"job-{index}"
            item = self.jobs_tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    job.get("series_id", ""),
                    batch_id,
                    workflow,
                    job.get("openai_status", ""),
                    job.get("output_file_id", ""),
                ),
            )
            if selected_batch_id and selected_batch_id == batch_id:
                self.jobs_tree.selection_set(item)

        self.status_var.set(f"{len(jobs)} tracked job(s), {waiting} waiting")

    def selected_batch_id(self):
        selection = self.jobs_tree.selection()
        if not selection:
            return None
        values = self.jobs_tree.item(selection[0], "values")
        return values[1] if len(values) > 1 else None

    def selected_series_id(self):
        selection = self.jobs_tree.selection()
        if not selection:
            return None
        values = self.jobs_tree.item(selection[0], "values")
        return values[0] if values else None

    def run_setup_script(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Enter a Syosetsu URL first.")
            return

        cmd = [sys.executable, "-u", str(SCRIPT_DIR / "setup_syosetu_series.py"), url]
        name = self.name_var.get().strip()
        if name:
            cmd.extend(["--name", name])
        cmd.extend(["--model", self.model_var.get()])
        if self.skip_existing_var.get():
            cmd.append("--skip-existing")
        if self.submit_batch_var.get():
            cmd.append("--submit-openai-batch")

        self.run_command(cmd, "Running setup script")

    def run_finalize_all(self):
        cmd = [sys.executable, "-u", str(SCRIPT_DIR / "finalize_openai_batch.py"), "--all"]
        if self.fix_lines_var.get():
            cmd.append("--fix-line-counts")
        self.run_command(cmd, "Checking all waiting jobs")

    def run_finalize_selected(self):
        series_id = self.selected_series_id()
        if not series_id:
            messagebox.showwarning("No job selected", "Select a job first.")
            return

        cmd = [sys.executable, "-u", str(SCRIPT_DIR / "finalize_openai_batch.py"), series_id]
        if self.fix_lines_var.get():
            cmd.append("--fix-line-counts")
        self.run_command(cmd, f"Checking {series_id}")

    def run_command(self, cmd, status):
        if self.running:
            messagebox.showinfo("Busy", "A script is already running.")
            return

        self.running = True
        self.set_buttons_enabled(False)
        self.status_var.set(status)
        self.log(f"\n> {' '.join(cmd)}\n")

        thread = threading.Thread(target=self.worker, args=(cmd,), daemon=True)
        thread.start()

    def worker(self, cmd):
        try:
            process = subprocess.Popen(
                cmd,
                cwd=ROOT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if process.stdout:
                for line in process.stdout:
                    self.output_queue.put(("line", line))
            return_code = process.wait()
            self.output_queue.put(("done", return_code))
        except Exception as exc:
            self.output_queue.put(("error", str(exc)))

    def drain_output_queue(self):
        try:
            while True:
                kind, payload = self.output_queue.get_nowait()
                if kind == "line":
                    self.log(payload)
                elif kind == "done":
                    self.running = False
                    self.set_buttons_enabled(True)
                    self.load_jobs()
                    self.status_var.set("Ready" if payload == 0 else f"Script exited with code {payload}")
                    self.log(f"\n[exit code {payload}]\n")
                elif kind == "error":
                    self.running = False
                    self.set_buttons_enabled(True)
                    self.load_jobs()
                    self.status_var.set("Error")
                    self.log(f"\nError: {payload}\n")
                elif kind == "api_ok":
                    self.set_api_status(payload, "#207a3a")
                    self.log("OpenAI API key test succeeded.\n")
                elif kind == "api_error":
                    self.set_api_status("API key: failed", "#7a1f1f")
                    self.log(f"{payload}\n")
        except queue.Empty:
            pass

        self.after(100, self.drain_output_queue)

    def set_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for button in (
            self.save_api_button,
            self.test_api_button,
            self.save_test_api_button,
            self.run_setup_button,
            self.reload_button,
            self.refresh_button,
            self.finalize_selected_button,
        ):
            button.configure(state=state)

    def log(self, text):
        self.output.insert("end", text)
        self.output.see("end")


def main():
    app = BatchUi()
    app.mainloop()


if __name__ == "__main__":
    main()
