import statistics
import sys

from PIL import Image, ImageOps

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import qt_material

MAX_FILE_PREVIEW_LEN = 40


def str_trunc(string: str, nchars: int):
    return (string[:nchars - 1] + "…")[:min(len(string), nchars)]


def remove_transparency(im, bg_colour=(255, 255, 255)):
    # Only process if image has transparency (http://stackoverflow.com/a/1963146)
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):

        # Need to convert to RGBA if LA format due to a bug in PIL (http://stackoverflow.com/a/1963146)
        alpha = im.convert('RGBA').split()[-1]

        # Create a new background image of our matt color.
        # Must be RGBA because paste requires both images to have the same format
        # (http://stackoverflow.com/a/8720632  and  http://stackoverflow.com/a/9459208)
        bg = Image.new("RGBA", im.size, bg_colour + (255,))
        bg.paste(im, mask=alpha)
        return bg

    else:
        return im


def slice_per(source, step):
    return [source[i::step] for i in range(step)]


def flatten(li):
    return [item for sublist in li for item in sublist]


class MainWindow(QMainWindow):
    # noinspection PyArgumentList
    def __init__(self):
        super(MainWindow, self).__init__(None)
        self.setWindowTitle("DMD Page Builder")

        self.file = None
        self.im = Image.open("error.png")
        self.threshold = 50
        self.invert = False

        self.widget = QTabWidget()
        self.setCentralWidget(self.widget)

        self.builder_widget = QWidget()
        self.builder_layout = QVBoxLayout()
        self.builder_widget.setLayout(self.builder_layout)
        self.widget.addTab(self.builder_widget, "Builder")

        self.file_group = QGroupBox("Step 1")
        self.builder_layout.addWidget(self.file_group)

        self.file_layout = QVBoxLayout()
        self.file_group.setLayout(self.file_layout)

        self.file_button = QPushButton("Select an Image")
        self.file_button.clicked.connect(self.load_source)
        self.file_layout.addWidget(self.file_button)

        self.file_text = QLabel(str_trunc("No file selected", MAX_FILE_PREVIEW_LEN))
        self.file_layout.addWidget(self.file_text)

        self.edit_group = QGroupBox("Step 2")
        self.builder_layout.addWidget(self.edit_group)

        self.edit_layout = QHBoxLayout()
        self.edit_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_group.setLayout(self.edit_layout)

        self.edit_left_layout = QVBoxLayout()
        self.edit_layout.addLayout(self.edit_left_layout)

        self.source_preview = QLabel()
        self.source_preview.setPixmap(QPixmap("error.png").scaled(64, 64))
        self.source_preview.setFixedSize(QSize(64, 64))
        self.source_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_left_layout.addWidget(self.source_preview)

        self.output_preview = QLabel()
        self.output_preview.setPixmap(QPixmap("error.png").scaled(64, 64))
        self.output_preview.setFixedSize(QSize(64, 64))
        self.output_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_left_layout.addWidget(self.output_preview)

        self.edit_right_layout = QVBoxLayout()
        self.edit_layout.addLayout(self.edit_right_layout)

        self.invert_check = QCheckBox("Invert")
        self.invert_check.setChecked(self.invert)
        self.invert_check.toggled.connect(self.create_image)
        self.edit_right_layout.addWidget(self.invert_check)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(-1, 255)
        self.threshold_slider.setValue(self.threshold)
        self.threshold_slider.valueChanged.connect(self.create_image)
        self.edit_right_layout.addWidget(self.threshold_slider)

        self.bottom_layout = QHBoxLayout()
        self.builder_layout.addLayout(self.bottom_layout)

        self.save_pc_button = QPushButton("Save for PC")
        self.save_pc_button.clicked.connect(self.save_pc)
        self.bottom_layout.addWidget(self.save_pc_button)

        self.save_dmd_button = QPushButton("Save for DMD")
        self.save_dmd_button.clicked.connect(self.save_dmd)
        self.bottom_layout.addWidget(self.save_dmd_button)

        self.create_image()
        self.show()

    def load_source(self):
        dialog = QFileDialog(self)
        dialog.setNameFilter("Supported Images (*.png *.jpg *.bmp *.dib *.jpg *.jpeg *.jpe *.jfif *.tiff *.tif *.webp)")
        out = dialog.exec()
        if out:
            self.file = dialog.selectedFiles()[0]

            self.im = Image.open(self.file)
            if self.im.size != (32, 32):
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText("Image Size must be 32x32")
                msg.setWindowTitle("Image Size")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec_()
            else:
                self.file_text.setText(str_trunc(self.file, MAX_FILE_PREVIEW_LEN))
                preview_im = self.im
                preview_im = remove_transparency(preview_im, (0, 0, 0))
                preview_im = preview_im.convert("RGB")
                data = preview_im.tobytes("raw", "RGB")
                qi = QImage(data, preview_im.size[0], preview_im.size[1], preview_im.size[0] * 3,
                            QImage.Format.Format_RGB888)
                preview_pixmap = QPixmap.fromImage(qi)
                self.source_preview.setPixmap(preview_pixmap.scaled(64, 64))

                self.create_image()

    def create_image(self):
        self.invert = self.invert_check.isChecked()
        self.threshold = self.threshold_slider.value()

        if self.file:
            self.im = Image.open(self.file)
        else:
            self.im = Image.open("error.png")

        self.im = remove_transparency(self.im, (0, 0, 0))
        self.im = self.im.convert("RGB")

        if self.invert:
            self.im = ImageOps.invert(self.im)

        raw_data = slice_per(list(self.im.getdata()), 32)

        for yi, y in enumerate(raw_data):
            for xi, x in enumerate(y):
                if self.invert:
                    threshold = 255 - self.threshold
                else:
                    threshold = self.threshold

                if statistics.mean(x) > threshold:
                    raw_data[yi][xi] = (255, 255, 255)
                else:
                    raw_data[yi][xi] = (0, 0, 0)

        self.im = Image.new(self.im.mode, self.im.size)
        self.im.putdata(flatten(raw_data))
        self.im = self.im.rotate(-90)
        self.im = ImageOps.mirror(self.im)

        preview_im = self.im
        preview_im = preview_im.convert("RGB")
        data = preview_im.tobytes("raw", "RGB")

        qi = QImage(data, preview_im.size[0], preview_im.size[1], preview_im.size[0] * 3,
                    QImage.Format.Format_RGB888)

        preview_pixmap = QPixmap.fromImage(qi)
        self.output_preview.setPixmap(preview_pixmap.scaled(64, 64))

    def save_pc(self):
        dialog = QFileDialog(self)
        out = dialog.getSaveFileName(filter="Bitmap Image (*.bmp)", parent=self)
        if out[0]:
            self.im.save(out[0])

    def save_dmd(self):
        dialog = QFileDialog(self)
        out = dialog.getSaveFileName(filter="DMD Image (*.dmd)", parent=self)
        if out[0]:
            data = list(self.im.getdata())

            for index, pixel in enumerate(data):
                if pixel == (255, 255, 255):
                    data[index] = "1"
                else:
                    data[index] = "0"

            data = "10;" + "".join(data)
            print(data)
            with open(out[0], "w") as file:
                file.write(data)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    qt_material.apply_stylesheet(app, "dark_red.xml")
    window = MainWindow()
    sys.exit(app.exec())
