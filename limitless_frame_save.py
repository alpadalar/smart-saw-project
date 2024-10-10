import cv2
import time
from datetime import datetime
from threading import Thread
import queue
import os

# Raspberry Pi'nin IP adresini ve portunu buraya girin
raspberry_pi_ip = "192.168.11.185"  # Örnek IP, kendi Raspberry Pi'nizin IP adresini girin
url = f"http://{raspberry_pi_ip}:8001/stream.mjpg"

# Frame kuyrukları ve işleme thread'leri
frame_queue = queue.Queue()
output_dir = "./frames"  # Frame'lerin kaydedileceği dizin

if not os.path.exists(output_dir):
    os.makedirs(output_dir)

def save_frame_thread():
    while True:
        frame_info = frame_queue.get()
        if frame_info is None:  # Kuyrukta None varsa çıkış yap
            break
        frame, frame_number = frame_info
        filename = f"{output_dir}/frame_{frame_number:06d}.jpg"
        cv2.imwrite(filename, frame)
        frame_queue.task_done()

# 8 işçi thread başlat
num_threads = 8
threads = []
for _ in range(num_threads):
    thread = Thread(target=save_frame_thread)
    thread.start()
    threads.append(thread)

# VideoCapture ile MJPEG akışını açın
cap = cv2.VideoCapture(url)

if not cap.isOpened():
    print("Cannot open the stream.")
    exit()

# Frame kaybı ve gecikme için başlangıç zamanı ve sayaçlar
start_time = time.time()
frame_count = 0
lost_frames = 0
log_interval = 1  # Log'ları her saniye yaz

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame")
        lost_frames += 1
        continue

    frame_count += 1
    frame_queue.put((frame, frame_count))

    # Frame'i göster
    cv2.imshow("Raspberry Pi Stream", frame)

    # 'q' tuşuna basıldığında döngüyü kır
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # Log bilgilerini belirli aralıklarla yaz
    current_time = time.time()
    if current_time - start_time >= log_interval:
        print(f"Time: {current_time - start_time:.2f}s, Total Frames: {frame_count}, Lost Frames: {lost_frames}")
        start_time = current_time

# Kuyruğa None ekleyerek işçi thread'lerini sonlandır
for _ in range(num_threads):
    frame_queue.put(None)

# Tüm thread'lerin bitmesini bekleyin
for thread in threads:
    thread.join()

# Kaynakları serbest bırakın
cap.release()
cv2.destroyAllWindows()

print(f"Final Total Frames: {frame_count}, Final Lost Frames: {lost_frames}")
