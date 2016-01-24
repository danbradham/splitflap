from __future__ import division
import math
from collections import defaultdict
from itertools import permutations
from PySide import QtGui, QtCore


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


class GridWidget(QtGui.QWidget):
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
        for y in xrange(self.rows):
            for x in xrange(self.columns):
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
        font.setStyleHint(QtGui.QFont.Fantasy)
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
            for l in lines:
                painter.drawLine(*l)

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
        for l in lines:
            a_painter.drawLine(*l)

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


class Dialog(QtGui.QDialog):

    def __init__(self, parent=None):
        super(Dialog, self).__init__(parent)

        self.grid = GridWidget(
            rows=3,
            columns=4,
            width=2,
            height=3,
            padding=0.2,
        )
        self.grid.setMinimumSize(300, 300)

        row_label = QtGui.QLabel('rows')
        row_label.setAlignment(QtCore.Qt.AlignRight)

        column_label = QtGui.QLabel('columns')
        column_label.setAlignment(QtCore.Qt.AlignRight)

        num_images_label = QtGui.QLabel('num_images')
        num_images_label.setAlignment(QtCore.Qt.AlignRight)

        radius_label = QtGui.QLabel('radius')
        radius_label.setAlignment(QtCore.Qt.AlignRight)

        padding_label = QtGui.QLabel('padding')
        padding_label.setAlignment(QtCore.Qt.AlignRight)

        self.rows = QtGui.QSpinBox()
        self.rows.setMinimum(1)
        self.rows.setValue(3)
        self.rows.valueChanged.connect(self.grid_attr_changed('rows'))

        self.columns = QtGui.QSpinBox()
        self.columns.setMinimum(1)
        self.columns.setValue(4)
        self.columns.valueChanged.connect(self.grid_attr_changed('columns'))

        self.num_images = QtGui.QSpinBox()
        self.num_images.setMinimum(12)

        self.radius = QtGui.QDoubleSpinBox()
        self.radius.setSingleStep(0.025)

        self.padding = QtGui.QDoubleSpinBox()
        self.padding.valueChanged.connect(self.grid_attr_changed('padding'))
        self.padding.setValue(0.2)
        self.padding.setSingleStep(0.025)

        control_layout = QtGui.QGridLayout()
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

        self.generate_base_flaps = QtGui.QPushButton('Generate Base Flaps')
        self.generate_wall = QtGui.QPushButton('Generate Wall')

        button_layout = QtGui.QGridLayout()
        button_layout.setContentsMargins(20, 20, 20, 20)
        button_layout.addWidget(self.generate_base_flaps, 0, 0)
        button_layout.addWidget(self.generate_wall, 0, 1)

        layout = QtGui.QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.grid)
        layout.addLayout(control_layout)
        layout.addLayout(button_layout)

    def grid_attr_changed(self, attr):

        def change_value():
            setattr(self.grid, attr, getattr(self, attr).value())
        return change_value

if __name__ == '__main__':
    import signal
    import sys
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QtGui.QApplication(sys.argv)
    d = Dialog()
    d.show()
    sys.exit(app.exec_())
