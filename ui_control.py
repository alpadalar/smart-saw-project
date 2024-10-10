import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import DateFormatter
import pandas as pd
from datetime import datetime, timedelta


class UIControl:
    def __init__(self, root, toggle_fuzzy_control_callback, plot_queue, start_camera_callback, stop_camera_callback):
        self.toggle_fuzzy_control_callback = toggle_fuzzy_control_callback
        self.plot_queue = plot_queue
        self.start_camera_callback = start_camera_callback
        self.stop_camera_callback = stop_camera_callback
        self.camera_running = False
        self.root = root
        self.root.title("Control Panel")

        self.status_label = tk.Label(root, text="Fuzzy Control: OFF")
        self.status_label.pack()

        self.toggle_button = tk.Button(root, text="Toggle Fuzzy Control", command=self.toggle_fuzzy_control)
        self.toggle_button.pack()

        self.camera_button = tk.Button(root, text="Start Camera", command=self.toggle_camera)
        self.camera_button.pack()

        self.figure, self.ax = plt.subplots(figsize=(5, 4))
        self.ax.set_title('Fuzzy Control Output')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Fuzzy Output')
        self.line, = self.ax.plot([], [], 'r-')
        self.ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        self.xdata = []
        self.ydata = []

        self.canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.table_frame = tk.Frame(root)
        self.table_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.table_columns = ["Descent Speed", "Cutting Speed", "Descent Current", "Cutting Current", "Torques",
                              "Band Deviation"]
        self.table_data = {col: tk.StringVar() for col in self.table_columns}

        self.table = tk.Frame(self.table_frame)
        for i, col in enumerate(self.table_columns):
            tk.Label(self.table, text=col).grid(row=0, column=i)
            tk.Label(self.table, textvariable=self.table_data[col]).grid(row=1, column=i)

        self.table.pack()

        self.update_plot()
        self.update_table()

    def toggle_fuzzy_control(self):
        fuzzy_enabled = self.toggle_fuzzy_control_callback()
        if fuzzy_enabled:
            self.status_label.config(text="Fuzzy Control: ON")
        else:
            self.status_label.config(text="Fuzzy Control: OFF")
        print(f"Fuzzy Control Toggled: {'ON' if fuzzy_enabled else 'OFF'}")

    def toggle_camera(self):
        if self.camera_running:
            self.stop_camera_callback()
            self.camera_button.config(text="Start Camera")
            self.camera_running = False
        else:
            self.start_camera_callback()
            self.camera_button.config(text="Stop Camera")
            self.camera_running = True

    def update_plot(self):
        while not self.plot_queue.empty():
            timestamp, y = self.plot_queue.get()
            self.xdata.append(datetime.fromtimestamp(timestamp))
            self.ydata.append(y)
            # Keep only the last 10 seconds of data
            self.xdata = [x for x in self.xdata if x >= datetime.now() - timedelta(seconds=10)]
            self.ydata = self.ydata[-len(self.xdata):]
            self.line.set_data(self.xdata, self.ydata)
            self.ax.relim()
            self.ax.autoscale_view()

        self.canvas.draw()
        self.root.after(100, self.update_plot)

    def update_table(self):
        while not self.plot_queue.empty():
            _, data = self.plot_queue.get()
            self.table_data["Descent Speed"].set(data.get("serit_inme_hizi", "N/A"))
            self.table_data["Cutting Speed"].set(data.get("serit_kesme_hizi", "N/A"))
            self.table_data["Descent Current"].set(data.get("inme_motor_akim_a", "N/A"))
            self.table_data["Cutting Current"].set(data.get("serit_motor_akim_a", "N/A"))
            self.table_data["Torques"].set(data.get("inme_motor_tork_percentage", "N/A"))
            self.table_data["Band Deviation"].set(data.get("serit_sapmasi", "N/A"))

        self.root.after(100, self.update_table)
