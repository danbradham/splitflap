from __future__ import division
from collections import defaultdict
from Qt import QtWidgets, QtGui, QtCore


class RepaintProperty(object):
    '''
    A property that will cause a QWidget to repaint when changed
    '''

    values = defaultdict(dict)

    def __init__(self, name, default):
        self.name = name
        self.default = default

    def __get__(self, inst, cls=None):
        value = self.values[inst].setdefault(self.name, self.default)
        return value

    def __set__(self, inst, value):
        self.values[inst][self.name] = value
        inst.repaint()


class GridWidget(QtWidgets.QWidget):
    '''
    A Widget displaying an array of cards based on some parameters
    '''

    rows = RepaintProperty('rows', 2)
    columns = RepaintProperty('columns', 2)
    width = RepaintProperty('width', 1.5)
    height = RepaintProperty('height', 3)
    padding = RepaintProperty('padding', 0.2)
    image = RepaintProperty('image', None)

    def __init__(self, rows, columns, width, height, padding, parent=None):
        super(GridWidget, self).__init__(parent)
        self.rows = rows
        self.columns = columns
        self.width = width
        self.height = height
        self.padding = padding
        self.pixmap = None

    def set_image(self, image_path):
        self.pixmap = None
        self.image = image_path

    def draw_geometry(self, painter, event):

        ev_width = event.rect().width()
        ev_height = event.rect().height()
        g_width = self.columns * self.width + self.padding
        g_height = self.rows * self.height + self.padding

        scale = min(ev_height / g_height, ev_width / g_width)
        tx = (ev_width - g_width * scale) * 0.5
        ty = (ev_height - g_height * scale) * 0.5

        padding = self.padding * scale
        width = self.width * scale
        height = self.height * scale
        rect = QtCore.QRectF(
            padding,
            padding,
            width - padding,
            height - padding
        )

        rects = []
        lines = []
        for y in range(self.rows):
            for x in range(self.columns):
                dx = x * width + tx
                dy = y * height + ty
                rects.append(rect.translated(dx, dy))

                mid = dy + (height + padding) * 0.5
                lines.append([dx, mid, dx + width, mid])

        # Get round rect radius
        rscale = self.width / self.height
        if rscale < 1:
            rx = 25
            ry = rx * rscale
        else:
            rscale = self.height / self.width
            ry = 25
            rx = ry * rscale

        font = QtGui.QFont('')
        font.setStyleHint(QtGui.QFont.Monospace)
        font.setStretch(90)
        font.setPixelSize(min(width, height) * 0.7)

        # Draw Rects
        if not self.image:

            painter.setBrush(QtGui.QColor(145, 145, 145))
            for r in rects:
                painter.drawRoundRect(r, rx, ry)

            painter.setFont(font)
            painter.setPen(QtGui.QColor(72, 72, 72))
            for i, r in enumerate(rects):
                painter.drawText(r, QtCore.Qt.AlignCenter, str(i))

            # Draw Lines
            pen = QtGui.QPen(
                QtGui.QColor(37, 37, 37),
                height * 0.025,
                QtCore.Qt.SolidLine)
            painter.setPen(pen)
            for line in lines:
                painter.drawLine(*line)

            return

        alpha = QtGui.QPixmap(ev_width, ev_height)
        a_painter = QtGui.QPainter()
        a_painter.begin(alpha)
        a_painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Draw Background
        a_painter.setBrush(QtGui.QColor(0, 0, 0))
        a_painter.drawRect(event.rect())

        # Draw rects
        a_painter.setBrush(QtGui.QColor(255, 255, 255))
        for r in rects:
            a_painter.drawRoundRect(r, rx, ry)

        # Draw text
        a_painter.setFont(font)
        a_painter.setPen(QtGui.QColor(75, 75, 75))
        for i, r in enumerate(rects):
            a_painter.drawText(r, QtCore.Qt.AlignCenter, str(i))

        # Draw Lines
        pen = QtGui.QPen(
            QtGui.QColor(0, 0, 0),
            height * 0.025,
            QtCore.Qt.SolidLine)
        a_painter.setPen(pen)
        for line in lines:
            a_painter.drawLine(*line)

        a_painter.end()

        pw, ph = g_width * scale, g_height * scale
        alpha = alpha.copy(QtCore.QRect(tx, ty, pw, ph))
        if not self.pixmap:
            self.pixmap = QtGui.QPixmap(self.image)

        scaled = self.pixmap.scaled(pw, ph)
        scaled.setAlphaChannel(alpha)
        painter.drawPixmap(tx, ty, scaled)
        return

    def paintEvent(self, event):

        painter = QtGui.QPainter()
        painter.begin(self)

        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # Draw Background
        painter.setBrush(QtGui.QColor(37, 37, 37))
        painter.drawRect(event.rect())

        # Draw Rects
        self.draw_geometry(painter, event)

        painter.end()


class Dialog(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(Dialog, self).__init__(parent)

        self.grid = GridWidget(
            rows=3,
            columns=4,
            width=2,
            height=3,
            padding=0.2,
        )
        self.grid.setMinimumSize(300, 200)

        row_label = QtWidgets.QLabel('rows')
        row_label.setAlignment(QtCore.Qt.AlignRight)

        column_label = QtWidgets.QLabel('columns')
        column_label.setAlignment(QtCore.Qt.AlignRight)

        num_images_label = QtWidgets.QLabel('num_images')
        num_images_label.setAlignment(QtCore.Qt.AlignRight)

        radius_label = QtWidgets.QLabel('radius')
        radius_label.setAlignment(QtCore.Qt.AlignRight)

        padding_label = QtWidgets.QLabel('padding')
        padding_label.setAlignment(QtCore.Qt.AlignRight)

        self.rows = QtWidgets.QSpinBox()
        self.rows.setMinimum(1)
        self.rows.setValue(3)
        self.rows.valueChanged.connect(self.grid_attr_changed('rows'))

        self.columns = QtWidgets.QSpinBox()
        self.columns.setMinimum(1)
        self.columns.setValue(4)
        self.columns.valueChanged.connect(self.grid_attr_changed('columns'))

        self.num_images = QtWidgets.QSpinBox()
        self.num_images.setValue(32)
        self.num_images.setMinimum(8)

        self.radius = QtWidgets.QDoubleSpinBox()
        self.radius.setValue(0.225)
        self.radius.setSingleStep(0.025)
        self.radius.setDecimals(3)

        self.padding = QtWidgets.QDoubleSpinBox()
        self.padding.valueChanged.connect(self.grid_attr_changed('padding'))
        self.padding.setValue(0.2)
        self.padding.setSingleStep(0.025)
        self.padding.setDecimals(3)

        control_layout = QtWidgets.QGridLayout()
        control_layout.setContentsMargins(20, 20, 20, 20)
        control_layout.addWidget(row_label, 0, 0)
        control_layout.addWidget(self.rows, 0, 1)
        control_layout.addWidget(column_label, 1, 0)
        control_layout.addWidget(self.columns, 1, 1)
        control_layout.addWidget(num_images_label, 2, 0)
        control_layout.addWidget(self.num_images, 2, 1)
        control_layout.addWidget(radius_label, 3, 0)
        control_layout.addWidget(self.radius, 3, 1)
        control_layout.addWidget(padding_label, 4, 0)
        control_layout.addWidget(self.padding, 4, 1)

        self.generate_base_flaps = QtWidgets.QPushButton('Generate Base Flaps')
        self.generate_wall = QtWidgets.QPushButton('Generate Wall')

        button_layout = QtWidgets.QGridLayout()
        button_layout.setContentsMargins(20, 20, 20, 20)
        button_layout.addWidget(self.generate_base_flaps, 0, 0)
        button_layout.addWidget(self.generate_wall, 0, 1)

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.setWindowTitle('Split Flap Display Builder')
        layout.addWidget(self.grid)
        layout.addLayout(control_layout)
        layout.addLayout(button_layout)

    def grid_attr_changed(self, attr):

        def change_value():
            setattr(self.grid, attr, getattr(self, attr).value())
        return change_value


class ProgressBar(object):

    _instance = None
    _suppress = True

    @classmethod
    def suppress(cls, value):
        cls._suppress = value

    @classmethod
    def create(self, parent=None):
        dialog = QtWidgets.QDialog(parent=parent)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        dialog.setLayout(layout)
        dialog.setFixedSize(300, 100)

        dialog.progress_bar = QtWidgets.QProgressBar()
        dialog.progress_bar.setMinimum(0)
        dialog.progress_bar.setMaximum(100)
        dialog.label = QtWidgets.QLabel()

        layout.addWidget(dialog.progress_bar)
        layout.addWidget(dialog.label)

        return dialog

    @classmethod
    def set_title(cls, title):
        if cls._suppress:
            return
        cls._instance.setWindowTitle(title)

    @classmethod
    def set(cls, value, text=None):
        if cls._suppress:
            return
        cls._instance.progress_bar.setValue(value)
        if text:
            cls._instance.label.setText(text)

    @classmethod
    def set_maximum(cls, value):
        if cls._suppress:
            return
        cls._instance.progress_bar.setMaximum(value)

    @classmethod
    def show(cls):
        if cls._suppress:
            return
        cls._instance.show()

    @classmethod
    def hide(cls, delay=1):
        if cls._suppress:
            return
        QtCore.QTimer.singleShot(delay * 1000, cls._instance.hide)

    @classmethod
    def setup(cls, title, text, maximum, parent=None):
        if cls._suppress:
            return
        if not cls._instance:
            cls._instance = cls.create(parent=parent)

        cls.set_title(title)
        cls.set_maximum(maximum)
        cls.set(0, text)
        cls._instance.show()
        return cls._instance


if __name__ == '__main__':
    import signal
    import sys
    import time
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QtWidgets.QApplication(sys.argv)

    def test_progressbar():
        ProgressBar.suppress(False)
        ProgressBar.setup('Amazing', 'doing things...', 1000)
        for i in range(1000):
            ProgressBar.set(i + 1, 'doing thing {}'.format(i))
            time.sleep(0.05)
            app.processEvents()
        ProgressBar.show()

    def test_dialog():
        dialog = Dialog()
        dialog.show()

    test_dialog()
    sys.exit(app.exec_())
