from random import randint
from typing import Callable, TypeVar, Tuple, List, Optional

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QMouseEvent,
    QPaintDevice,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QDialog,
)
from shapely.geometry import LineString

QPolygon = TypeVar("QPolygon", bound=List[QPoint])
OnClearCallback = TypeVar("OnClearCallback", bound=Callable[[], None])
OnNewPointCallback = TypeVar("OnNewPointCallback", bound=Callable[[QPoint], None])
OnPolygonCallback = TypeVar("OnPolygonCallback", bound=Callable[[List[QPoint]], None])


class Dialog(QDialog):
    def __init__(self, title: str = "Ошибка!", message: str = "Непредвиденная ошибка!"):
        super().__init__()

        self.setWindowTitle(title)

        button = QDialogButtonBox.StandardButton.Ok

        self.buttonBox = QDialogButtonBox(button)
        self.buttonBox.accepted.connect(self.accept)

        self.layout = QVBoxLayout()

        message = QLabel(message)
        message.setStyleSheet("QLabel {font-size: 16pt; margin: auto;}")

        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class Canvas(QLabel):
    size: Tuple[int, int] = (720, 480)
    background_color: Tuple[int, int, int] = (42, 42, 42)

    first_polygon_color: QColor
    second_polygon_color: QColor

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super(Canvas, self).__init__(*args, **kwargs)

        self.setFixedSize(*Canvas.size)

        canvas: QPixmap = QPixmap(*Canvas.size)
        canvas.fill(QColor(*Canvas.background_color))

        self.setPixmap(canvas)

        self.set_random_color()

        self.place_grid()

        self.previous_point: Optional[QPoint] = None
        self.dragging_point: Optional[QPoint] = None

        self.first_polygon: Optional[QPolygon] = list()
        self.second_polygon: Optional[QPolygon] = list()

        self.current_polygon: Optional[QPolygon] = self.first_polygon

    def place_grid(self, grid_step: int = 30) -> None:
        canvas = self.pixmap()
        painter = construct_painter(QColor(100, 100, 100, alpha=40), canvas, 2)

        for i in range(grid_step, Canvas.size[1], grid_step):
            painter.drawLine(QPoint(0, i), QPoint(Canvas.size[0], i))

        for i in range(grid_step, Canvas.size[0], grid_step):
            painter.drawLine(QPoint(i, 0), QPoint(i, Canvas.size[1]))

        painter.end()
        self.setPixmap(canvas)

    def set_random_color(self) -> None:
        self.first_polygon_color = QColor(
            randint(0, 220), randint(0, 220), randint(0, 220)
        )

        self.second_polygon_color = QColor(
            randint(0, 220), randint(0, 220), randint(0, 220)
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        color = (
            self.first_polygon_color
            if self.current_polygon is self.first_polygon
            else self.second_polygon_color
        )

        canvas: QPixmap = self.pixmap()
        painter: QPainter = construct_painter(color, canvas)

        def is_close(p: QPoint, q: QPoint, r: float) -> bool:
            d: QPoint = p - q

            return d.x() ** 2 + d.y() ** 2 <= r**2

        if event.button() == Qt.MouseButton.LeftButton:
            closest_point: Optional[QPoint] = None
            for previous_point in (*self.first_polygon, *self.second_polygon):
                if is_close(event.pos(), previous_point, 5):
                    closest_point = previous_point

                    break

            if closest_point is not None:
                self.set_drag_point(closest_point)
            elif self.current_polygon is not None:
                self.add_point(event.pos(), painter)
        elif (
            event.button() == Qt.MouseButton.RightButton
            and self.current_polygon is not None
        ):
            self.close_polygon(painter)

        painter.end()
        self.setPixmap(canvas)

        if self.current_polygon is None:
            self.calculate_intersections()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.dragging_point is None:
            return

        canvas = self.pixmap()
        canvas.fill(QColor(*Canvas.background_color))
        self.setPixmap(canvas)
        self.place_grid()

        for polygon in (self.first_polygon, self.second_polygon):
            self.redraw_polygon(polygon, event.pos())

        if self.current_polygon is None:
            self.calculate_intersections()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.dragging_point is not None:
            self.dragging_point = None

    def redraw_polygon(self, polygon: QPolygon, new_point: QPoint) -> None:
        color = (
            self.first_polygon_color
            if polygon is self.first_polygon
            else self.second_polygon_color
        )

        canvas = self.pixmap()
        painter: QPainter = construct_painter(color, canvas)

        previous_point: Optional[QPoint] = None
        for index, point in enumerate(polygon.copy()):
            if point is self.dragging_point:
                point.setX(new_point.x())
                point.setY(new_point.y())

            painter.drawEllipse(point, 2, 2)
            if previous_point is not None:
                painter.drawLine(previous_point, point)

            previous_point = point

        if self.current_polygon is not polygon and len(polygon) != 0:
            painter.drawLine(previous_point, polygon[0])

        painter.end()
        self.setPixmap(canvas)

    def add_point(self, point: QPoint, painter: QPainter) -> None:
        painter.drawEllipse(point, 2, 2)

        if self.previous_point is not None:
            painter.drawLine(self.previous_point, point)

        self.current_polygon.append(point)
        self.previous_point = point

    def close_polygon(self, painter: QPainter) -> None:
        if len(self.current_polygon) >= 3:
            first_point: QPoint = QPoint(self.current_polygon[0])
            painter.drawLine(self.previous_point, first_point)

            self.next_polygon()
        else:
            Dialog(
                message="Недостаточно точек для закрытия полигона. Их должно быть не менее 3."
            ).exec()

    def set_drag_point(self, point: QPoint) -> None:
        self.dragging_point = point

    def calculate_intersections(self) -> None:
        intersections: List[QPoint] = list()

        polygons: List[List[LineString]] = list()

        for polygon in self.first_polygon, self.second_polygon:
            polygons.append(current_sections := list())

            previous_point: Tuple[int, int] = polygon[0].x(), polygon[0].y()

            for point in polygon[1:]:
                current_point: Tuple[int, int] = point.x(), point.y()

                current_sections.append(LineString([previous_point, current_point]))

                previous_point = current_point

            current_point: Tuple[int, int] = polygon[0].x(), polygon[0].y()
            current_sections.append(LineString([previous_point, current_point]))

        for first_section in polygons[0]:
            for second_section in polygons[1]:
                if intersection := first_section.intersection(second_section):
                    intersections.append(
                        QPoint(int(intersection.x), int(intersection.y))
                    )

        canvas = self.pixmap()
        painter = construct_painter(QColor("red"), canvas, 10)

        for intersection in intersections:
            painter.drawPoint(intersection)

        painter.end()
        self.setPixmap(canvas)

    def clear(self) -> None:
        canvas = self.pixmap()
        canvas.fill(QColor(*Canvas.background_color))
        self.setPixmap(canvas)

        self.place_grid()

        self.first_polygon.clear()
        self.second_polygon.clear()

        self.current_polygon = self.first_polygon

        self.previous_point = None

    def next_polygon(self) -> None:
        # points: List[Tuple[int, int]] = list()
        # for point in self.points:
        #     points.append((point.x(), point.y()))

        if self.current_polygon is self.first_polygon:
            self.current_polygon = self.second_polygon
        else:
            self.current_polygon = None

        self.previous_point = None


def construct_painter(
    color: QColor, paint_device: QPaintDevice, width: int = 4
) -> QPainter:
    painter = QPainter(paint_device)

    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine))
    painter.setBrush(QBrush(color, Qt.BrushStyle.SolidPattern))

    return painter


class Polygons(QMainWindow):
    def __init__(self):
        super(Polygons, self).__init__()

        self.setWindowTitle("Полигоны")
        self.setFixedSize(1280, 720)

        all_widgets = QVBoxLayout()

        central_widgets = QHBoxLayout()

        self.canvas = Canvas()

        right_widgets = QVBoxLayout()
        right_widgets.setSpacing(20)
        right_widgets.setAlignment(Qt.AlignmentFlag.AlignCenter)

        clear_button = QPushButton("Очистить холст")
        clear_button.clicked.connect(self.canvas.clear)
        clear_button.setStyleSheet(
            "QPushButton {margin: auto; padding: 5px; font-size: 24px;}"
        )

        info_button = QPushButton("Справка")
        info_button.clicked.connect(self.info_clicked)
        info_button.setStyleSheet(
            "QPushButton {margin: auto; padding: 5px; font-size: 24px;}"
        )

        right_widgets.addWidget(clear_button)
        right_widgets.addWidget(info_button)

        central_widgets.addWidget(self.canvas)
        central_widgets.addLayout(right_widgets)

        all_widgets.addLayout(central_widgets)

        container = QWidget()
        container.setLayout(all_widgets)

        self.setCentralWidget(container)

    @staticmethod
    def info_clicked():
        dialog = Dialog(
            "Справка",
            """1. По центру Вы видите сетчатое поле - на нём можно расставлять точки левой кнопкой мыши.
2. Чтобы замкнуть полигон, нажмите в любом месте поля правой кнопкой мыши.
3. Точки можно перетаскивать нажав левой кнопкой мыши на них и не отпуская клавишу двигать мышкой.
4. Новое положение точки будет учтено как точка, в которой Вы отпустите клавишу.
5. Кнопка \"Очистить холст\" уберёт с поля все точки и позволит Вам нарисовать их заново.""",
        )
        dialog.exec()


if __name__ == "__main__":
    app = QApplication([])

    window = Polygons()
    window.show()

    app.exec()
