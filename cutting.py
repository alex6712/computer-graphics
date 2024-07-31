from random import randint
from typing import Tuple, List, Optional, TypeVar

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QMouseEvent,
    QPaintDevice,
    QPainter,
    QPen,
    QPixmap,
    QFont,
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


class _QPoint(QPoint):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def to_tuple(self) -> tuple[int, int]:
        return self.x(), self.y()


QPoint = _QPoint


class Dialog(QDialog):
    def __init__(self, title: str = "Ошибка", message: str = "Непредвиденная ошибка!"):
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

    polygon_color: QColor

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

        self.polygon: QPolygon = list()

        self.polygon_closed: bool = False

    def place_grid(self, grid_step: int = 30) -> None:
        canvas = self.pixmap()
        painter = Canvas.construct_painter(QColor(100, 100, 100, alpha=40), canvas, 2)

        for i in range(grid_step, Canvas.size[1], grid_step):
            painter.drawLine(QPoint(0, i), QPoint(Canvas.size[0], i))

        for i in range(grid_step, Canvas.size[0], grid_step):
            painter.drawLine(QPoint(i, 0), QPoint(i, Canvas.size[1]))

        painter.end()
        self.setPixmap(canvas)

    def set_random_color(self) -> None:
        self.polygon_color = QColor(
            randint(63, 220), randint(63, 220), randint(63, 220)
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        canvas: QPixmap = self.pixmap()
        painter: QPainter = Canvas.construct_painter(self.polygon_color, canvas)

        def is_close(p: QPoint, q: QPoint, r: float) -> bool:
            d: QPoint = p - q

            return d.x() ** 2 + d.y() ** 2 <= r**2

        if event.button() == Qt.MouseButton.LeftButton:
            closest_point: Optional[QPoint] = None
            for previous_point in self.polygon:
                if is_close(event.pos(), previous_point, 5):
                    closest_point = previous_point

                    break

            if closest_point is not None:
                self.set_drag_point(closest_point)
            else:
                if self.polygon_closed:
                    Dialog(
                        "Полигон закрыт",
                        "Полигон закрыт: невозможно поставить ещё одну точку.",
                    ).exec()
                else:
                    self.add_point(QPoint(event.pos()), painter)
        elif event.button() == Qt.MouseButton.RightButton:
            self.close_polygon(painter)

        painter.end()
        self.setPixmap(canvas)

        if self.polygon_closed:
            self.cut_polygon()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.dragging_point is None:
            return

        canvas = self.pixmap()
        canvas.fill(QColor(*Canvas.background_color))
        self.setPixmap(canvas)
        self.place_grid()

        self.redraw_polygon(self.polygon, event.pos())

        self.cut_polygon()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.dragging_point is not None:
            self.dragging_point = None

    def redraw_polygon(self, polygon: QPolygon, new_point: QPoint) -> None:
        canvas = self.pixmap()
        painter: QPainter = Canvas.construct_painter(self.polygon_color, canvas)

        previous_point: Optional[QPoint] = None
        for index, point in enumerate(polygon):
            if point is self.dragging_point:
                point.setX(new_point.x())
                point.setY(new_point.y())

            painter.drawEllipse(point, 2, 2)
            if previous_point is not None:
                painter.drawLine(previous_point, point)

            previous_point = point

        if self.polygon_closed:
            painter.drawLine(previous_point, polygon[0])

        painter.end()
        self.setPixmap(canvas)

    def add_point(self, point: QPoint, painter: QPainter) -> None:
        if self.check_for_intersections(point):
            Dialog(
                "Проверка на самопересечения",
                "Точка, которую Вы хотите поставить, приведёт к самопересечению многоугольника.",
            ).exec()

            return

        painter.drawEllipse(point, 2, 2)

        if self.previous_point is not None:
            painter.drawLine(self.previous_point, point)

        self.polygon.append(point)
        self.previous_point = point

    def close_polygon(self, painter: QPainter) -> None:
        if self.polygon_closed:
            Dialog(
                "Полигон закрыт",
                "Невозможно закрыть полигон: полигон уже закрыт!",
            ).exec()

            return

        if self.check_for_intersections(self.polygon[0]):
            Dialog(
                "Проверка на самопересечения",
                "Закрытие полигона сейчас приведёт к самопересечению. "
                "Измените геометрию полигона и повторите попытку.",
            ).exec()

            return

        if len(self.polygon) >= 4:
            first_point: QPoint = QPoint(self.polygon[0])

            painter.drawLine(first_point, self.previous_point)

            self.polygon_closed = True
        else:
            Dialog(
                message="Недостаточно точек для закрытия полигона. Их должно быть не менее 4."
            ).exec()

    def set_drag_point(self, point: QPoint) -> None:
        self.dragging_point = point

    def cut_polygon(self) -> None:
        diagonals: List[Tuple[QPoint, QPoint]] = list()

        for first_index, first_point in enumerate(self.polygon):
            for second_point in self.polygon[first_index + 2 :]:
                if {first_point, second_point} == {self.polygon[0], self.polygon[-1]}:
                    continue

                if self.check_for_intersections(first_point, second_point):
                    continue

                diagonals.append((first_point, second_point))

        canvas = self.pixmap()
        painter = Canvas.construct_painter(QColor("red"), canvas)

        for diagonal in diagonals:
            painter.drawLine(diagonal[0], diagonal[1])

        painter.end()
        self.setPixmap(canvas)

    def check_for_intersections(
        self, new_point: QPoint, start_point: QPoint = None
    ) -> bool:
        if len(self.polygon) < 3:
            return False

        edges: List[LineString] = list()

        previous_point: Tuple[int, int] = self.polygon[0].to_tuple()

        for point in self.polygon[1:]:
            current_point: Tuple[int, int] = point.to_tuple()

            edges.append(LineString([previous_point, current_point]))

            previous_point = current_point

        if start_point is not None:
            previous_point = start_point.to_tuple()

        new_edge: LineString = LineString([previous_point, new_point.to_tuple()])

        for edge in edges:
            if intersection := new_edge.intersection(edge):
                point: QPoint = QPoint(int(intersection.x), int(intersection.y))

                if point in self.polygon:
                    continue

                return True

        return False

    def clear(self) -> None:
        canvas = self.pixmap()
        canvas.fill(QColor(*Canvas.background_color))
        self.setPixmap(canvas)

        self.place_grid()

        self.polygon.clear()

        self.previous_point = None
        self.polygon_closed = False

        self.set_random_color()

    def random_polygon(self) -> None:
        self.clear()

        canvas: QPixmap = self.pixmap()
        painter: QPainter = Canvas.construct_painter(self.polygon_color, canvas)

        vertex_number: int = randint(4, 8)

        def is_close(p: QPoint, q: QPoint, r: float) -> bool:
            d: QPoint = p - q

            return d.x() ** 2 + d.y() ** 2 <= r**2

        points: List[QPoint] = list()
        count: int = 0
        while count < vertex_number:
            new_point: QPoint = QPoint(
                randint(0, Canvas.size[0]), randint(0, Canvas.size[1])
            )

            for point in points:
                if is_close(new_point, point, 10):
                    break
            else:
                points.append(new_point)
                count += 1

        leftmost_point: QPoint = points[0]
        rightmost_point: QPoint = points[0]

        for point in points[1:]:
            if point.x() < leftmost_point.x():
                leftmost_point = point

            if point.x() > rightmost_point.x():
                rightmost_point = point

        above_line_points: List[QPoint] = list()
        below_line_points: List[QPoint] = list()

        points.remove(leftmost_point)
        points.remove(rightmost_point)

        for point in points:
            vector_product: int = int(
                (point.x() - leftmost_point.x())
                * (rightmost_point.y() - leftmost_point.y())
                - (point.y() - leftmost_point.y())
                * (rightmost_point.x() - leftmost_point.x())
            )

            if vector_product < 0:
                above_line_points.append(point)
            else:
                below_line_points.append(point)

        above_line_points.sort(key=lambda p: p.x())
        below_line_points.sort(key=lambda p: p.x(), reverse=True)

        for point in (
            leftmost_point,
            *above_line_points,
            rightmost_point,
            *below_line_points,
        ):
            self.add_point(point, painter)

        self.close_polygon(painter)

        painter.end()
        self.setPixmap(canvas)

        self.cut_polygon()

    @staticmethod
    def construct_painter(
        color: QColor, paint_device: QPaintDevice, width: int = 4
    ) -> QPainter:
        painter = QPainter(paint_device)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine))
        painter.setBrush(QBrush(color, Qt.BrushStyle.SolidPattern))

        return painter


class InfoDialog(QDialog):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.setWindowTitle("Справка")

        button = QDialogButtonBox.StandardButton.Ok

        self.buttonBox = QDialogButtonBox(button)
        self.buttonBox.accepted.connect(self.accept)

        self.layout = QVBoxLayout()

        central_label: QLabel = QLabel(
            """
Эта программа реализует функционал триангуляции произвольного многоугольника (полигона) его диагоналями.

Управление:
    1. Нажатие левой кнопки мыши на сетчатом поле поставит вершину полигона в точке нажатия. Вершины
        соединяются рёбрами автоматически в порядке их добавления.
    2. Нажатие правой кнопки мышки в любом месте сетчатого поля моментально замкнёт полигон.
        Полигон возможно замкнуть только если он имеет не менее четырёх вершин (т.к. у полигона
        с тремя вершинами не будет диагоналей). В случае попытки замкнуть полигон с меньшим количеством 
        вершин, Вы увидите сообщение об ошибке.
    3. Зажав левую кнопку мыши рядом с существующей вершиной полигона Вы можете перемещать её.
        Новое положение вершины будет учтено как точка, в которой Вы отпустили левую кнопку мыши.
    5. Кнопка \"Очистить холст\" сотрёт всё содержимое сетчатого поля. После этого полигон будет необходимо
        создать заново.
        """
        )

        font: QFont = QFont("Monospace", 12)
        font.setStyleHint(QFont.StyleHint.Monospace)

        central_label.setFont(font)
        central_label.setStyleSheet("QLabel {margin: auto;}")

        self.layout.addWidget(central_label)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class Cutting(QMainWindow):
    def __init__(self):
        super(Cutting, self).__init__()

        self.setWindowTitle(
            "3.21 Разрезание полигона диагоналями на выпуклые фрагменты"
        )
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

        bottom_widgets = QHBoxLayout()
        bottom_widgets.setSpacing(20)
        bottom_widgets.setAlignment(Qt.AlignmentFlag.AlignCenter)

        random_button = QPushButton("Случайный полигон")
        random_button.clicked.connect(self.canvas.random_polygon)
        random_button.setStyleSheet(
            "QPushButton {margin: auto; padding: 5px; font-size: 24px;}"
        )

        bottom_widgets.addWidget(random_button)

        all_widgets.addLayout(central_widgets)
        all_widgets.addLayout(bottom_widgets)

        container = QWidget()
        container.setLayout(all_widgets)

        self.setCentralWidget(container)

    @staticmethod
    def info_clicked() -> None:
        InfoDialog().exec()


if __name__ == "__main__":
    app = QApplication([])

    window = Cutting()
    window.show()

    app.exec()
