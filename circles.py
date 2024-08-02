import math

from PyQt6.QtCore import QPoint, QTimer, Qt
from PyQt6.QtGui import QColor, QFont, QPaintDevice, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class _QPoint(QPoint):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def to_tuple(self) -> tuple[int, int]:
        return self.x(), self.y()


QPoint = _QPoint


class Circle:
    def __init__(self, radius: int = 20, color: QColor = QColor("black")) -> None:
        self._radius: int = radius

        self._color: QColor = color

        self._pos: QPoint = QPoint(0, 0)

    def get_radius(self) -> int:
        return self._radius

    def set_radius(self, radius: int) -> None:
        self._radius = radius

    def get_color(self) -> QColor:
        return self._color

    def set_color(self, color: QColor) -> None:
        self._color = color

    def get_pos(self) -> QPoint:
        return self._pos

    def set_pos(self, pos: QPoint) -> None:
        self._pos = pos


class CircularMove:
    _period: float
    _angular_velocity: float
    _velocity: float
    _acceleration: float

    def __init__(self, radius: int, period: float, subject: Circle) -> None:
        self._radius: int = radius

        self.set_period(period)

        self._subject: Circle = subject

    def set_radius(self, radius: int) -> None:
        self._radius = radius

    def get_period(self) -> float:
        return self._period

    def set_period(self, period: float) -> None:
        self._period = period

        self._angular_velocity = 2 * math.pi / period
        self._velocity = self._angular_velocity * self._radius
        self._acceleration = self._angular_velocity**2 * self._radius

    def get_angular_velocity(self) -> float:
        return self._angular_velocity

    def recalculate_subject_pos(self, time: float) -> None:
        point: QPoint = QPoint(
            int(self._radius * math.cos(self._angular_velocity * time)),
            int(self._radius * math.sin(self._angular_velocity * time)),
        )

        self._subject.set_pos(point)


class Hypocycloid:
    def __init__(self, outer_circle: Circle, inner_circle: Circle) -> None:
        self._outer_circle: Circle = outer_circle
        self._inner_circle: Circle = inner_circle

        self._hypocycloid_point: QPoint = QPoint(0, 0)

    def get_hypocycloid_point(self) -> QPoint:
        return self._hypocycloid_point

    def _get_k(self) -> float:
        return self._outer_circle.get_radius() / self._inner_circle.get_radius()

    def recalculate_hypocycloid_point(
        self, angular_velocity: float, time: float
    ) -> None:
        self._hypocycloid_point = QPoint(
            int(
                self._inner_circle.get_radius()
                * (self._get_k() - 1)
                * math.cos(angular_velocity * time)
                + self._inner_circle.get_radius()
                * math.cos((self._get_k() - 1) * angular_velocity * time)
            ),
            int(
                self._inner_circle.get_radius()
                * (self._get_k() - 1)
                * math.sin(angular_velocity * time)
                - self._inner_circle.get_radius()
                * math.sin((self._get_k() - 1) * angular_velocity * time)
            ),
        )


class Canvas(QLabel):
    size: tuple[int, int] = (720, 480)
    _background_color: tuple[int, int, int] = (255, 240, 240)

    def __init__(
        self,
        outer_circle: Circle,
        inner_circle: Circle,
        hypocycloid: Hypocycloid,
        *args,
        **kwargs,
    ):
        super(Canvas, self).__init__(*args, **kwargs)

        self.setFixedSize(*Canvas.size)

        _canvas: QPixmap = QPixmap(*Canvas.size)
        _canvas.fill(QColor(*Canvas._background_color))

        self.hypocycloid_canvas: QPixmap = QPixmap(*Canvas.size)
        self.hypocycloid_canvas.fill(QColor(0, 0, 0, 0))

        self.setPixmap(_canvas)

        self.outer_circle: Circle = outer_circle
        self.inner_circle: Circle = inner_circle
        self.hypocycloid: Hypocycloid = hypocycloid
        self.interactive: bool = True
        self.show_hypocycloid: bool = False

        self.redraw_timeout()

    def clear(self):
        canvas = self.pixmap()
        canvas.fill(QColor(*Canvas._background_color))
        self.setPixmap(canvas)

    def redraw_timeout(self):
        self.clear()

        canvas: QPixmap = self.pixmap()
        painter: QPainter = Canvas.construct_painter(
            self.inner_circle.get_color(), canvas
        )

        outer_circle_diameter: int = self.outer_circle.get_radius() * 2
        outer_circle_pos = Canvas.get_absolute_pos(
            self.outer_circle.get_pos(), (outer_circle_diameter, outer_circle_diameter)
        )

        painter.drawEllipse(
            *outer_circle_pos.to_tuple(), outer_circle_diameter, outer_circle_diameter
        )

        inner_circle_diameter: int = self.inner_circle.get_radius() * 2
        inner_circle_pos = Canvas.get_absolute_pos(
            self.inner_circle.get_pos(), (inner_circle_diameter, inner_circle_diameter)
        )

        painter.drawEllipse(
            *inner_circle_pos.to_tuple(), inner_circle_diameter, inner_circle_diameter
        )

        hypocycloid_point_diameter: int = 5
        hypocycloid_point_pos: QPoint = Canvas.get_absolute_pos(
            self.hypocycloid.get_hypocycloid_point(),
            (hypocycloid_point_diameter, hypocycloid_point_diameter),
        )
        painter.drawEllipse(
            *hypocycloid_point_pos.to_tuple(),
            hypocycloid_point_diameter,
            hypocycloid_point_diameter,
        )

        inner_circle_center_pos: QPoint = QPoint(
            inner_circle_pos.x() + self.inner_circle.get_radius(),
            inner_circle_pos.y() + self.inner_circle.get_radius(),
        )
        hypocycloid_point_center_pos: QPoint = QPoint(
            hypocycloid_point_pos.x() + int(hypocycloid_point_diameter / 2),
            hypocycloid_point_pos.y() + int(hypocycloid_point_diameter / 2),
        )
        painter.drawLine(
            *inner_circle_center_pos.to_tuple(),
            *hypocycloid_point_center_pos.to_tuple(),
        )

        hypocycloid_painter = Canvas.construct_painter(
            QColor("red"), self.hypocycloid_canvas
        )
        hypocycloid_painter.drawEllipse(*hypocycloid_point_pos.to_tuple(), 3, 3)
        hypocycloid_painter.end()

        if self.show_hypocycloid:
            painter.drawPixmap(0, 0, self.hypocycloid_canvas)

        painter.end()
        self.setPixmap(canvas)

    def clear_hypocycloid_canvas(self):
        self.hypocycloid_canvas.fill(QColor(0, 0, 0, 0))

    @staticmethod
    def get_absolute_pos(
        relative_pos: QPoint, subject_size: tuple[float, float]
    ) -> QPoint:
        return QPoint(
            relative_pos.x() + int((Canvas.size[0] - subject_size[0]) / 2),
            int((Canvas.size[1] - subject_size[1]) / 2) - relative_pos.y(),
        )

    @staticmethod
    def construct_painter(
        color: QColor, paint_device: QPaintDevice, width: int = 4
    ) -> QPainter:
        painter = QPainter(paint_device)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine))

        return painter


class InfoDialog(QDialog):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Справка")

        button = QDialogButtonBox.StandardButton.Ok

        self.buttonBox = QDialogButtonBox(button)
        self.buttonBox.accepted.connect(self.accept)  # noqa

        self.layout = QVBoxLayout()

        central_label: QLabel = QLabel(
            """
Эта программа является симуляцией качения малой окружности C радиуса r (изменяемая величина)
по внутренней стороне большой окружности M радиуса R = 240 пикселей (R > r).

Управление:
    1. Кнопка \"Запустить\" запускает симуляцию: центр окружности C (точка O) начинает равномерное
        движение по окружности CM радиуса R' = R - r.
    2. Кнопка \"Остановить\" приостанавливает симуляцию, сохраняя положение окружности C.
    3. Ползунок \"Радиус внутренней окружности\" позволяет изменить радиус внутренней окружности r
        в пределах от 20 до 200 пикселей с шагом 1 пиксель.
    4. Ползунок \"Период вращения внутренней окружности\" позволяет изменить период T движения
        окружности C в пределах от 3 до 10 секунд с шагом 1 секунда. Этот период показывает, какое
        время затратит малая окружность C на полный круг движения по внутренней стороне большой окружности M.
    5. Галочка \"Показывать гипоциклоиду\" включает режим отображения гипоциклоиды - линии,
        описывающей движение отдельной точки на окружности C.
    6. Галочка \"Движение по часовой стрелке\" инвертирует направление качения окружности C.

Принцип работы:
    1. Перерисовка холста происходит каждую 1 / 240 часть секунды, т.е программа работает на 240 кадрах
        в секунду.
    2. За время dt = 1 / 240 секунд центр окружности C смещается из точки O в точку O' с координатами:

        x' = R' * cos(w * t');
        y' = R' * sin(w * t');

        где R' = R - r (радиус окружности, по которой движется точка O);
            w = 2 * pi / T (угловая скорость точки O);
            t' = t + dt (время, прошедшее с начала симуляции).
    3. За время dt точка A, принадлежащая окружности C, смещается в точку A' с координатами:

        u' = r * (k - 1) * cos(w * t') + r * cos((k - 1) * w * t');
        v' = r * (k - 1) * sin(w * t') - r * sin((k - 1) * w * t');

        где k = R / r (отношение радиусов внешней окружности M и внутренней окружности C).
        """
        )

        font: QFont = QFont("Monospace", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)

        central_label.setFont(font)
        central_label.setStyleSheet("QLabel {margin: auto;}")

        self.layout.addWidget(central_label)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class Circles(QMainWindow):
    def __init__(self):
        super(Circles, self).__init__()

        self.repaint_time: float = 0.0

        self.setWindowTitle("2.21 Внутреннее качение окружности по окружности")
        self.setFixedSize(1280, 720)

        all_widgets = QVBoxLayout()

        central_widgets = QHBoxLayout()

        outer_circle: Circle = Circle(
            radius=int(Canvas.size[1] / 2), color=QColor("black")
        )
        inner_circle: Circle = Circle(radius=60, color=QColor("black"))

        self.circular_mover: CircularMove = CircularMove(
            radius=outer_circle.get_radius() - inner_circle.get_radius(),
            period=5.0,
            subject=inner_circle,
        )
        self.circular_mover.recalculate_subject_pos(0.0)

        self.hypocycloid: Hypocycloid = Hypocycloid(outer_circle, inner_circle)
        self.hypocycloid.recalculate_hypocycloid_point(
            self.circular_mover.get_angular_velocity(), 0.0
        )

        self.canvas = Canvas(outer_circle, inner_circle, self.hypocycloid)

        left_widgets = QVBoxLayout()
        left_widgets.setSpacing(20)
        left_widgets.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setGeometry(50, 50, 200, 50)
        self.size_slider.setValue(60)
        self.size_slider.setMinimum(20)
        self.size_slider.setMaximum(200)
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.size_slider.setTickInterval(10)
        self.size_slider.valueChanged.connect(self.size_changed)  # noqa

        self.size_slider_label = QLabel(
            f"Радиус внутренней окружности: {self.size_slider.value()}px"
        )
        self.size_slider_label.setWordWrap(True)
        self.size_slider_label.setStyleSheet(
            "QLabel {margin: auto; padding: 10px; font-size: 18px;}"
        )

        self.period_slider = QSlider(Qt.Orientation.Horizontal)
        self.period_slider.setGeometry(50, 50, 200, 50)
        self.period_slider.setValue(5)
        self.period_slider.setMinimum(3)
        self.period_slider.setMaximum(10)
        self.period_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.period_slider.setTickInterval(1)
        self.period_slider.valueChanged.connect(self.period_changed)  # noqa

        self.period_slider_label = QLabel(
            f"Период вращения внутренней окружности: {self.period_slider.value()}с"
        )
        self.period_slider_label.setWordWrap(True)
        self.period_slider_label.setStyleSheet(
            "QLabel {margin: auto; padding: 10px; font-size: 18px;}"
        )

        left_widgets.addWidget(self.size_slider_label)
        left_widgets.addWidget(self.size_slider)
        left_widgets.addWidget(self.period_slider_label)
        left_widgets.addWidget(self.period_slider)

        right_widgets = QVBoxLayout()
        right_widgets.setSpacing(20)
        right_widgets.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.start_button = QPushButton("Запустить")
        self.start_button.clicked.connect(self.start_timer)  # noqa
        self.start_button.setStyleSheet(
            "QPushButton {margin: auto; padding: 10px; font-size: 18px;}"
        )

        self.stop_button = QPushButton("Остановить")
        self.stop_button.clicked.connect(self.stop_timer)  # noqa
        self.stop_button.setStyleSheet(
            "QPushButton {margin: auto; padding: 10px; font-size: 18px;}"
        )

        self.info_button = QPushButton("Справка")
        self.info_button.clicked.connect(self.show_info)  # noqa
        self.info_button.setStyleSheet(
            "QPushButton {margin: auto; padding: 10px; font-size: 18px;}"
        )

        self.stop_button.setEnabled(False)

        right_widgets.addWidget(self.start_button)
        right_widgets.addWidget(self.stop_button)
        right_widgets.addWidget(self.info_button)

        central_widgets.addLayout(left_widgets)
        central_widgets.addWidget(self.canvas)
        central_widgets.addLayout(right_widgets)

        bottom_widgets = QHBoxLayout()
        bottom_widgets.setSpacing(20)
        bottom_widgets.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.line_check_box = QCheckBox("Показывать гипоциклоиду")
        self.line_check_box.clicked.connect(self.line_toggle)  # noqa
        self.line_check_box.setStyleSheet(
            "QCheckBox {margin: auto; padding: 10px; font-size: 18px;}"
        )

        self.motion_direction_clockwise: bool = False
        self.motion_direction_check_box = QCheckBox("Движение по часовой стрелке")
        self.motion_direction_check_box.clicked.connect(  # noqa
            self.motion_direction_changed
        )
        self.motion_direction_check_box.setStyleSheet(
            "QCheckBox {margin: auto; padding: 10px; font-size: 18px;}"
        )

        bottom_widgets.addWidget(self.line_check_box)
        bottom_widgets.addWidget(self.motion_direction_check_box)

        all_widgets.addLayout(central_widgets)
        all_widgets.addLayout(bottom_widgets)

        container = QWidget()
        container.setLayout(all_widgets)

        self.setCentralWidget(container)

        self.timer = QTimer(self)

        self.timer.timeout.connect(self.repaint_timeout)  # noqa

    def start_timer(self):
        self.timer.start(int(1000 / 240))
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    @staticmethod
    def show_info():
        InfoDialog().exec()

    def size_changed(self):
        self.canvas.clear_hypocycloid_canvas()
        self.canvas.inner_circle.set_radius(value := self.size_slider.value())

        self.circular_mover.set_radius(
            self.canvas.outer_circle.get_radius()
            - self.canvas.inner_circle.get_radius()
        )

        self.size_slider_label.setText(f"Радиус внутренней окружности: {value}px")

        time: float = self.repaint_time / 1000

        self.circular_mover.recalculate_subject_pos(time)
        self.hypocycloid.recalculate_hypocycloid_point(
            self.circular_mover.get_angular_velocity(), time
        )
        self.canvas.redraw_timeout()

    def period_changed(self):
        self.canvas.clear_hypocycloid_canvas()

        self.repaint_time = 0.0

        value = self.period_slider.value()
        if self.motion_direction_clockwise:
            value = -value

        self.circular_mover.set_period(value)

        self.period_slider_label.setText(
            f"Период вращения внутренней окружности: {abs(value)}с"
        )

        time: float = 0.0

        self.circular_mover.recalculate_subject_pos(time)
        self.hypocycloid.recalculate_hypocycloid_point(
            self.circular_mover.get_angular_velocity(), time
        )
        self.canvas.redraw_timeout()

    def line_toggle(self):
        self.canvas.show_hypocycloid = self.line_check_box.isChecked()
        self.canvas.redraw_timeout()

    def motion_direction_changed(self):
        self.motion_direction_clockwise = self.motion_direction_check_box.isChecked()

        self.period_changed()

    def repaint_timeout(self):
        self.repaint_time += 1000 / 240

        time: float = self.repaint_time / 1000

        self.circular_mover.recalculate_subject_pos(time)
        self.hypocycloid.recalculate_hypocycloid_point(
            self.circular_mover.get_angular_velocity(), time
        )
        self.canvas.redraw_timeout()

    def stop_timer(self):
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)


if __name__ == "__main__":
    app = QApplication([])

    window = Circles()
    window.show()

    app.exec()
