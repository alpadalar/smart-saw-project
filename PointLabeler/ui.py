import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush
from PyQt5.QtWidgets import (QMainWindow, QGraphicsView, QGraphicsScene,
                             QFileDialog, QAction, QPushButton, QVBoxLayout, QWidget,
                             QDockWidget, QLabel, QGraphicsEllipseItem)

from data_manager import DataManager


class ImageViewer(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.image_pixmap = None
        self.selected_point = None
        self.selected_point_item = None
        self.setDragMode(QGraphicsView.NoDrag)  # Kaydırma modunu değiştir
        self._mousePressed = False
        self.viewport().setCursor(Qt.CrossCursor)  # Başlangıç imlecini + olarak ayarla

    def set_image(self, image_path):
        self.scene.clear()
        self.image_pixmap = QPixmap(image_path)
        self.scene.addPixmap(self.image_pixmap)
        rect = self.image_pixmap.rect()
        self.setSceneRect(rect.x(), rect.y(), rect.width(), rect.height())
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)  # Bu satırı ekleyin
        self.selected_point = None
        self.selected_point_item = None

    def wheelEvent(self, event):
        factor = 1.2
        if event.angleDelta().y() > 0:
            self.scale(factor, factor)
        else:
            self.scale(1 / factor, 1 / factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._mousePressed = True
            self._dragPos = event.pos()
            self.viewport().setCursor(Qt.ClosedHandCursor)  # Kaydırma için imleci değiştir
            event.accept()
        elif self.image_pixmap and event.button() == Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            if 0 <= scene_pos.x() <= self.image_pixmap.width() and 0 <= scene_pos.y() <= self.image_pixmap.height():
                self.update_selected_point(scene_pos.x(), scene_pos.y())
                if hasattr(self.parent(), 'add_label'):
                    self.parent().add_label(scene_pos.x(), scene_pos.y())
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._mousePressed:
            newPos = event.pos()
            diff = newPos - self._dragPos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            self._dragPos = newPos
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._mousePressed = False
            self.viewport().setCursor(Qt.CrossCursor)  # Kaydırma bittiğinde imleci tekrar + yap
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def drawForeground(self, painter, rect):
        if self.selected_point:
            painter.setPen(QPen(Qt.red, 5))  # Noktanın rengini ve büyüklüğünü ayarlayın
            painter.drawPoint(int(self.selected_point[0]), int(self.selected_point[1]))

    def update_selected_point(self, x, y):
        # Eski seçilen noktayı temsil eden grafik öğeyi kaldır
        if self.selected_point_item:
            self.scene.removeItem(self.selected_point_item)
            self.selected_point_item = None

        # Yeni seçilen noktayı temsil eden bir nokta (çok küçük bir daire) çizin
        self.selected_point_item = self.scene.addEllipse(x - 1, y - 1, 2, 2, QPen(Qt.red), QBrush(Qt.red))
        self.selected_point = (x, y)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_image_index = 0
        self.setWindowTitle('Image Labeling Application')
        self.data_manager = DataManager()
        self.init_ui()
        # self.setGeometry(100, 100, 800, 600)
        self.setWindowState(Qt.WindowMaximized)

    def init_ui(self):
        self.image_viewer = ImageViewer()
        self.setCentralWidget(self.image_viewer)

        open_folder_action = QAction('Open Folder', self)
        open_folder_action.triggered.connect(self.open_folder)

        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(open_folder_action)

        next_button = QPushButton('Next')
        next_button.clicked.connect(self.next_image)

        prev_button = QPushButton('Previous')
        prev_button.clicked.connect(self.prev_image)

        self.label_coordinates = QLabel("Selected Point = N/A")  # Koordinatları göstermek için etiket
        layout = QVBoxLayout()
        layout.addWidget(prev_button)
        layout.addWidget(next_button)
        layout.addWidget(self.label_coordinates)  # Koordinat etiketini layout'a ekle

        container = QWidget()
        container.setLayout(layout)

        dockWidget = QDockWidget("Controls", self)
        dockWidget.setWidget(container)
        self.addDockWidget(Qt.RightDockWidgetArea, dockWidget)

        self.setCursor(Qt.CrossCursor)

    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.data_manager.set_folder_path(folder_path)
            self.show_image(0)

    def show_image(self, index):
        if 0 <= index < len(self.data_manager.image_paths):
            image_path = self.data_manager.image_paths[index]
            image_name = os.path.basename(image_path)
            self.image_viewer.set_image(image_path)
            total_images = len(self.data_manager.image_paths)
            labeled_images_count = len(
                [label for label in self.data_manager.labels if self.data_manager.labels[label] is not None])

            # Burası önemli: Eğer bu görüntü için bir etiket varsa, onu artı işareti olarak çizdir
            if image_name in self.data_manager.labels:
                x, y = self.data_manager.labels[image_name]
                # Mevcut etiketleri temizle ve yeniden çiz
                self.image_viewer.scene.clear()
                self.image_viewer.set_image(image_path)  # Görüntüyü yeniden yükler
                self.image_viewer.update_selected_point(x, y)  # Etiketi artı olarak çizdir
                self.label_coordinates.setText(f"Selected Point = {x:.2f}, {y:.2f}")
            else:
                self.image_viewer.selected_point = None
                self.label_coordinates.setText("Selected Point = N/A")

            # Başlık güncelleme
            self.setWindowTitle(
                f"Image Labeling Application - {image_name} [{index + 1}/{total_images}], Labeled Images: {labeled_images_count}")

            self.image_viewer.update()  # Görüntüleyiciyi güncelle

    def next_image(self):
        if self.current_image_index + 1 < len(self.data_manager.image_paths):
            self.current_image_index += 1
            self.show_image(self.current_image_index)

    def prev_image(self):
        if self.current_image_index - 1 >= 0:
            self.current_image_index -= 1
            self.show_image(self.current_image_index)

    def add_label(self, x, y):
        if not self.data_manager.image_paths:
            return
        image_path = self.data_manager.image_paths[self.current_image_index]
        image_name = os.path.basename(image_path)
        self.data_manager.add_label(image_name, x, y)
        self.label_coordinates.setText(f"Selected Point = {x:.2f}, {y:.2f}")
