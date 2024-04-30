# Detect connected camera and display video stream
import os

import cv2


# def set_manual_exposure(dev_video_id, exposure_time):
#     commands = [
#         ("v4l2-ctl --device /dev/video"+str(dev_video_id)+" -c exposure_auto=3"),
#         ("v4l2-ctl --device /dev/video"+str(dev_video_id)+" -c exposure_auto=1"),
#         ("v4l2-ctl --device /dev/video"+str(dev_video_id)+" -c exposure_absolute="+str(exposure_time))
#     ]
#     for c in commands:
#         os.system(c)
# # usage
# set_manual_exposure(0, 180)

def main():
    # Get the first camera
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1200)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1200)
    # Set manual exposure
    # cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
    cap.set(cv2.CAP_PROP_EXPOSURE, 250)
    cap.set(cv2.CAP_PROP_GAIN, 0)
    # Check if camera is connected
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    # Display video stream
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame.")
            break

        cv2.imshow("Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
