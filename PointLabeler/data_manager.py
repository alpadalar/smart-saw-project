import os
from PIL import Image

class DataManager:
    """A class to manage image files and labels within a specified folder.
    
    Attributes:
        folder_path (str): The path to the folder containing image files and the labels.txt file.
        image_paths (list): A list of paths to the image files within the folder.
        labels (dict): A dictionary mapping image file names to their label coordinates (x, y).
    """
    
    def __init__(self, folder_path=None):
        """Initializes the DataManager with an optional folder path, loads image paths and labels."""
        self.folder_path = folder_path
        self.image_paths = []
        self.labels = {}
        if folder_path:
            self.load_images()
            self.load_labels()

    def set_folder_path(self, folder_path):
        """Sets the folder path, reloads image paths and labels according to the new folder."""
        self.folder_path = folder_path
        self.load_images()
        self.load_labels()

    def load_images(self):
        """Loads the paths of all .jpg and .png files within the specified folder."""
        if self.folder_path:
            self.image_paths = [os.path.join(self.folder_path, f) for f in os.listdir(self.folder_path) if f.endswith(('.jpg', '.png'))]
            self.image_paths.sort()

    def load_labels(self):
        """Loads labels from the labels.txt file within the specified folder."""
        self.labels.clear()
        labels_path = os.path.join(self.folder_path, 'labels.txt')
        if os.path.exists(labels_path):
            with open(labels_path, 'r') as file:
                for line in file:
                    parts = line.strip().split()
                    if len(parts) == 3:
                        self.labels[parts[0]] = (float(parts[1]), float(parts[2]))

    def save_labels(self):
        """Saves all labels to the labels.txt file within the specified folder."""
        labels_path = os.path.join(self.folder_path, 'labels.txt')
        with open(labels_path, 'w') as file:
            for img_name, coords in self.labels.items():
                file.write(f'{img_name} {coords[0]} {coords[1]}\n')

    def add_label(self, image_name, x, y):
        """Adds or updates a label for a specific image and saves the updated labels to file."""
        self.labels[image_name] = (x, y)
        self.save_labels()
