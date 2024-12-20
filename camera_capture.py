import cv2
import time

# Kamera Ayarları
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1200
FPS = 50
MIN_EXPOSURE = -999999999999999999999  # Minimum shutter time (en kısa pozlama süresi)

# Kamera bağlantısı
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("Kamera açılamadı! Lütfen bağlantıyı kontrol edin.")
    exit()

# Kamera çözünürlüğü ve FPS ayarla
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS)
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)  # Manual exposure
cap.set(cv2.CAP_PROP_EXPOSURE, MIN_EXPOSURE)

# Kamera ayarlarının uygulanıp uygulanmadığını kontrol et
actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
actual_fps = int(cap.get(cv2.CAP_PROP_FPS))

print("Kamera ayarları (gerçek değerler):")
print(f"Çözünürlük: {actual_width}x{actual_height}, FPS: {actual_fps}")

# Video kaydedici ayarları
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # MP4 formatı
out = None
is_recording = False

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Kare okunamıyor, kamera bağlantısında sorun olabilir.")
            break

        # Kayıt yapılıyorsa videoya yaz
        if is_recording and out is not None:
            out.write(frame)

        # Kareyi göster (tam ekran)
        cv2.namedWindow("Arducam UVC Kamera", cv2.WINDOW_FULLSCREEN)
        cv2.imshow("Arducam UVC Kamera", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('q'):  # Çıkış
            break
        elif key == ord('r'):  # Kayıt başlat/durdur
            if not is_recording:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                filename = f"{timestamp}.mp4"
                out = cv2.VideoWriter(
                    filename,
                    fourcc,
                    FPS,
                    (actual_width, actual_height)  # Gerçek çözünürlük kullanılıyor
                )
                if not out.isOpened():
                    print(f"VideoWriter oluşturulamadı, dosya: {filename}")
                    out = None
                else:
                    is_recording = True
                    print(f"Kayıt başladı: {filename}")
            else:
                is_recording = False
                if out is not None:
                    out.release()
                    print("Kayıt durduruldu.")

except KeyboardInterrupt:
    print("Program sonlandırıldı.")

finally:
    # Kamera ve video kaydediciyi kapat
    cap.release()
    if out is not None:
        out.release()
    cv2.destroyAllWindows()
    print("Kamera kapatıldı.")
