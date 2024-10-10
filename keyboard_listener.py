import threading


def keyboard_listener(keyboard_queue):
    import keyboard  # third-party library, make sure it's installed

    def on_press(event):
        if event.name == 'm':
            keyboard_queue.put('m')
        elif event.name == 'f':
            keyboard_queue.put('f')
        print(event)

    keyboard.on_press(on_press)
    threading.Event().wait()  # Keep the thread alive
