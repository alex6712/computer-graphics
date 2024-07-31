import math
from enum import Enum
from random import randint

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


class _QPoint(QPoint):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def to_tuple(self) -> tuple[int, int]:
        return self.x(), self.y()


QPoint = _QPoint


class VertexType(Enum):
    START = "start"
    SPLIT = "split"
    END = "end"
    MERGE = "merge"
    REGULAR = "regular"


class Vertex(QPoint):
    type_: VertexType

    def __init__(self, index: int, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._index: int = index

    def index(self) -> int:
        return self._index

    @staticmethod
    def from_point(index: int, point: QPoint) -> "Vertex":
        return Vertex(index, point)

    def __repr__(self) -> str:
        return f"Vertex <index: {self._index}, type_: {self.type_}, pos: {self.to_tuple()}>"


class Dialog(QDialog):
    def __init__(self, title: str = "Ошибка", message: str = "Непредвиденная ошибка!"):
        super().__init__()

        self.setWindowTitle(title)

        button = QDialogButtonBox.StandardButton.Ok

        self.buttonBox = QDialogButtonBox(button)
        self.buttonBox.accepted.connect(self.accept)  # noqa

        self.layout = QVBoxLayout()

        message = QLabel(message)
        message.setStyleSheet("QLabel {font-size: 16pt; margin: auto;}")

        self.layout.addWidget(message)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)


class Polygon:
    def __init__(self, color: QColor = QColor("black")) -> None:
        self._vertexes: list[Vertex] = list()

        self._color: QColor = color

        self._closed: bool = False

    def get_color(self) -> QColor:
        return self._color

    def _set_color(self, color: QColor) -> None:
        self._color = color

    def set_random_color(self) -> None:
        self._set_color(QColor(randint(63, 220), randint(63, 220), randint(63, 220)))

    def add_vertex(self, point: QPoint) -> None:
        vertex: Vertex = Vertex.from_point(
            self.vertex_count(),
            point,
        )
        self._vertexes.append(vertex)

    def vertex_count(self) -> int:
        return len(self._vertexes)

    def peek_vertexes(self) -> list[Vertex]:
        return self._vertexes.copy()

    def peek_vertex(self, index: int) -> Vertex:
        return self._vertexes[index]

    def peek_last_vertex(self) -> Vertex:
        return self.peek_vertex(-1)

    def close(self) -> None:
        self._closed = True

    def is_closed(self) -> bool:
        return self._closed

    def intersects(self, start_point: QPoint, end_point: QPoint) -> bool:
        if len(self._vertexes) < 2:
            return False

        edges: list[LineString] = list()

        previous_vertex: QPoint = self._vertexes[0]
        for current_vertex in self._vertexes[1:]:
            edges.append(
                LineString([previous_vertex.to_tuple(), current_vertex.to_tuple()])
            )

            previous_vertex = current_vertex

        line: LineString = LineString([start_point.to_tuple(), end_point.to_tuple()])

        for edge in edges:
            if intersection := line.intersection(edge):
                point: QPoint = QPoint(int(intersection.x), int(intersection.y))

                if point in self._vertexes:
                    continue

                return True

        return False

    def triangulate(self) -> None:
        vertex_queue: list[Vertex] = sorted(
            self._vertexes, key=lambda _vertex: (_vertex.y(), -_vertex.x()), reverse=True
        )

        while len(vertex_queue) > 0:
            current_vertex: Vertex = vertex_queue.pop(0)

            current_vertex.type_ = self._type_of_vertex(current_vertex)

    def _type_of_vertex(self, current_vertex: Vertex) -> VertexType:
        current_index: int = current_vertex.index()

        next_vertex: Vertex = self._vertexes[
            (current_index + 1) % self.vertex_count()
        ]
        previous_vertex: Vertex = self._vertexes[current_index - 1]

        def is_higher(v1: Vertex, v2: Vertex) -> bool:
            if v1.y() == v2.y():
                return v1.x() < v2.x()

            return v1.y() < v2.y()

        is_higher_than_right: bool = is_higher(current_vertex, next_vertex)
        is_higher_than_left: bool = is_higher(current_vertex, previous_vertex)

        vector_to_next: list[int] = [
            next_vertex.x() - current_vertex.x(),
            next_vertex.y() - current_vertex.y(),
        ]
        vector_to_previous: list[int] = [
            previous_vertex.x() - current_vertex.x(),
            previous_vertex.y() - current_vertex.y(),
        ]

        angle: float = math.acos(
            (vector_to_next[0] * vector_to_previous[0] + vector_to_next[1] * vector_to_previous[1])
            / (
                math.sqrt(vector_to_next[0] ** 2 + vector_to_next[1] ** 2)
                * math.sqrt(vector_to_previous[0] ** 2 + vector_to_previous[1] ** 2)
            )
        )
        angle = math.degrees(angle)

        if is_higher_than_right and is_higher_than_left:
            if angle > 180:
                return VertexType.SPLIT
            else:
                return VertexType.START
        elif not (is_higher_than_right or is_higher_than_left):
            if angle > 180:
                return VertexType.MERGE
            else:
                return VertexType.END

        return VertexType.REGULAR

    @staticmethod
    def random_polygon() -> "Polygon":
        vertex_number: int = randint(4, 8)

        canvas_width, canvas_height = Canvas.get_size()

        vertexes: list[QPoint] = list()
        while len(vertexes) < vertex_number:
            vertexes.append(QPoint(randint(0, canvas_width), randint(0, canvas_height)))

        leftmost_vertex: QPoint = vertexes[0]
        rightmost_vertex: QPoint = vertexes[0]

        for vertex in vertexes[1:]:
            if vertex.x() < leftmost_vertex.x():
                leftmost_vertex = vertex

            if vertex.x() > rightmost_vertex.x():
                rightmost_vertex = vertex

        above_line_vertexes: list[QPoint] = list()
        below_line_vertexes: list[QPoint] = list()

        vertexes.remove(leftmost_vertex)
        vertexes.remove(rightmost_vertex)

        for vertex in vertexes:
            vector_product: int = int(
                (vertex.x() - leftmost_vertex.x())
                * (rightmost_vertex.y() - leftmost_vertex.y())
                - (vertex.y() - leftmost_vertex.y())
                * (rightmost_vertex.x() - leftmost_vertex.x())
            )

            if vector_product > 0:
                above_line_vertexes.append(vertex)
            else:
                below_line_vertexes.append(vertex)

        above_line_vertexes.sort(key=lambda p: p.x())
        below_line_vertexes.sort(key=lambda p: p.x(), reverse=True)

        polygon: Polygon = Polygon()
        polygon.set_random_color()

        for vertex in (
            leftmost_vertex,
            *above_line_vertexes,
            rightmost_vertex,
            *below_line_vertexes,
        ):
            polygon.add_vertex(vertex)

        polygon.close()

        return polygon


class Canvas(QLabel):
    _size: tuple[int, int] = (720, 480)
    _background_color: tuple[int, int, int] = (42, 42, 42)

    def __init__(
        self,
        raw_polygon: Polygon,
        *args,
        **kwargs,
    ):
        super(Canvas, self).__init__(*args, **kwargs)

        self.setFixedSize(*Canvas._size)

        _canvas: QPixmap = QPixmap(*Canvas._size)
        _canvas.fill(QColor(*Canvas._background_color))

        self.setPixmap(_canvas)

        self.place_grid()

        self._polygon: Polygon = raw_polygon
        self._triangles: list[Polygon] = list()

        self._dragging_vertex: QPoint | None = None

    @classmethod
    def get_size(cls) -> tuple[int, int]:
        return cls._size

    def replace_polygon(self, new_polygon: Polygon) -> None:
        self._polygon = new_polygon

        self.redraw_canvas()

        if self._polygon.is_closed():
            self.triangulate_polygon()

    def place_grid(self, grid_step: int = 30) -> None:
        canvas = self.pixmap()
        painter = Canvas.construct_painter(QColor(100, 100, 100, alpha=40), canvas, 2)

        for i in range(grid_step, Canvas._size[1], grid_step):
            painter.drawLine(QPoint(0, i), QPoint(Canvas._size[0], i))

        for i in range(grid_step, Canvas._size[0], grid_step):
            painter.drawLine(QPoint(i, 0), QPoint(i, Canvas._size[1]))

        painter.end()
        self.setPixmap(canvas)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        canvas: QPixmap = self.pixmap()
        painter: QPainter = Canvas.construct_painter(self._polygon.get_color(), canvas)

        def is_close(p: QPoint, q: QPoint, r: float) -> bool:
            d: QPoint = p - q

            return d.x() ** 2 + d.y() ** 2 <= r**2

        if event.button() == Qt.MouseButton.LeftButton:
            closest_point: QPoint | None = None
            for previous_point in self._polygon.peek_vertexes():
                if is_close(event.pos(), previous_point, 5):
                    closest_point = previous_point

                    break

            if closest_point is not None:
                self.set_dragging_vertex(closest_point)
            else:
                if self._polygon.is_closed():
                    Dialog(
                        "Полигон закрыт",
                        "Полигон закрыт: невозможно поставить ещё одну точку.",
                    ).exec()
                else:
                    self.place_point(QPoint(event.pos()), painter)
        elif event.button() == Qt.MouseButton.RightButton:
            self.close_polygon(painter)

        painter.end()
        self.setPixmap(canvas)

        if self._polygon.is_closed():
            self.triangulate_polygon()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging_vertex is None:
            return

        for vertex in self._polygon.peek_vertexes():
            if vertex is self._dragging_vertex:
                vertex.setX(event.pos().x())
                vertex.setY(event.pos().y())

        self.redraw_canvas()

        if self._polygon.is_closed():
            self.triangulate_polygon()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging_vertex is not None:
            self._dragging_vertex = None

    def redraw_canvas(self) -> None:
        self.clear_canvas()

        canvas = self.pixmap()
        painter: QPainter = Canvas.construct_painter(self._polygon.get_color(), canvas)

        previous_vertex: QPoint | None = None
        for vertex in self._polygon.peek_vertexes():
            painter.drawEllipse(vertex, 2, 2)

            if previous_vertex is not None:
                painter.drawLine(previous_vertex, vertex)

            previous_vertex = vertex

        if self._polygon.is_closed():
            painter.drawLine(previous_vertex, self._polygon.peek_vertexes()[0])

        painter.end()
        self.setPixmap(canvas)

    def place_point(self, point: QPoint, painter: QPainter) -> None:
        if self._polygon.vertex_count() > 0 and self._polygon.intersects(
            point, self._polygon.peek_vertex(-1)
        ):
            Dialog(
                "Проверка на самопересечения",
                "Точка, которую Вы хотите поставить, приведёт к самопересечению многоугольника.",
            ).exec()

            return

        painter.drawEllipse(point, 2, 2)

        if self._polygon.vertex_count() > 0:
            painter.drawLine(self._polygon.peek_last_vertex(), point)

        self._polygon.add_vertex(point)

    def close_polygon(self, painter: QPainter) -> None:
        if self._polygon.vertex_count() < 4:
            Dialog(
                message="Недостаточно точек для закрытия полигона. Их должно быть не менее 4."
            ).exec()

            return

        if self._polygon.is_closed():
            Dialog(
                "Полигон закрыт",
                "Невозможно закрыть полигон: полигон уже закрыт!",
            ).exec()

            return

        if self._polygon.intersects(
            self._polygon.peek_last_vertex(), self._polygon.peek_vertex(0)
        ):
            Dialog(
                "Проверка на самопересечения",
                "Закрытие полигона сейчас приведёт к самопересечению. "
                "Измените геометрию полигона и повторите попытку.",
            ).exec()

            return

        painter.drawLine(self._polygon.peek_last_vertex(), self._polygon.peek_vertex(0))

        self._polygon.close()

    def set_dragging_vertex(self, vertex: QPoint) -> None:
        self._dragging_vertex = vertex

    def triangulate_polygon(self) -> None:
        self._polygon.triangulate()

        # diagonals: list[tuple[QPoint, QPoint]] = list()
        #
        # for first_index, first_point in enumerate(self.polygon):
        #     for second_point in self.polygon[first_index + 2 :]:
        #         if {first_point, second_point} == {self.polygon[0], self.polygon[-1]}:
        #             continue
        #
        #         if self.check_for_intersections(first_point, second_point):
        #             continue
        #
        #         diagonals.append((first_point, second_point))

        def place_point(color: QColor, point: QPoint) -> None:
            canvas_ = self.pixmap()
            painter_ = Canvas.construct_painter(color, canvas_, 10)

            painter_.drawPoint(point)

            painter_.end()
            self.setPixmap(canvas_)

        for vertex in self._polygon.peek_vertexes():
            match vertex.type_:
                case VertexType.START:
                    place_point(QColor("yellow"), vertex)
                case VertexType.END:
                    place_point(QColor("green"), vertex)
                case VertexType.SPLIT:
                    place_point(QColor("red"), vertex)
                case VertexType.MERGE:
                    place_point(QColor("blue"), vertex)
                case VertexType.REGULAR:
                    place_point(QColor("black"), vertex)

    def clear_canvas(self) -> None:
        canvas = self.pixmap()
        canvas.fill(QColor(*Canvas._background_color))
        self.setPixmap(canvas)

        self.place_grid()

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
        self.buttonBox.accepted.connect(self.accept)  # noqa

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

        polygon: Polygon = Polygon()
        polygon.set_random_color()

        self.canvas = Canvas(polygon)

        right_widgets = QVBoxLayout()
        right_widgets.setSpacing(20)
        right_widgets.setAlignment(Qt.AlignmentFlag.AlignCenter)

        clear_button = QPushButton("Очистить холст")
        clear_button.clicked.connect(self.clear_canvas)  # noqa
        clear_button.setStyleSheet(
            "QPushButton {margin: auto; padding: 5px; font-size: 24px;}"
        )

        info_button = QPushButton("Справка")
        info_button.clicked.connect(self.info_clicked)  # noqa
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
        random_button.clicked.connect(self.place_random_polygon)  # noqa
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

    def clear_canvas(self) -> None:
        self.canvas.clear_canvas()

        polygon: Polygon = Polygon()
        polygon.set_random_color()

        self.canvas.replace_polygon(polygon)

    def place_random_polygon(self) -> None:
        random_polygon: Polygon = Polygon.random_polygon()

        self.canvas.replace_polygon(random_polygon)


if __name__ == "__main__":
    app = QApplication([])

    window = Cutting()
    window.show()

    app.exec()
