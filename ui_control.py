import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import DateFormatter
from datetime import datetime, timedelta
import threading


class UIControl:
    def __init__(self, root, toggle_fuzzy_control_callback, toggle_linear_control_callback,
                 start_camera_callback, stop_camera_callback, plot_queue, close_app_callback, conn_status=0):
        self.toggle_fuzzy_control_callback = toggle_fuzzy_control_callback
        self.toggle_linear_control_callback = toggle_linear_control_callback
        self.start_camera_callback = start_camera_callback
        self.stop_camera_callback = stop_camera_callback
        self.plot_queue = plot_queue
        self.root = root
        self.close_app_callback = close_app_callback
        self.camera_running = False
        self.fuzzy_control_enabled = False
        self.linear_control_enabled = False
        self.frame_count = 0

        # Pencere başlığı
        self.root.title("Control Panel")

        # Bağlantı Durumu
        self.connection_status_label = tk.Label(root, text=f"Bağlantı Durumu: {'Bağlı' if conn_status else 'Bağlı Değil'}")
        self.connection_status_label.pack()

        # Tarih ve Saat
        self.time_label = tk.Label(root, text="")
        self.time_label.pack()
        self.update_time()

        # Kontrol Durumu
        self.status_label = tk.Label(root, text="Kontrol Durumu: Kapalı")
        self.status_label.pack()

        # Fuzzy Control Butonları
        self.fuzzy_on_button = tk.Button(root, text="Fuzzy Aç", command=self.enable_fuzzy_control)
        self.fuzzy_on_button.pack()
        self.fuzzy_off_button = tk.Button(root, text="Fuzzy Kapat", command=self.disable_fuzzy_control)
        self.fuzzy_off_button.pack()

        # Lineer Control Butonları
        self.linear_on_button = tk.Button(root, text="Lineer Aç", command=self.enable_linear_control)
        self.linear_on_button.pack()
        self.linear_off_button = tk.Button(root, text="Lineer Kapat", command=self.disable_linear_control)
        self.linear_off_button.pack()

        # Kamera Kaydı Butonları ve Durumu
        self.camera_status_label = tk.Label(root, text="Kamera: Kapalı")
        self.camera_status_label.pack()
        self.start_camera_button = tk.Button(root, text="Kamera Başlat", command=self.start_camera)
        self.start_camera_button.pack()
        self.stop_camera_button = tk.Button(root, text="Kamera Durdur", command=self.stop_camera)
        self.stop_camera_button.pack()

        # Alınan Frame Sayısı
        self.frame_count_label = tk.Label(root, text="Alınan Frame Sayısı: 0")
        self.frame_count_label.pack()

        # Grafik Ayarları
        self.figure, self.ax = plt.subplots(figsize=(5, 4))
        self.ax.set_title('Fuzzy Çıkışı')
        self.ax.set_xlabel('Zaman')
        self.ax.set_ylabel('Çıkış Değeri')
        self.line, = self.ax.plot([], [], 'r-')
        self.ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S'))
        self.xdata = []
        self.ydata = []

        self.canvas = FigureCanvasTkAgg(self.figure, master=root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # Uygulamayı Kapat Butonu
        self.close_button = tk.Button(root, text="Uygulamayı Kapat", command=self.close_app_callback)
        self.close_button.pack()

        # Arayüz güncellemeleri
        self.update_plot()

    def update_time(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=f"Tarih & Saat: {current_time}")
        self.root.after(1000, self.update_time)

    def enable_fuzzy_control(self):
        self.fuzzy_control_enabled = True
        self.linear_control_enabled = False
        self.status_label.config(text="Kontrol Durumu: Fuzzy Açık")
        self.toggle_fuzzy_control_callback()
        print("Fuzzy Control Açıldı")

    def disable_fuzzy_control(self):
        self.fuzzy_control_enabled = False
        self.status_label.config(text="Kontrol Durumu: Kapalı")
        self.toggle_fuzzy_control_callback()
        print("Fuzzy Control Kapandı")

    def enable_linear_control(self):
        self.linear_control_enabled = True
        self.fuzzy_control_enabled = False
        self.status_label.config(text="Kontrol Durumu: Lineer Açık")
        self.toggle_linear_control_callback()
        print("Lineer Control Açıldı")

    def disable_linear_control(self):
        self.linear_control_enabled = False
        self.status_label.config(text="Kontrol Durumu: Kapalı")
        self.toggle_linear_control_callback()
        print("Lineer Control Kapandı")

    def start_camera(self):
        if not self.camera_running:
            self.camera_running = True
            self.camera_status_label.config(text="Kamera: Açık")
            self.frame_count = 0
            self.update_frame_count()
            self.camera_thread = threading.Thread(target=self.start_camera_callback)
            self.camera_thread.start()
            print("Kamera Kaydı Başlatıldı")

    def stop_camera(self):
        if self.camera_running:
            self.camera_running = False
            self.camera_status_label.config(text="Kamera: Kapalı")
            self.stop_camera_callback()
            print("Kamera Kaydı Durduruldu")

    def update_frame_count(self):
        self.frame_count += 1
        self.frame_count_label.config(text=f"Alınan Frame Sayısı: {self.frame_count}")
        if self.camera_running:
            self.root.after(100, self.update_frame_count)

    def update_plot(self):
        while not self.plot_queue.empty():
            timestamp, y = self.plot_queue.get()
            # timestamp'ı datetime objesine dönüştür
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

            self.xdata.append(timestamp)
            self.ydata.append(y)
            # Keep only the last 10 seconds of data
            self.xdata = [x for x in self.xdata if x >= datetime.now() - timedelta(seconds=10)]
            self.ydata = self.ydata[-len(self.xdata):]
            self.line.set_data(self.xdata, self.ydata)
            self.ax.relim()
            self.ax.autoscale_view()

        self.canvas.draw()
        self.root.after(100, self.update_plot)
