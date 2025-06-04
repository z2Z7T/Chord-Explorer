import tkinter as tk
from tkinter import ttk, simpledialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import sounddevice as sd
import threading
import time
import sys # For platform check for scroll wheel binding

# --- Theme Colors (Discord-like) ---
# ... (colors remain the same)
BG_PRIMARY = "#36393F"
BG_SECONDARY = "#2F3136"
BG_TERTIARY = "#202225"
WIDGET_BG = "#40444B"
TEXT_PRIMARY = "#FFFFFF"
TEXT_SECONDARY = "#B9BBBE"
ACCENT_COLOR = "#7289DA"
ACCENT_HOVER = "#677BC4"
BUTTON_TEXT = "#FFFFFF"
BORDER_COLOR = "#202225"
SUCCESS_COLOR = "#43B581"
WARNING_COLOR = "#FAA61A"
DANGER_COLOR = "#F04747"
PLOT_GRID_COLOR = "#4A4E54"
PLOT_AXIS_COLOR = TEXT_SECONDARY
WAVE_COLORS = ['#58A6FF', '#3FB950', '#F4D03F', '#F06292', '#4DD0E1', '#FF8A65', '#BA68C8']
PIANO_WHITE_KEY_BG = "#FFFFFF"
PIANO_WHITE_KEY_FG = "#000000"
PIANO_WHITE_KEY_ACTIVE_BG = "#E0E0E0"
PIANO_BLACK_KEY_BG = "#333333"
PIANO_BLACK_KEY_FG = "#FFFFFF"
PIANO_BLACK_KEY_ACTIVE_BG = "#555555"

class ScrollableEntry(ttk.Entry):
    # ... (ScrollableEntry class remains the same as your last version)
    def __init__(self, master=None, variable=None, min_val=-float('inf'), max_val=float('inf'), sensitivity=0.1, is_int=False, **kwargs):
        super().__init__(master, textvariable=variable, **kwargs)
        self.variable = variable
        self.min_val = min_val
        self.max_val = max_val
        self.sensitivity = sensitivity
        self.is_int = is_int

        self.bind("<MouseWheel>", self._on_scroll)
        if sys.platform == "darwin":
            self.bind("<Button-4>", lambda e: self._on_scroll(e, direction=-1))
            self.bind("<Button-5>", lambda e: self._on_scroll(e, direction=1))
        self.config(cursor="xterm")

    def _on_scroll(self, event, direction=None):
        if self.focus_get() != self:
            return

        if direction is None:
            delta = -1 if event.delta > 0 else 1
        else:
            delta = direction

        try:
            current_value = float(self.variable.get())
        except ValueError:
            current_value = 0

        scroll_step = self.sensitivity
        if self.is_int:
             scroll_step = max(1, round(self.sensitivity * 5 if self.sensitivity <= 0.2 else self.sensitivity))
        else:
            scroll_step = self.sensitivity / 2.0 if self.sensitivity > 0.01 else 0.01

        new_value = current_value + delta * scroll_step

        if self.is_int:
            new_value = round(new_value)
        else:
            if scroll_step < 1:
                precision = max(2, -int(np.floor(np.log10(scroll_step)))) if scroll_step > 0 else 2
                new_value = round(new_value, precision)
            else:
                 new_value = round(new_value, 2)

        new_value = max(self.min_val, min(self.max_val, new_value))
        self.variable.set(str(new_value if not self.is_int else int(new_value)))
        return "break"

class SineWaveComparator:
    def __init__(self, master):
        self.master = master
        master.title("Sine Wave Harmony Explorer")
        master.configure(bg=BG_PRIMARY)
        master.geometry("1200x950")

        self.sine_waves = []
        self.next_color_index = 0
        self.A4_FREQ = 440.0

        # --- TTK Styling ---
        self.style = ttk.Style()
        self.style.theme_use('clam')
        # ... (Styling definitions remain the same)
        self.style.configure('.', background=BG_PRIMARY, foreground=TEXT_PRIMARY, fieldbackground=WIDGET_BG, bordercolor=BORDER_COLOR)
        self.style.map('.', background=[('active', BG_SECONDARY)])
        self.style.configure("TFrame", background=BG_PRIMARY)
        self.style.configure("TLabel", background=BG_PRIMARY, foreground=TEXT_SECONDARY, font=('Segoe UI', 10))
        self.style.configure("Header.TLabel", font=('Segoe UI', 12, 'bold'), foreground=TEXT_PRIMARY)
        self.style.configure("TButton", background=ACCENT_COLOR, foreground=BUTTON_TEXT, font=('Segoe UI', 10, 'bold'), borderwidth=0, focusthickness=0, padding=6)
        self.style.map("TButton", background=[('active', ACCENT_HOVER), ('pressed', ACCENT_HOVER)], relief=[('pressed', 'sunken'), ('!pressed', 'raised')])
        self.style.configure("Remove.TButton", background=DANGER_COLOR)
        self.style.map("Remove.TButton", background=[('active', '#C0392B')])
        self.style.configure("TEntry", fieldbackground=WIDGET_BG, foreground=TEXT_PRIMARY, insertcolor=TEXT_PRIMARY, bordercolor=BORDER_COLOR, lightcolor=WIDGET_BG, darkcolor=WIDGET_BG, padding=4)
        self.style.configure("TScrollbar", background=WIDGET_BG, troughcolor=BG_SECONDARY, bordercolor=WIDGET_BG, arrowcolor=TEXT_PRIMARY)
        self.style.map("TScrollbar", background=[('active', ACCENT_COLOR)])
        self.style.configure("WhiteKey.TButton", background=PIANO_WHITE_KEY_BG, foreground=PIANO_WHITE_KEY_FG, font=('Segoe UI', 9), borderwidth=1, relief="raised", padding=0)
        self.style.map("WhiteKey.TButton", background=[('active', PIANO_WHITE_KEY_ACTIVE_BG), ('pressed', PIANO_WHITE_KEY_ACTIVE_BG)])
        self.style.configure("BlackKey.TButton", background=PIANO_BLACK_KEY_BG, foreground=PIANO_BLACK_KEY_FG, font=('Segoe UI', 8), borderwidth=1, relief="raised", padding=0)
        self.style.map("BlackKey.TButton", background=[('active', PIANO_BLACK_KEY_ACTIVE_BG), ('pressed', PIANO_BLACK_KEY_ACTIVE_BG)])

        # --- Main Layout Frames ---
        # ... (Layout frames setup remains the same) ...
        self.top_controls_frame = ttk.Frame(master, style="TFrame")
        self.top_controls_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10,0))
        self.general_settings_frame = ttk.Frame(self.top_controls_frame, style="TFrame", padding=10)
        self.general_settings_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0,5), anchor='n')
        self.wave_management_frame = ttk.Frame(self.top_controls_frame, style="TFrame", padding=10)
        self.wave_management_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.piano_frame = ttk.Frame(master, style="TFrame", height=120)
        self.piano_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        self.piano_frame.pack_propagate(False)
        self._create_piano_keyboard()
        self.plot_area_frame = ttk.Frame(master, style="TFrame")
        self.plot_area_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.bottom_controls_frame = ttk.Frame(master, style="TFrame", padding=10)
        self.bottom_controls_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0,10))

        # --- Plotting Setup ---
        # ... (Plot setup remains the same) ...
        self.fig, self.ax = plt.subplots()
        self.fig.patch.set_facecolor(BG_TERTIARY)
        self.ax.set_facecolor(BG_TERTIARY)
        self.ax.spines['bottom'].set_color(PLOT_AXIS_COLOR)
        self.ax.spines['top'].set_color(PLOT_AXIS_COLOR)
        self.ax.spines['left'].set_color(PLOT_AXIS_COLOR)
        self.ax.spines['right'].set_color(PLOT_AXIS_COLOR)
        self.ax.tick_params(axis='x', colors=TEXT_SECONDARY)
        self.ax.tick_params(axis='y', colors=TEXT_SECONDARY)
        self.ax.title.set_color(TEXT_PRIMARY)
        self.ax.xaxis.label.set_color(TEXT_SECONDARY)
        self.ax.yaxis.label.set_color(TEXT_SECONDARY)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_area_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.configure(bg=BG_TERTIARY)
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        # --- General Plot Settings ---
        # ... (Distance and Start Point entries remain the same, with traces) ...
        ttk.Label(self.general_settings_frame, text="Plot Settings", style="Header.TLabel").pack(pady=(0,10), anchor='w')
        ttk.Label(self.general_settings_frame, text="Graph Distance (X-axis):").pack(pady=(5,0), anchor='w')
        self.distance_var = tk.StringVar(value="0.02") # Shorter default distance
        self.distance_var.trace_add("write", self._trigger_plot_update_from_trace)
        self.distance_entry = ScrollableEntry(self.general_settings_frame, variable=self.distance_var, min_val=0.001, max_val=10.0, sensitivity=0.01, width=10, style="TEntry")
        self.distance_entry.pack(fill=tk.X, pady=(0,5))
        ttk.Label(self.general_settings_frame, text="Graph Start Point:").pack(pady=(5,0), anchor='w')
        self.start_point_var = tk.StringVar(value="0.0")
        self.start_point_var.trace_add("write", self._trigger_plot_update_from_trace)
        self.start_point_entry = ScrollableEntry(self.general_settings_frame, variable=self.start_point_var, min_val=-1000.0, max_val=1000.0, sensitivity=0.1, width=10, style="TEntry")
        self.start_point_entry.pack(fill=tk.X, pady=(0,10))

        # --- Sine Wave Controls ---
        # ... (Wave management setup remains the same) ...
        wave_header_frame = ttk.Frame(self.wave_management_frame)
        wave_header_frame.pack(fill=tk.X, pady=(0,5))
        ttk.Label(wave_header_frame, text="Sine Waves", style="Header.TLabel").pack(side=tk.LEFT, anchor='w')
        self.add_wave_button = ttk.Button(wave_header_frame, text="+ Add Freq", command=self.add_sine_wave_dialog, style="TButton")
        self.add_wave_button.pack(side=tk.RIGHT, padx=(0,0))
        self.wave_controls_outer_canvas = tk.Canvas(self.wave_management_frame, borderwidth=0, background=BG_SECONDARY, highlightthickness=0)
        self.wave_controls_scrollbar = ttk.Scrollbar(self.wave_management_frame, orient="vertical", command=self.wave_controls_outer_canvas.yview, style="TScrollbar")
        self.wave_controls_frame = ttk.Frame(self.wave_controls_outer_canvas, style="TFrame")
        self.wave_controls_outer_canvas.configure(yscrollcommand=self.wave_controls_scrollbar.set)
        self.wave_controls_outer_canvas.pack(side="left", fill="both", expand=True)
        self.wave_controls_scrollbar.pack(side="right", fill="y")
        self.wave_controls_canvas_window = self.wave_controls_outer_canvas.create_window((0, 0), window=self.wave_controls_frame, anchor="nw")
        def _configure_scroll_region(event): self.wave_controls_outer_canvas.configure(scrollregion=self.wave_controls_outer_canvas.bbox("all"))
        self.wave_controls_frame.bind("<Configure>", _configure_scroll_region)
        self.wave_controls_outer_canvas.bind("<Enter>", lambda e: self.wave_controls_outer_canvas.bind_all("<MouseWheel>", _on_mousewheel_canvas_specific))
        self.wave_controls_outer_canvas.bind("<Leave>", lambda e: self.wave_controls_outer_canvas.unbind_all("<MouseWheel>"))
        if sys.platform == "darwin":
            self.wave_controls_outer_canvas.bind("<Enter>", lambda e: self.wave_controls_outer_canvas.bind_all("<Button-4>", _on_mousewheel_canvas_specific), add="+")
            self.wave_controls_outer_canvas.bind("<Enter>", lambda e: self.wave_controls_outer_canvas.bind_all("<Button-5>", _on_mousewheel_canvas_specific), add="+")
            self.wave_controls_outer_canvas.bind("<Leave>", lambda e: self.wave_controls_outer_canvas.unbind_all("<Button-4>"), add="+")
            self.wave_controls_outer_canvas.bind("<Leave>", lambda e: self.wave_controls_outer_canvas.unbind_all("<Button-5>"), add="+")
        def _on_mousewheel_canvas_specific(event):
            if sys.platform == "darwin":
                if event.num == 4: self.wave_controls_outer_canvas.yview_scroll(-1, "units")
                elif event.num == 5: self.wave_controls_outer_canvas.yview_scroll(1, "units")
            else:
                self.wave_controls_outer_canvas.yview_scroll(int(-1*(event.delta/120)), "units")


        # --- Zero Crossing & Actions (Bottom) ---
        controls_bottom_frame = ttk.Frame(self.bottom_controls_frame)
        controls_bottom_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        zero_crossing_controls_frame = ttk.Frame(controls_bottom_frame)
        zero_crossing_controls_frame.pack(fill=tk.X, pady=(0,5))

        ttk.Label(zero_crossing_controls_frame, text="Y Axis Threashold (% Y):", anchor='w').pack(side=tk.LEFT, padx=(0,2))
        self.zero_crossing_tolerance_var = tk.StringVar(value="0.01") # Amplitude tolerance for defining a crossing
        self.zero_crossing_tolerance_var.trace_add("write", self._trigger_plot_update_from_trace)
        self.zero_crossing_tolerance_entry = ScrollableEntry(zero_crossing_controls_frame, variable=self.zero_crossing_tolerance_var, min_val=0.01, max_val=20.0, sensitivity=0.05, width=6, style="TEntry")
        self.zero_crossing_tolerance_entry.pack(side=tk.LEFT, padx=(0,10))

        # NEW Time Proximity Control
        ttk.Label(zero_crossing_controls_frame, text="X Axis Threashold (x0.0001s):", anchor='w').pack(side=tk.LEFT, padx=(0,2))
        self.zc_time_proximity_var = tk.StringVar(value="1") # Default: 10 * 0.0001s = 1ms
        self.zc_time_proximity_var.trace_add("write", self._trigger_plot_update_from_trace)
        self.zc_time_proximity_entry = ScrollableEntry(zero_crossing_controls_frame, variable=self.zc_time_proximity_var, min_val=0, max_val=1000, sensitivity=1, is_int=True, width=6, style="TEntry") # Integer input for simplicity
        self.zc_time_proximity_entry.pack(side=tk.LEFT, padx=(0,5))
        
        action_buttons_frame = ttk.Frame(self.bottom_controls_frame)
        action_buttons_frame.pack(side=tk.RIGHT, fill=tk.NONE)
        self.play_audio_button = ttk.Button(action_buttons_frame, text="🔊 Play Audio", command=self.play_audio, style="TButton")
        self.play_audio_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.audio_thread = None
        self.stop_audio_flag = False
        self.sample_rate = 44100

        master.after(100, self.update_plot_explicitly)

    def _trigger_plot_update_from_trace(self, *args):
            if self.master.winfo_exists():
                self.update_plot_explicitly()

    def _get_frequency_from_semitones(self, semitones_from_a4):
        return self.A4_FREQ * (2**(1/12))**semitones_from_a4

    def _on_piano_key_press(self, semitone_offset, note_name):
            target_freq = self._get_frequency_from_semitones(semitone_offset)
            rounded_target_freq = round(target_freq, 2) # Match the precision we store

            # Check if a wave with this specific note_name already exists
            wave_to_toggle = None
            for wave in self.sine_waves:
                if wave.get('note_name') == note_name:
                    # Secondary check for frequency in case of rounding issues during storage/retrieval
                    try:
                        current_freq_val = float(wave['freq_var'].get())
                        if abs(current_freq_val - rounded_target_freq) < 0.01: # Tolerance for float comparison
                            wave_to_toggle = wave
                            break
                    except ValueError:
                        continue # Skip if freq_var is not a valid float

            if wave_to_toggle:
                print(f"Piano key {note_name} pressed, removing existing wave (ID: {wave_to_toggle['id']}).")
                self.remove_wave(wave_to_toggle['id']) # remove_wave will call update_plot
            else:
                print(f"Piano key {note_name} pressed, Freq: {target_freq:.2f} Hz, adding new wave.")
                self.add_sine_wave_controls(initial_freq=rounded_target_freq, note_name=note_name)
                self.update_plot_explicitly() # add_sine_wave_controls doesn't call it

    def _create_piano_keyboard(self):
        # ... (Piano keyboard creation remains the same) ...
        piano_keys_data = [
            ("C4",  -9, "white", "C4"), ("C#4", -8, "black", "C#\nD♭"),
            ("D4",  -7, "white", "D4"), ("D#4", -6, "black", "D#\nE♭"),
            ("E4",  -5, "white", "E4"),
            ("F4",  -4, "white", "F4"), ("F#4", -3, "black", "F#\nG♭"),
            ("G4",  -2, "white", "G4"), ("G#4", -1, "black", "G#\nA♭"),
            ("A4",   0, "white", "A4"), ("A#4",  1, "black", "A#\nB♭"),
            ("B4",   2, "white", "B4"),
            ("C5",   3, "white", "C5")
        ]
        num_white_keys = sum(1 for k in piano_keys_data if k[2] == "white")
        white_key_relwidth = 1.0 / num_white_keys
        black_key_relwidth = white_key_relwidth * 0.65
        black_key_relheight = 0.6
        white_key_index = 0
        for _, (note_name, semitone_offset, key_type, display_label) in enumerate(piano_keys_data):
            if key_type == "white":
                key_button = ttk.Button(self.piano_frame, text=display_label, style="WhiteKey.TButton",
                                        command=lambda off=semitone_offset, nn=note_name: self._on_piano_key_press(off, nn))
                key_button.place(relx=white_key_index * white_key_relwidth, rely=0,
                                 relwidth=white_key_relwidth, relheight=1.0)
                white_key_index += 1
        white_key_index = 0 
        last_white_key_x = 0
        for _, (note_name, semitone_offset, key_type, display_label) in enumerate(piano_keys_data):
            if key_type == "white":
                last_white_key_x = white_key_index * white_key_relwidth
                white_key_index += 1
            elif key_type == "black":
                key_button = ttk.Button(self.piano_frame, text=display_label, style="BlackKey.TButton",
                                        command=lambda off=semitone_offset, nn=note_name: self._on_piano_key_press(off, nn))
                key_button.place(relx=last_white_key_x + white_key_relwidth - (black_key_relwidth / 2) , rely=0,
                                 relwidth=black_key_relwidth, relheight=black_key_relheight)

    def get_next_color(self):
        color = WAVE_COLORS[self.next_color_index % len(WAVE_COLORS)]
        self.next_color_index += 1
        return color

    def add_sine_wave_dialog(self):
        freq = simpledialog.askfloat("New Sine Wave", "Enter frequency (Hz):",
                                     parent=self.master, minvalue=0.01, initialvalue=self.A4_FREQ)
        if freq is not None:
            self.add_sine_wave_controls(initial_freq=freq)
            self.update_plot_explicitly()

    def add_sine_wave_controls(self, initial_freq=1.0, note_name=None):
        wave_id = len(self.sine_waves) # Assign ID before potential modification by other threads if any
        color = self.get_next_color()
        
        # Create a unique ID for the wave if managing concurrent additions is a concern
        # For now, simple length-based ID is fine for single-threaded GUI ops
        
        wave_frame = ttk.Frame(self.wave_controls_frame, padding=(8,5))
        wave_frame.pack(fill=tk.X, pady=2)
        
        freq_var = tk.StringVar(value=f"{initial_freq:.2f}")
        # ADD TRACE for real-time frequency updates
        freq_var.trace_add("write", lambda name, index, mode, var=freq_var, w_id=wave_id: self._handle_freq_var_change(var, w_id))
        freq_var.trace_add("write", self._trigger_plot_update_from_trace)
        
        amp_var = tk.DoubleVar(value=1.0) 
        phase_var = tk.DoubleVar(value=0.0)
        
        color_label = tk.Label(wave_frame, text="●", fg=color, bg=BG_SECONDARY, font=('Arial', 14, 'bold'))
        color_label.grid(row=0, column=0, padx=(0,5), sticky='w')
        
        # The label can show the initial note/source, frequency entry is live
        base_display_name = f"{note_name}" if note_name else "Manual"
        
        # Label to show the base note/type
        ttk.Label(wave_frame, text=base_display_name, style="TLabel", background=BG_SECONDARY).grid(row=0, column=1, sticky='w', padx=(0,5))

        # Frequency entry is NOW EDITABLE
        freq_entry = ScrollableEntry(wave_frame, variable=freq_var, min_val=0.01, max_val=20000.0, sensitivity=0.5, width=8, style="TEntry") # Sensitivity tuned for Hz
        # freq_entry.config(state='readonly') # REMOVE THIS to make it editable
        freq_entry.grid(row=0, column=2, padx=(0,5), sticky='ew') 

        # Add "Hz" unit label next to the entry
        ttk.Label(wave_frame, text="Hz", style="TLabel", background=BG_SECONDARY).grid(row=0, column=3, sticky='w', padx=(0,5))

        remove_button = ttk.Button(wave_frame, text="✕", width=2, command=lambda w_id_to_remove=wave_id: self.remove_wave(w_id_to_remove), style="Remove.TButton")
        remove_button.grid(row=0, column=4, sticky='e', padx=5)
        
        wave_frame.columnconfigure(2, weight=1) # Allow frequency entry to expand a bit
        
        wave_data = {'id': wave_id, 'frame': wave_frame, 'freq_var': freq_var,
                     'amp_var': amp_var, 'phase_var': phase_var, 'color': color,
                     'y_data': None, 'note_name': note_name, 
                     'base_freq_for_display': initial_freq} # Store original freq for display if needed
        self.sine_waves.append(wave_data)
        
        # Ensure wave_id is correctly captured if list is modified elsewhere (should be fine here)
        # Need to re-map IDs if waves are removed and strict 0..N-1 indexing is desired for other logic
        # For now, wave_id assigned at creation is used for removal.

        self.wave_controls_frame.update_idletasks()
        self.wave_controls_outer_canvas.config(scrollregion=self.wave_controls_outer_canvas.bbox("all"))
        # self.update_plot_explicitly() # Called by the function that calls this, or by trace


    def remove_wave(self, wave_id_to_remove):
        # ... (remove_wave remains the same) ...
        wave_to_remove = next((w for w in self.sine_waves if w['id'] == wave_id_to_remove), None)
        if wave_to_remove:
            wave_to_remove['frame'].destroy()
            self.sine_waves.remove(wave_to_remove)
            self.update_plot_explicitly()
        self.wave_controls_frame.update_idletasks()
        self.wave_controls_outer_canvas.config(scrollregion=self.wave_controls_outer_canvas.bbox("all"))


    def update_plot_explicitly(self):
        # ... (update_plot_explicitly remains largely the same, num_points already increased) ...
        if not self.master.winfo_exists(): return

        if not self.sine_waves:
            self.ax.clear()
            self.ax.set_title("Add a sine wave to begin", color=TEXT_PRIMARY)
            self.ax.set_xlabel("Time (s)", color=TEXT_SECONDARY)
            self.ax.set_ylabel("Amplitude", color=TEXT_SECONDARY)
            self.ax.set_facecolor(BG_TERTIARY)
            self.ax.grid(True, color=PLOT_GRID_COLOR, linestyle=':', linewidth=0.5)
            self.canvas.draw_idle() 
            return

        try:
            self.current_plot_start_time = float(self.start_point_var.get())
            distance = float(self.distance_var.get())
            if distance <= 0: distance = 0.001 # Ensure positive distance
        except ValueError:
            self.start_point_var.set("0.0")
            self.distance_var.set("0.1")
            self.current_plot_start_time = 0.0
            distance = 0.1

        self.current_plot_end_time = self.current_plot_start_time + distance
        
        num_points = max(1000, int(distance * 5000)) # Higher resolution for accurate zero-crossing
        if distance < 0.01: # Very short distances might need even more points relative to distance
            num_points = max(500, int(distance * 20000))
        if num_points <= 1: num_points = 2 

        self.x_data = np.linspace(self.current_plot_start_time, self.current_plot_end_time, num_points, endpoint=False)
        self.ax.clear()
        max_amp_sum = 0

        for wave in self.sine_waves:
            try:
                freq = float(wave['freq_var'].get())
                if freq <=0: freq = 0.01 
            except ValueError: freq = 1.0 
            amp = wave['amp_var'].get()
            phase = wave['phase_var'].get() 
            wave['y_data'] = amp * np.sin(2 * np.pi * freq * self.x_data + phase)
            self.ax.plot(self.x_data, wave['y_data'], color=wave['color'], linewidth=1.5) 
            max_amp_sum += amp
        
        current_max_amp = max(1.0, max_amp_sum if max_amp_sum > 0 else 1.0)
        self.ax.set_ylim(-current_max_amp * 1.2, current_max_amp * 1.2)
        self.ax.set_xlabel("Time (s)", color=TEXT_SECONDARY)
        self.ax.set_ylabel("Amplitude", color=TEXT_SECONDARY)
        self.ax.set_title("Sine Wave Harmony Explorer", color=TEXT_PRIMARY)
        self.ax.grid(True, color=PLOT_GRID_COLOR, linestyle=':', linewidth=0.5)
        self.ax.axhline(0, color=PLOT_AXIS_COLOR, lw=0.7)

        self.plot_zero_crossings()
        self.canvas.draw_idle()

    def plot_zero_crossings(self):
        if len(self.sine_waves) < 2 or not hasattr(self, 'x_data') or self.x_data is None or len(self.x_data) < 2:
            return
        
        if not hasattr(self, 'current_plot_start_time') or not hasattr(self, 'current_plot_end_time'):
            if hasattr(self, 'x_data') and len(self.x_data) > 0:
                plot_start_time = self.x_data[0]
                plot_end_time = self.x_data[-1]
            else: return 
        else:
            plot_start_time = self.current_plot_start_time
            plot_end_time = self.current_plot_end_time

        try:
            amp_tol_percent = float(self.zero_crossing_tolerance_var.get())
            # Convert "X ten-thousandths of a second" to seconds
            time_proximity_setting = float(self.zc_time_proximity_var.get())
            time_grouping_tolerance = time_proximity_setting * 0.0001
            if time_grouping_tolerance < 0: time_grouping_tolerance = 0 # Must be non-negative
        except ValueError:
            return 

        current_ylim = self.ax.get_ylim()
        y_range = current_ylim[1] - current_ylim[0]
        if abs(y_range) < 1e-9: y_range = 2.0 # Avoid division by zero if plot is flat
        amplitude_tolerance = (y_range * (amp_tol_percent / 100.0)) / 2.0
        if amplitude_tolerance < 1e-9 : amplitude_tolerance = 1e-9 # Ensure a minimum tolerance


        all_individual_crossings = [] # List of (time, wave_index)

        for wave_idx, wave in enumerate(self.sine_waves):
            if wave['y_data'] is None or len(wave['y_data']) < 2:
                continue
            
            y_values = wave['y_data']
            x_times = self.x_data
            
            # Find where product of adjacent y_values is non-positive (means sign change or one is zero)
            cross_indices = np.where(y_values[:-1] * y_values[1:] <= 0)[0]

            for idx in cross_indices:
                y1, y2 = y_values[idx], y_values[idx+1]
                x1, x2 = x_times[idx], x_times[idx+1]

                # Perform linear interpolation to find the crossing time
                # x_cross = x1 - y1 * (x2 - x1) / (y2 - y1)
                if abs(y2 - y1) > 1e-9: # Avoid division by zero if y1 and y2 are almost equal
                    t_cross = x1 - y1 * (x2 - x1) / (y2 - y1)
                elif abs(y1) < amplitude_tolerance : # y1 is already at/near zero
                    t_cross = x1
                elif abs(y2) < amplitude_tolerance : # y2 is at/near zero
                    t_cross = x2
                else: # Both y1, y2 are same and non-zero, but y1*y2<=0 means both are effectively zero
                      # This case should ideally be caught by abs(y1) < tol, but as a fallback:
                    t_cross = (x1 + x2) / 2.0 

                # Ensure the crossing is within the current plot view and that its amplitude is indeed near zero
                # The interpolation itself finds where it *would* be zero.
                # The amplitude_tolerance check is more about how "flat" a crossing is allowed to be.
                # For now, we trust the sign change and interpolation.
                if plot_start_time <= t_cross <= plot_end_time:
                    # Check if one of the points defining the crossing is within amplitude_tolerance of zero
                    # This helps filter out crossings that are numerically found but might be very "shallow"
                    # if the amplitude_tolerance is very small. The primary check is the sign change.
                    # if abs(y1) < amplitude_tolerance or abs(y2) < amplitude_tolerance or abs(y1*y2) < 1e-9: # one point is close or product is zero
                    all_individual_crossings.append((t_cross, wave_idx))


        if not all_individual_crossings:
            return

        all_individual_crossings.sort() # Sort by time, crucial for grouping

        # Group sorted crossings
        final_groups = []
        if not all_individual_crossings: return

        processed_up_to_idx = -1 # To skip already grouped items efficiently

        for i in range(len(all_individual_crossings)):
            if i <= processed_up_to_idx:
                continue

            group_candidate = [all_individual_crossings[i]]
            group_start_time = all_individual_crossings[i][0]
            
            current_max_idx_in_this_group = i

            for j in range(i + 1, len(all_individual_crossings)):
                next_crossing_time = all_individual_crossings[j][0]
                
                if (next_crossing_time - group_start_time) <= time_grouping_tolerance:
                    group_candidate.append(all_individual_crossings[j])
                    current_max_idx_in_this_group = j
                else:
                    # This crossing is too far to be part of the current group started at group_start_time.
                    break 
            
            final_groups.append(group_candidate)
            processed_up_to_idx = current_max_idx_in_this_group


        # Plot bars for groups with >= 2 unique waves
        plotted_bar_avg_times = set() # To prevent overplotting nearly identical group averages

        for group in final_groups:
            unique_waves_in_group = set(wave_idx for _, wave_idx in group)

            if len(unique_waves_in_group) >= 2: # Condition: At least two different waves
                avg_time = np.mean([t for t, _ in group])
                
                # Check if a bar for a very similar group average time has already been plotted
                is_too_close_to_plotted = False
                # Use a slightly larger tolerance for merging displayed bars than for grouping initial events
                display_merge_tolerance = max(time_grouping_tolerance * 0.5, (self.x_data[1]-self.x_data[0]) if len(self.x_data)>1 else 0.0001)

                for plotted_t in plotted_bar_avg_times:
                    if abs(avg_time - plotted_t) < display_merge_tolerance:
                        is_too_close_to_plotted = True
                        break
                
                if is_too_close_to_plotted:
                    continue
                
                plotted_bar_avg_times.add(avg_time)

                percentage_crossing = (len(unique_waves_in_group) / len(self.sine_waves)) * 100
                
                bar_height_normalized = percentage_crossing / 100.0
                ymin, ymax = self.ax.get_ylim()
                bar_actual_height = bar_height_normalized * (ymax - ymin) * 0.9
                bar_bottom = ymin + (ymax - ymin) * 0.05
                
                # Bar width could be a small fraction of the time_grouping_tolerance or a fixed small screen fraction
                bar_width = max((self.x_data[-1] - self.x_data[0]) * 0.0015, time_grouping_tolerance * 0.2)
                if bar_width <=0 : bar_width = (self.x_data[-1] - self.x_data[0]) * 0.001 # Fallback if time_grouping_tolerance is 0


                self.ax.bar(avg_time, bar_actual_height, width=bar_width, bottom=bar_bottom,
                            color=SUCCESS_COLOR, alpha=0.7, edgecolor=TEXT_PRIMARY, linewidth=0.5)
                self.ax.text(avg_time, bar_bottom + bar_actual_height + 0.01 * abs(ymax-ymin) , f'{percentage_crossing:.0f}%',
                             ha='center', va='bottom', fontsize=7, color=TEXT_PRIMARY)

    def play_audio(self):
        # ... (play_audio remains the same) ...
        if self.audio_thread and self.audio_thread.is_alive():
            self.stop_audio_flag = True
            try: self.audio_thread.join(timeout=0.5)
            except RuntimeError: pass 
            self.play_audio_button.config(text="🔊 Play Audio")
            self.play_audio_button.configure(style="TButton")
            return

        if not self.sine_waves: return
        self.stop_audio_flag = False
        self.style.configure("StopButton.TButton", background=DANGER_COLOR, foreground=BUTTON_TEXT)
        self.style.map("StopButton.TButton", background=[('active', '#C0392B')])
        self.play_audio_button.config(text="⏹️ Stop Audio", style="StopButton.TButton")
        self.audio_thread = threading.Thread(target=self._generate_and_play_audio, daemon=True)
        self.audio_thread.start()

    def _generate_and_play_audio(self):
        # ... (_generate_and_play_audio remains the same) ...
        duration_s = 3.0
        t_audio = np.linspace(0, duration_s, int(self.sample_rate * duration_s), False)
        combined_wave = np.zeros_like(t_audio)
        active_waves_for_audio = 0
        for wave_data in self.sine_waves:
            try:
                freq = float(wave_data['freq_var'].get())
                if freq <= 0: continue 
            except ValueError: continue 
            amp = wave_data['amp_var'].get()
            phase = wave_data['phase_var'].get()
            combined_wave += amp * np.sin(2 * np.pi * freq * t_audio + phase)
            active_waves_for_audio +=1
        if active_waves_for_audio == 0:
            if hasattr(self.master, 'call'): self.master.after(0, self._reset_play_button)
            return
        max_abs_val = np.max(np.abs(combined_wave))
        if max_abs_val > 1.0: combined_wave /= max_abs_val
        elif max_abs_val == 0 and active_waves_for_audio > 0:
             print("Waves destructively interfered to silence.")
        stream = None
        try:
            stream = sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype=np.float32)
            stream.start()
            block_size = 1024 
            num_blocks = (len(combined_wave) + block_size -1) // block_size
            for i in range(num_blocks):
                if self.stop_audio_flag: break
                start = i * block_size
                end = min(start + block_size, len(combined_wave))
                if start < end: stream.write(combined_wave[start:end].astype(np.float32))
        except Exception as e: print(f"Error during audio playback: {e}")
        finally:
            if stream:
                try: stream.stop(); stream.close(ignore_errors=True)
                except Exception as e_close: print(f"Error closing audio stream: {e_close}")
            if hasattr(self.master, 'call'): self.master.after(0, self._reset_play_button)

    def _reset_play_button(self):
        # ... (_reset_play_button remains the same) ...
        self.play_audio_button.config(text="🔊 Play Audio")
        self.play_audio_button.configure(style="TButton") 
        self.stop_audio_flag = False


def main():
    # ... (main and on_closing remain the same) ...
    root = tk.Tk()
    app = SineWaveComparator(root)
    def on_closing():
        print("Closing application...")
        if app.audio_thread and app.audio_thread.is_alive():
            print("Stopping audio on close...")
            app.stop_audio_flag = True
            try: app.audio_thread.join(timeout=0.2) 
            except RuntimeError: pass 
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == '__main__':
    main()
