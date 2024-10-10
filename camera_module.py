import cv2
import time
import os
from threading import Thread
import queue
from datetime import datetime


class CameraModule:
    def __init__(self, raspberry_pi_ip):
        self.url = f"http://{raspberry_pi_ip}:8001/stream.mjpg"
        self.frame_queue = queue.Queue()
        self.camera_running = False
        self.num_threads = 4
        self.threads = []
        self.output_dir = "./frames"
        self.frame_count = 0
        self.lost_frames = 0
        self.start_time = None
        self.log_interval = 1
        self.capture_thread = None
        self.log_thread = None
        self.timestamp_format = "%d-%m-%Y_%H:%M:%S"

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def save_frame_thread(self):
        while True:
            frame_info = self.frame_queue.get()
            if frame_info is None:  # Kuyrukta None varsa çıkış yap
                break
            frame, frame_number = frame_info
            timestamp = datetime.now().strftime("%d-%m-%Y_%H:%M:%S.%f")
            filename = f"{self.output_dir}/frame_{frame_number:06d}_{timestamp}.jpg"
            cv2.imwrite(filename, frame)
            self.frame_queue.task_done()

    def start_camera(self):
        self.camera_running = True
        self.start_time = time.time()
        self.frame_count = 0
        self.lost_frames = 0

        # Create a new directory for this session
        timestamp = datetime.now().strftime(self.timestamp_format)
        self.output_dir = os.path.join("./frames", f"frames_{timestamp}")
        os.makedirs(self.output_dir, exist_ok=True)

        cap = cv2.VideoCapture(self.url)

        if not cap.isOpened():
            print("Cannot open the stream.")
            self.camera_running = False
            return

        def capture_frames():
            while self.camera_running:
                ret, frame = cap.read()
                if not ret:
                    print("Failed to grab frame")
                    self.lost_frames += 1
                    continue

                self.frame_count += 1
                self.frame_queue.put((frame, self.frame_count))

            cap.release()
            print(f"Final Total Frames: {self.frame_count}, Final Lost Frames: {self.lost_frames}")

        self.capture_thread = Thread(target=capture_frames)
        self.capture_thread.start()

        self.log_thread = Thread(target=self.log_camera_status)
        self.log_thread.start()

        # Start worker threads for saving frames
        for _ in range(self.num_threads):
            thread = Thread(target=self.save_frame_thread)
            thread.start()
            self.threads.append(thread)

        print("Camera started")

    def stop_camera(self):
        self.camera_running = False
        self.frame_queue.put(None)  # Kuyruğa None ekleyerek işçi thread'lerini sonlandır
        if self.capture_thread:
            self.capture_thread.join()
        if self.log_thread:
            self.log_thread.join()

        for thread in self.threads:
            thread.join()

        self.threads = []
        print("Camera stopped")

    def log_camera_status(self):
        while self.camera_running:
            current_time = time.time()
            elapsed_time = current_time - self.start_time
            print(f"Recording: {elapsed_time:.2f}s, Total Frames: {self.frame_count}, Lost Frames: {self.lost_frames}")
            time.sleep(self.log_interval)
