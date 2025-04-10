import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import os
import sys
import shutil
import signal
import json  # Usaremos JSON para facilitar futuras expansiones

# --- Configuración Global ---
YT_DLP_PATH = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
CONFIG_FILE_PATH = os.path.join(os.path.expanduser("~"), ".yt_dlp_gui_config.json")


# --- Clase de la Aplicación ---
class YtDlpApp:
    def __init__(self, root_window):
        """Inicializa la aplicación GUI."""
        self.root = root_window
        self.root.title("Interfaz Gráfica para yt-dlp (Clase)")
        # Ajustar geometría si es necesario por los botones
        self.root.geometry("700x650")

        self.download_thread = None
        self.current_process = None

        # Llama a los métodos en el orden correcto
        self._initialize_variables()
        self._create_widgets()  # <-- Este se llamaba pero faltaba definirlo
        self._layout_widgets()  # <-- Este se llamaba pero faltaba definirlo
        self._initial_setup()  # <-- Este se llamaba pero faltaba definirlo

    def _load_last_folder(self):
        """Intenta cargar la última carpeta usada desde el archivo de config."""
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                last_folder = config_data.get("last_folder")
                if last_folder and os.path.isdir(last_folder):
                    return last_folder
        except FileNotFoundError:
            pass  # No es un error si no existe
        except (json.JSONDecodeError, KeyError, TypeError, Exception) as e:
            print(
                f"Advertencia: No se pudo cargar la configuración desde {CONFIG_FILE_PATH}: {e}"
            )
        return None

    def _save_last_folder(self, folder_path):
        """Guarda la carpeta dada en el archivo de configuración."""
        config_data = {"last_folder": folder_path}
        try:
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(
                f"Advertencia: No se pudo guardar la configuración en {CONFIG_FILE_PATH}: {e}"
            )

    def _initialize_variables(self):
        """Inicializa las variables de control de Tkinter."""
        self.url_var = tk.StringVar()
        last_used_folder = self._load_last_folder()
        if last_used_folder:
            default_dest = last_used_folder
        else:
            home_dir = os.path.expanduser("~")
            videos_dir_en = os.path.join(home_dir, "Videos")
            videos_dir_es = os.path.join(home_dir, "Vídeos")
            default_dest = home_dir
            if os.path.isdir(videos_dir_en):
                default_dest = videos_dir_en
            elif os.path.isdir(videos_dir_es):
                default_dest = videos_dir_es
        self.destination_var = tk.StringVar(value=default_dest)
        self.audio_only_var = tk.BooleanVar()
        self.audio_format_var = tk.StringVar(value="best")
        self.video_format_var = tk.StringVar(value="best")
        self.subs_var = tk.BooleanVar()
        self.auto_subs_var = tk.BooleanVar()

    # --- MÉTODO RESTAURADO ---
    def _create_widgets(self):
        """Crea todos los widgets de la interfaz."""
        # --- Frames ---
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.url_frame = ttk.LabelFrame(
            self.main_frame, text="URL del Video", padding="10"
        )
        self.dest_frame = ttk.LabelFrame(self.main_frame, text="Destino", padding="10")
        self.options_frame = ttk.LabelFrame(
            self.main_frame, text="Opciones de Descarga", padding="10"
        )
        self.action_frame = ttk.Frame(self.main_frame, padding="10")
        self.progress_frame = ttk.Frame(self.main_frame, padding=(10, 0, 10, 10))
        self.output_frame = ttk.LabelFrame(
            self.main_frame, text="Salida de yt-dlp", padding="10"
        )

        # --- Sección URL ---
        self.url_label = ttk.Label(self.url_frame, text="URL:")
        self.url_entry = ttk.Entry(self.url_frame, textvariable=self.url_var, width=60)

        # --- Sección Destino ---
        self.dest_label = ttk.Label(self.dest_frame, text="Carpeta:")
        self.dest_entry = ttk.Entry(
            self.dest_frame, textvariable=self.destination_var, width=50
        )
        self.dest_button = ttk.Button(
            self.dest_frame,
            text="Seleccionar...",
            command=self.select_destination_folder,
        )

        # --- Sección Opciones ---
        # Fila 1
        self.row1_frame = ttk.Frame(self.options_frame)
        self.audio_only_check = ttk.Checkbutton(
            self.row1_frame, text="Sólo Audio", variable=self.audio_only_var
        )
        self.audio_format_label = ttk.Label(self.row1_frame, text="Formato Audio:")
        self.audio_format_combo = ttk.Combobox(
            self.row1_frame,
            textvariable=self.audio_format_var,
            values=["best", "mp3", "m4a", "opus", "wav", "flac"],
            width=8,
        )
        # Fila 2
        self.row2_frame = ttk.Frame(self.options_frame)
        self.video_format_label = ttk.Label(
            self.row2_frame, text="Formato Video/Contenedor:"
        )
        self.video_format_combo = ttk.Combobox(
            self.row2_frame,
            textvariable=self.video_format_var,
            values=["best", "bestvideo+bestaudio/best", "mp4", "webm"],
            width=25,
        )
        # Fila 3
        self.row3_frame = ttk.Frame(self.options_frame)
        self.subs_check = ttk.Checkbutton(
            self.row3_frame, text="Descargar Subtítulos", variable=self.subs_var
        )
        self.auto_subs_check = ttk.Checkbutton(
            self.row3_frame,
            text="Descargar Subs Automáticos",
            variable=self.auto_subs_var,
        )

        # --- Sección Botones de Acción ---
        self.download_button = ttk.Button(
            self.action_frame, text="Descargar", command=self.start_download_thread
        )
        self.stop_button = ttk.Button(
            self.action_frame,
            text="Detener",
            command=self.stop_download,
            state=tk.DISABLED,
        )

        # --- Sección Progreso ---
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, orient=tk.HORIZONTAL, length=300, mode="determinate"
        )

        # --- Sección Salida ---
        self.output_text = scrolledtext.ScrolledText(
            self.output_frame, wrap=tk.WORD, height=15, state="disabled"
        )

    # --- MÉTODO RESTAURADO ---
    def _layout_widgets(self):
        """Organiza los widgets en la ventana usando pack."""
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # URL
        self.url_frame.pack(fill=tk.X, pady=5)
        self.url_label.pack(side=tk.LEFT, padx=(0, 5))
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Destino
        self.dest_frame.pack(fill=tk.X, pady=5)
        self.dest_label.pack(side=tk.LEFT, padx=(0, 5))
        self.dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.dest_button.pack(side=tk.LEFT)

        # Opciones
        self.options_frame.pack(fill=tk.X, pady=5)
        self.row1_frame.pack(fill=tk.X, pady=2)
        self.audio_only_check.pack(side=tk.LEFT, padx=5)
        self.audio_format_label.pack(side=tk.LEFT, padx=(20, 5))
        self.audio_format_combo.pack(side=tk.LEFT)
        self.row2_frame.pack(fill=tk.X, pady=2)
        self.video_format_label.pack(side=tk.LEFT, padx=5)
        self.video_format_combo.pack(side=tk.LEFT, padx=5)
        self.row3_frame.pack(fill=tk.X, pady=2)
        self.subs_check.pack(side=tk.LEFT, padx=5)
        self.auto_subs_check.pack(side=tk.LEFT, padx=20)

        # Acciones
        self.action_frame.pack(fill=tk.X, pady=(5, 0))
        # Usar fill=tk.X en los botones dentro del action_frame para que se expandan
        self.download_button.pack(side=tk.LEFT, padx=(0, 5), fill=tk.X, expand=True)
        self.stop_button.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)

        # Progreso
        self.progress_frame.pack(fill=tk.X)
        self.progress_bar.pack(
            pady=5, fill=tk.X, padx=5
        )  # fill y padx para que ocupe ancho

        # Salida
        self.output_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        self.output_text.pack(fill=tk.BOTH, expand=True)

    # --- MÉTODO RESTAURADO ---
    def _initial_setup(self):
        """Realiza configuraciones iniciales como chequeos y foco."""
        if not self.check_yt_dlp():
            self.download_button.config(state=tk.DISABLED)
        # Asegurarse que url_entry existe antes de poner el foco
        if hasattr(self, "url_entry"):
            self.url_entry.focus_set()
        else:
            print("Advertencia: url_entry no encontrado durante _initial_setup.")

    def check_yt_dlp(self):
        """Verifica si yt-dlp está disponible."""
        if not YT_DLP_PATH:
            messagebox.showerror(
                "Error: yt-dlp no encontrado",
                "No se pudo encontrar el ejecutable 'yt-dlp'.\n"
                "Asegúrate de que esté instalado y en el PATH.",
                parent=self.root,
            )
            return False
        return True

    def select_destination_folder(self):
        """Abre diálogo para seleccionar carpeta, iniciando en la actual."""
        current_dir = self.destination_var.get()
        folder_selected = filedialog.askdirectory(
            parent=self.root,
            initialdir=current_dir,
            title="Seleccionar Carpeta de Destino",
        )
        if folder_selected:
            self.destination_var.set(folder_selected)

    def update_output(self, text):
        """Inserta texto en el widget de salida."""
        self.output_text.configure(state="normal")
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.configure(state="disabled")

    def run_yt_dlp(self, command_list, destination_path_used):
        """Ejecuta yt-dlp en un hilo separado."""
        self.current_process = None
        final_return_code = -999
        try:
            self.current_process = subprocess.Popen(
                command_list,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            while True:
                if not self.current_process or self.current_process.poll() is not None:
                    break
                output_line = self.current_process.stdout.readline()
                error_line = self.current_process.stderr.readline()
                if output_line:
                    self.root.after(0, self.update_output, output_line)
                if error_line:
                    self.root.after(0, self.update_output, f"ERROR: {error_line}")
                if (
                    self.current_process.poll() is not None
                    and not output_line
                    and not error_line
                ):
                    break

            final_return_code = self.current_process.wait()
            # Mensajes de finalización... (igual que antes)
            if final_return_code == 0:
                self.root.after(
                    0, self.update_output, "\n--- Descarga completada ---\n"
                )
            elif final_return_code < 0:
                self.root.after(
                    0,
                    self.update_output,
                    f"\n--- Proceso detenido ({final_return_code}) ---\n",
                )
            else:
                self.root.after(
                    0,
                    self.update_output,
                    f"\n--- Error en proceso ({final_return_code}) ---\n",
                )

        except FileNotFoundError:
            self.root.after(
                0,
                self.update_output,
                f"\nERROR: Ejecutable '{command_list[0]}' no encontrado.\n",
            )
            final_return_code = -100
        except Exception as e:
            self.root.after(0, self.update_output, f"\n--- Error inesperado: {e} ---\n")
            final_return_code = -101
        finally:
            self.current_process = None
            self.root.after(
                0,
                self._reset_ui_after_download,
                final_return_code,
                destination_path_used,
            )

    def _reset_ui_after_download(self, return_code, destination_path):
        """Resetea UI y guarda carpeta si éxito."""
        self.download_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_bar.stop()
        self.progress_bar.config(mode="determinate", value=0)
        if return_code == 0 and destination_path:
            self._save_last_folder(destination_path)

    def start_download_thread(self):
        """Prepara y lanza hilo de descarga."""
        if not self.check_yt_dlp():
            return
        url = self.url_var.get().strip()
        destination = self.destination_var.get().strip()
        if not url:
            messagebox.showwarning("Falta URL", "Ingresa una URL.", parent=self.root)
            return
        if not destination or not os.path.isdir(destination):
            messagebox.showwarning(
                "Destino Inválido", "Selecciona una carpeta válida.", parent=self.root
            )
            return
        if self.download_thread and self.download_thread.is_alive():
            messagebox.showwarning(
                "En Progreso", "Ya hay una descarga activa.", parent=self.root
            )
            return

        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", tk.END)
        self.output_text.configure(state="disabled")

        command = [YT_DLP_PATH]
        if self.audio_only_var.get():
            command.extend(["-x"])
            audio_format = self.audio_format_var.get()
            if audio_format != "best":
                command.extend(["--audio-format", audio_format])
            command.extend(["--audio-quality", "0"])
        else:
            video_format = self.video_format_var.get()
            if video_format != "best":
                command.extend(["-f", video_format])
            else:
                command.extend(
                    [
                        "-f",
                        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
                    ]
                )
        if self.subs_var.get():
            command.append("--write-sub")
        if self.auto_subs_var.get():
            command.append("--write-auto-sub")
        command.extend(["-P", destination])
        command.append(url)

        self.update_output(f"Ejecutando:\n{' '.join(command)}\n\n")
        self.download_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_bar.config(mode="indeterminate")
        self.progress_bar.start(10)

        self.download_thread = threading.Thread(
            target=self.run_yt_dlp, args=(command, destination), daemon=True
        )
        self.download_thread.start()

    def stop_download(self):
        """Intenta detener proceso actual."""
        if self.current_process and self.current_process.poll() is None:
            self.update_output("\n--- Intentando detener... ---\n")
            try:
                self.current_process.terminate()
                # Considerar self.current_process.kill() como fallback si terminate() no funciona rápido
            except Exception as e:
                self.update_output(f"\n--- Error al detener: {e} ---\n")
            self.stop_button.config(state=tk.DISABLED)  # Deshabilitar tras intento
        else:
            self.update_output("\n--- No hay proceso activo para detener ---\n")


# --- Punto de Entrada ---
if __name__ == "__main__":
    root = tk.Tk()
    app = YtDlpApp(root)
    # Opcional: Centrar ventana al inicio
    # root.eval('tk::PlaceWindow . center')
    root.mainloop()
