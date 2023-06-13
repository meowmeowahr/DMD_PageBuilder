import json
import os
import statistics
import sys
import platform

from PIL import Image, ImageOps

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
import qt_material
import qtawesome as qta

if platform.system() == "Windows" and platform.release() == "10":
    from pyqt_windows_os_light_dark_theme_window.main import Window
else:
    Window = QWidget

__version__ = "v0.1.0"

MAX_FILE_PREVIEW_LEN = 40

with open(os.path.join(os.path.curdir, "examples.json")) as ex_file:
    examples = json.loads(ex_file.read())


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


class MainWindow(Window):
    # noinspection PyArgumentList
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("DMD Page Builder")
        self.setWindowIcon(QIcon("icon.svg"))

        self.file = ""
        self.im = Image.open("error.png")
        self.threshold = 50
        self.invert = False
        self.timemult = 1

        self.example_picker = None

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.setLayout(self.layout)

        self.widget = QTabWidget()
        self.layout.addWidget(self.widget)

        self.load_widget = QWidget()
        self.load_root_layout = QHBoxLayout()
        self.load_layout = QVBoxLayout()
        self.load_root_layout.addLayout(self.load_layout)
        self.load_widget.setLayout(self.load_root_layout)
        self.widget.addTab(self.load_widget, "Load")

        self.edit_widget = QWidget()
        self.edit_layout = QVBoxLayout()
        self.edit_widget.setLayout(self.edit_layout)
        self.widget.addTab(self.edit_widget, "Edit")

        self.about_widget = QWidget()
        self.about_layout = QVBoxLayout()
        self.about_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.about_widget.setLayout(self.about_layout)
        self.widget.addTab(self.about_widget, "About")

        self.file_layout = QHBoxLayout()
        self.load_layout.addLayout(self.file_layout)

        self.file_button = QPushButton("Pick File")
        self.file_button.setIcon(qta.icon("mdi.upload", color=secondary_color))
        self.file_button.setIconSize(QSize(32, 32))
        self.file_button.clicked.connect(self.load_source)
        self.file_layout.addWidget(self.file_button)

        self.file_button = QPushButton("Pick an Example")
        self.file_button.setIcon(qta.icon("mdi.image", color=secondary_color))
        self.file_button.setIconSize(QSize(32, 32))
        self.file_button.clicked.connect(self.load_example)
        self.file_layout.addWidget(self.file_button)

        self.file_text = QLabel(str_trunc("No file selected", MAX_FILE_PREVIEW_LEN))
        self.load_layout.addWidget(self.file_text)

        self.load_layout.addStretch()

        self.source_preview = QLabel()
        self.source_preview.setPixmap(QPixmap("error.png").scaled(64, 64))
        self.source_preview.setFixedSize(QSize(64, 64))
        self.source_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.load_layout.addWidget(self.source_preview, alignment=Qt.AlignmentFlag.AlignCenter)

        self.load_layout.addStretch()

        self.edit_top_layout = QGridLayout()
        self.edit_layout.addLayout(self.edit_top_layout)

        self.edit_layout.addStretch()

        self.source_label = QLabel("Source")
        self.edit_top_layout.addWidget(self.source_label, 0, 0)

        self.out_label = QLabel("Output")
        self.edit_top_layout.addWidget(self.out_label, 0, 1)

        self.source_preview_2 = QLabel()
        self.source_preview_2.setPixmap(QPixmap("error.png").scaled(128, 128))
        self.source_preview_2.setFixedSize(QSize(128, 128))
        self.source_preview_2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_top_layout.addWidget(self.source_preview_2, 1, 0)

        self.output_preview = QLabel()
        self.output_preview.setPixmap(QPixmap("error.png").scaled(128, 128))
        self.output_preview.setFixedSize(QSize(128, 128))
        self.output_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit_top_layout.addWidget(self.output_preview, 1, 1)

        self.invert_check = QCheckBox("Invert")
        self.invert_check.setChecked(self.invert)
        self.invert_check.toggled.connect(self.create_image)
        self.edit_layout.addWidget(self.invert_check)

        self.threshold_layout = QHBoxLayout()
        self.edit_layout.addLayout(self.threshold_layout)

        self.threshold_label = QLabel("Threshold")
        self.threshold_layout.addWidget(self.threshold_label)

        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(-1, 255)
        self.threshold_slider.setValue(self.threshold)
        self.threshold_slider.valueChanged.connect(self.create_image)
        self.threshold_layout.addWidget(self.threshold_slider)

        self.multiplier_layout = QHBoxLayout()
        self.edit_layout.addLayout(self.multiplier_layout)

        self.multiplier_label = QLabel("Page Time Multiplier")
        self.multiplier_layout.addWidget(self.multiplier_label)

        self.multiplier_spin = QSpinBox()
        self.multiplier_spin.setValue(self.timemult)
        self.multiplier_spin.setRange(1, 20)
        self.multiplier_spin.valueChanged.connect(self.on_mult_spin)
        self.multiplier_layout.addWidget(self.multiplier_spin)

        self.bottom_layout = QHBoxLayout()
        self.edit_layout.addLayout(self.bottom_layout)

        self.save_pc_button = QPushButton("Save for PC")
        self.save_pc_button.setIcon(qta.icon("mdi.content-save", color=secondary_color))
        self.save_pc_button.setIconSize(QSize(32, 32))
        self.save_pc_button.clicked.connect(self.save_pc)
        self.bottom_layout.addWidget(self.save_pc_button)

        self.save_dmd_button = QPushButton("Save for DMD")
        self.save_dmd_button.setIcon(qta.icon("mdi.micro-sd", color=secondary_color))
        self.save_dmd_button.setIconSize(QSize(32, 32))
        self.save_dmd_button.clicked.connect(self.save_dmd)
        self.bottom_layout.addWidget(self.save_dmd_button)

        self.about_icon = QLabel()
        self.about_icon.setPixmap(QPixmap("icon-large.svg").scaled(192, 192,
                                  transformMode=Qt.TransformationMode.SmoothTransformation))
        self.about_layout.addWidget(self.about_icon)

        self.about_title = QLabel("DMD PageBuilder")
        self.about_title.setObjectName("H1")
        self.about_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.about_layout.addWidget(self.about_title)

        self.about_version = QLabel(__version__)
        self.about_version.setObjectName("H2")
        self.about_version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.about_layout.addWidget(self.about_version)

        self.about_author = QLabel("By: Kevin Ahr")
        self.about_author.setObjectName("H2")
        self.about_author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.about_layout.addWidget(self.about_author)

        self.create_image()
        self.show()

    def load_source(self):
        dialog = QFileDialog(self)
        dialog.setNameFilter("Supported Images (*.png *.jpg *.bmp *.dib *.jpg "
                             "*.jpeg *.jpe *.jfif *.tiff *.tif *.webp *.dmd)\n"
                             "Raster Images (*.png *.jpg *.bmp *.dib *.jpg "
                             "*.jpeg *.jpe *.jfif *.tiff *.tif *.webp)\nDMD Images (*.dmd)")
        out = dialog.exec()
        if out:
            self.file = dialog.selectedFiles()[0]

            if self.file.endswith(".dmd"):
                with open(self.file, 'rb') as file:
                    data = file.read()

                if len(data) == 1025:
                    start_byte = 1
                    self.timemult = data[0]
                    self.multiplier_spin.setValue(self.timemult)
                elif len(data) == 1024:
                    start_byte = 0
                else:
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Warning)
                    msg.setText(f"Image is corrupt\nExpected 1025/1024 bytes, Got {len(data)} bytes")
                    msg.setWindowTitle("Image Error")
                    msg.setStandardButtons(QMessageBox.Ok)
                    msg.exec_()
                    return

                pixels = []
                for byte in data[start_byte:]:
                    pixel = 0 if byte == 0x00 else 255
                    pixels.append(pixel)

                self.im = Image.new('L', (32, 32))
                self.im.putdata(pixels)

                self.file_text.setText(str_trunc(self.file, MAX_FILE_PREVIEW_LEN))
                preview_im = self.im
                preview_im = remove_transparency(preview_im, (0, 0, 0))
                preview_im = preview_im.convert("RGB")
                data = preview_im.tobytes("raw", "RGB")
                qi = QImage(data, preview_im.size[0], preview_im.size[1], preview_im.size[0] * 3,
                            QImage.Format.Format_RGB888)
                preview_pixmap = QPixmap.fromImage(qi)
                self.source_preview.setPixmap(preview_pixmap.scaled(64, 64))
                self.source_preview_2.setPixmap(preview_pixmap.scaled(128, 128))

                self.create_image()
            else:
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
                    self.source_preview_2.setPixmap(preview_pixmap.scaled(128, 128))

                    self.create_image()

    def open_example(self, file, name):
        self.im = Image.open(file)

        self.file_text.setText(str_trunc(f"Example, {name}", MAX_FILE_PREVIEW_LEN))
        preview_im = self.im
        preview_im = remove_transparency(preview_im, (0, 0, 0))
        preview_im = preview_im.convert("RGB")
        data = preview_im.tobytes("raw", "RGB")
        qi = QImage(data, preview_im.size[0], preview_im.size[1], preview_im.size[0] * 3,
                    QImage.Format.Format_RGB888)
        preview_pixmap = QPixmap.fromImage(qi)
        self.source_preview.setPixmap(preview_pixmap.scaled(64, 64))
        self.source_preview_2.setPixmap(preview_pixmap.scaled(128, 128))

    def load_example(self):
        self.example_picker = ExamplePicker(window)
        self.example_picker.exec()

        if self.example_picker.item:
            self.open_example(os.path.join(os.path.curdir, "examples",
                                           list(examples["name_pairs"].keys())
                                           [list(examples["name_pairs"].values()).index(self.example_picker.item)]),
                              self.example_picker.item)
            self.file = os.path.join(os.path.curdir, "examples",
                                     list(examples["name_pairs"].keys())
                                     [list(examples["name_pairs"].values()).index(self.example_picker.item)])
            self.create_image()

    def create_image(self):
        self.invert = self.invert_check.isChecked()
        self.threshold = self.threshold_slider.value()

        if self.file:
            if self.file.endswith(".dmd"):
                with open(self.file, 'rb') as file:
                    data = file.read()

                pixels = []
                for byte in data[1:]:
                    pixel = 0 if byte == 0x00 else 255
                    pixels.append(pixel)

                self.im = Image.new('L', (32, 32))
                self.im.putdata(pixels)
            else:
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
        self.output_preview.setPixmap(preview_pixmap.scaled(128, 128))

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
                    data[index] = 0x01
                else:
                    data[index] = 0x00

            data.insert(0, self.timemult)

            with open(out[0], "wb") as file:
                file.write(bytes(data))

    def on_mult_spin(self):
        self.timemult = self.multiplier_spin.value()


class ExamplePicker(QDialog):
    # noinspection PyArgumentList
    def __init__(self, parent):
        super(ExamplePicker, self).__init__(parent)
        self.setModal(True)

        self.item = ""

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.top_layout = QHBoxLayout()
        self.layout.addLayout(self.top_layout)

        icon_files = examples["name_pairs"].values()

        model = IconModel()
        model.setStringList(icon_files)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

        self.list_view = IconListView()
        self.list_view.setViewMode(QListView.IconMode)
        self.list_view.setModel(self.proxy_model)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.doubleClicked.connect(self.select)
        self.list_view.clicked.connect(lambda: self.select_btn.setEnabled(True))
        self.list_view.setMinimumWidth(520)
        self.top_layout.addWidget(self.list_view)

        self.bottom_layout = QHBoxLayout()
        self.layout.addLayout(self.bottom_layout)

        self.credit = QLabel(f"MDI icons from <a href=\"https://pictogrammers.com/\" "
                             f"style='color: {os.environ['QTMATERIAL_SECONDARYCOLOR']}'>Pictogrammers</a>")
        self.credit.setOpenExternalLinks(True)
        self.bottom_layout.addWidget(self.credit)

        self.bottom_layout.addStretch()

        self.cancel = QPushButton("Cancel")
        self.cancel.clicked.connect(self.close)
        self.bottom_layout.addWidget(self.cancel)

        self.select_btn = QPushButton("Select")
        self.select_btn.clicked.connect(self.select)
        self.select_btn.setEnabled(False)
        self.bottom_layout.addWidget(self.select_btn)

        self.show()

    def select(self):
        indexes = self.list_view.selectedIndexes()
        self.close()
        self.item = indexes[0].data()


class IconListView(QListView):
    """
    A QListView that scales its grid size to ensure the same number of
    columns are always drawn.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

    def resizeEvent(self, event):
        """
        Re-implemented to re-calculate the grid size to provide scaling icons

        Parameters
        ----------
        event : QtCore.QEvent
        """
        width = self.viewport().width() - 30
        # Minus 30 above ensures we don't end up with an item width that
        # can't be drawn the expected number of times across the view without
        # being wrapped.
        # Without this, the view can flicker during resize
        tile_width = width / 5
        icon_width = int(tile_width * 0.8)
        # tileWidth needs to be an integer for setGridSize
        tile_width = int(tile_width)

        self.setGridSize(QSize(tile_width, tile_width))
        self.setIconSize(QSize(icon_width, icon_width))

        return super().resizeEvent(event)


class IconModel(QStringListModel):

    def __init__(self):
        super().__init__()

    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index, role):
        """
        Re-implemented to return the icon for the current index.

        Parameters
        ----------
        index : QtCore.QModelIndex
        role : int

        Returns
        -------
        Any
        """
        if role == Qt.DecorationRole:
            icon_string = self.data(index, role=Qt.DisplayRole)
            return QPixmap(os.path.join(os.path.curdir, "examples",
                                        list(examples["name_pairs"].keys())
                                        [list(examples["name_pairs"].values()).index(icon_string)]))
        return super().data(index, role)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("DMD Page Builder")
    app.setApplicationVersion(__version__)

    qt_material.apply_stylesheet(app, "theme.xml", css_file="m3-style.qss")
    secondary_color = os.environ.get("QTMATERIAL_SECONDARYCOLOR")

    window = MainWindow()
    sys.exit(app.exec())
