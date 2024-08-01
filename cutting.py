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
from shapely.geometry import LineString, Point


class Vector2D:
    def __init__(self, x: float, y: float) -> None:
        self._x: float = x
        self._y: float = y

    @property
    def x(self) -> float:
        return self._x

    @x.setter
    def x(self, x: float):
        self._x = x

    @property
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, y: float):
        self._y = y

    def length(self) -> float:
        return math.sqrt(self._x**2 + self._y**2)

    def dot_product(self, other: "Vector2D") -> float:
        return self.x * other.x + self.y * other.y

    def cross_product(self, other: "Vector2D") -> float:
        return self.x * other.y - self.y * other.x

    def __repr__(self) -> str:
        return f"Vector <x: {self._x}, y: {self._y}>"


def left_turn(u: Vector2D, v: Vector2D) -> int:
    _cross_product: float = u.cross_product(v)

    if _cross_product < 0:
        return -1
    elif _cross_product == 0:
        return 0
    else:
        return 1


class VertexType(Enum):
    START = "start"
    SPLIT = "split"
    END = "end"
    MERGE = "merge"
    REGULAR = "regular"


class Vertex(QPoint):
    def __init__(self, half_edge: "HalfEdge" = None, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._half_edge: HalfEdge | None = half_edge

    @property
    def half_edge(self) -> "HalfEdge":
        return self._half_edge

    @half_edge.setter
    def half_edge(self, half_edge: "HalfEdge") -> None:
        self._half_edge = half_edge

    def to_tuple(self) -> tuple[int, int]:
        return self.x(), self.y()

    def __repr__(self) -> str:
        return f"{self.to_tuple()}"

    @staticmethod
    def from_point(point: QPoint) -> "Vertex":
        return Vertex(None, point)


class HalfEdge:
    def __init__(
        self,
        origin: Vertex = None,
        next_: "HalfEdge" = None,
        previous: "HalfEdge" = None,
        twin: "HalfEdge" = None,
        face: "Face" = None,
    ) -> None:
        self._origin: Vertex | None = origin

        self._next: HalfEdge | None = next_
        self._previous: HalfEdge | None = previous

        self._twin: HalfEdge | None = twin

        self._face: Face | None = face

    @property
    def origin(self) -> Vertex:
        return self._origin

    @origin.setter
    def origin(self, origin: Vertex) -> None:
        self._origin = origin

    @property
    def next(self) -> "HalfEdge":
        return self._next

    @next.setter
    def next(self, next_: "HalfEdge") -> None:
        self._next = next_

    @property
    def previous(self) -> "HalfEdge":
        return self._previous

    @previous.setter
    def previous(self, previous: "HalfEdge") -> None:
        self._previous = previous

    @property
    def twin(self) -> "HalfEdge":
        return self._twin

    @twin.setter
    def twin(self, twin: "HalfEdge") -> None:
        self._twin = twin

    @property
    def face(self) -> "Face":
        return self._face

    @face.setter
    def face(self, face: "Face") -> None:
        self._face = face


class Face:
    def __init__(self, boundary: HalfEdge) -> None:
        self._boundary: HalfEdge = boundary

    @property
    def boundary(self) -> HalfEdge:
        return self._boundary


class SelfIntersectionException(Exception):
    pass


class PolygonClosedException(Exception):
    pass


class NotEnoughVertexesException(Exception):
    pass


class Polygon:
    def __init__(self, color: QColor = QColor("black")) -> None:
        self._first_vertex: Vertex | None = None
        self._last_vertex: Vertex | None = None

        self._vertex_count: int = 0

        self._color: QColor = color

        self._closed: bool = False
        self._clockwise: bool = True

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, color: QColor) -> None:
        self._color = color

    def set_random_color(self) -> None:
        self._color = QColor(randint(63, 220), randint(63, 220), randint(63, 220))

    def add_vertex(self, point: QPoint) -> None:
        new_vertex: Vertex = Vertex.from_point(point)

        if self._last_vertex is not None and self.intersects(
            LineString([self._last_vertex.to_tuple(), new_vertex.to_tuple()])
        ):
            raise SelfIntersectionException()

        if self._first_vertex is None:
            self._first_vertex = new_vertex

        new_half_edge: HalfEdge = HalfEdge(new_vertex)
        new_vertex.half_edge = new_half_edge

        new_half_edge_twin: HalfEdge = HalfEdge(twin=new_half_edge)
        new_half_edge.twin = new_half_edge_twin

        if self._last_vertex is not None:
            last_half_edge: HalfEdge = self._last_vertex.half_edge
            last_half_edge_twin: HalfEdge = last_half_edge.twin

            new_half_edge.previous = last_half_edge

            new_half_edge_twin.next = last_half_edge_twin

            last_half_edge.next = new_half_edge

            last_half_edge_twin.origin = new_vertex
            last_half_edge_twin.previous = new_half_edge_twin

        self._last_vertex = new_vertex

        self._vertex_count += 1

    @property
    def vertex_count(self) -> int:
        return self._vertex_count

    @property
    def first_vertex(self) -> Vertex:
        return self._first_vertex

    @property
    def last_vertex(self) -> Vertex:
        return self._last_vertex

    def close(self) -> None:
        if self.is_closed():
            raise PolygonClosedException()

        if self.intersects(
            LineString([self._last_vertex.to_tuple(), self._first_vertex.to_tuple()])
        ):
            raise SelfIntersectionException()

        if self._vertex_count < 4:
            raise NotEnoughVertexesException()

        first_half_edge: HalfEdge = self._first_vertex.half_edge
        first_half_edge_twin: HalfEdge = first_half_edge.twin

        last_half_edge: HalfEdge = self._last_vertex.half_edge
        last_half_edge_twin: HalfEdge = last_half_edge.twin

        last_half_edge.next = first_half_edge

        first_half_edge.previous = last_half_edge

        last_half_edge_twin.origin = self._first_vertex
        last_half_edge_twin.previous = first_half_edge_twin

        first_half_edge_twin.next = last_half_edge_twin

        self._closed = True

    def is_closed(self) -> bool:
        return self._closed

    def intersects(self, line: LineString, no_vertexes: bool = True) -> bool:
        edges: list[LineString] = list()

        current_vertex: Vertex = self._first_vertex
        if current_vertex is None:
            return False

        if current_vertex.half_edge.next is None:
            return False

        next_vertex: Vertex = current_vertex.half_edge.next.origin
        if next_vertex is None:
            return False

        edges.append(LineString([current_vertex.to_tuple(), next_vertex.to_tuple()]))

        current_vertex = next_vertex

        while current_vertex is not self._first_vertex:
            if current_vertex.half_edge.next is None:
                break

            next_vertex = current_vertex.half_edge.next.origin
            if next_vertex is None:
                break

            edges.append(
                LineString([current_vertex.to_tuple(), next_vertex.to_tuple()])
            )

            current_vertex = next_vertex

        for edge in edges:
            intersection = line.intersection(edge)

            if not intersection:
                continue

            if not no_vertexes:
                return True

            point: tuple[int, int] = Point(int(intersection.x), int(intersection.y))

            if point in edge.boundary.geoms:
                continue

            return True

        return False

    def triangulate(self) -> None:
        vertex_queue: list[Vertex] = sorted(  # noqa
            self,
            key=lambda _vertex: (_vertex.y(), _vertex.x()),
        )

        first_vertex: Vertex = vertex_queue.pop(0)
        if self._type_of_vertex(first_vertex) is not VertexType.START:
            self._clockwise = False

        first_vertex.type_ = VertexType.START

        while len(vertex_queue) > 0:
            current_vertex: Vertex = vertex_queue.pop(0)

            current_vertex.type_ = self._type_of_vertex(current_vertex)

    def _type_of_vertex(self, current_vertex: Vertex) -> VertexType:
        next_vertex: Vertex = current_vertex.half_edge.next.origin
        previous_vertex: Vertex = current_vertex.half_edge.previous.origin

        def is_higher(v1: Vertex, v2: Vertex) -> bool:
            if v1.y() == v2.y():
                return v1.x() < v2.x()

            return v1.y() < v2.y()

        is_higher_than_right: bool = is_higher(current_vertex, next_vertex)
        is_higher_than_left: bool = is_higher(current_vertex, previous_vertex)

        vector_to_next: Vector2D = Vector2D(
            next_vertex.x() - current_vertex.x(),
            next_vertex.y() - current_vertex.y(),
        )
        vector_to_previous: Vector2D = Vector2D(
            previous_vertex.x() - current_vertex.x(),
            previous_vertex.y() - current_vertex.y(),
        )

        predicate: int = left_turn(vector_to_next, vector_to_previous)
        if not self._clockwise:
            predicate *= -1

        if is_higher_than_right and is_higher_than_left:
            if predicate == 1:
                return VertexType.SPLIT
            else:
                return VertexType.START
        elif not (is_higher_than_right or is_higher_than_left):
            if predicate == 1:
                return VertexType.MERGE
            else:
                return VertexType.END

        return VertexType.REGULAR

    @staticmethod
    def random_polygon() -> "Polygon":
        vertex_number: int = randint(4, 14)

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

    def __iter__(self) -> Vertex:
        current_vertex: Vertex = self._first_vertex

        while True:
            if current_vertex is None:
                break

            yield current_vertex

            if current_vertex.half_edge.next is None:
                break

            if self.is_closed() and self._first_vertex.half_edge.previous.origin is current_vertex:
                break

            current_vertex = current_vertex.half_edge.next.origin


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
        painter: QPainter = Canvas.construct_painter(self._polygon.color, canvas)

        def is_close(p: QPoint, q: QPoint, r: float) -> bool:
            d: QPoint = p - q

            return d.x() ** 2 + d.y() ** 2 <= r**2

        if event.button() == Qt.MouseButton.LeftButton:
            closest_point: QPoint | None = None
            for previous_point in self._polygon:
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

        self._dragging_vertex.setX(event.pos().x())
        self._dragging_vertex.setY(event.pos().y())

        self.redraw_canvas()

        if self._polygon.is_closed():
            self.triangulate_polygon()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging_vertex is not None:
            self._dragging_vertex = None

    def redraw_canvas(self) -> None:
        self.clear_canvas()

        canvas = self.pixmap()
        painter: QPainter = Canvas.construct_painter(self._polygon.color, canvas)

        previous_vertex: QPoint | None = None
        for vertex in self._polygon:
            painter.drawEllipse(vertex, 2, 2)

            if previous_vertex is not None:
                painter.drawLine(previous_vertex, vertex)

            previous_vertex = vertex

        if self._polygon.is_closed():
            painter.drawLine(self._polygon.last_vertex, self._polygon.first_vertex)

        painter.end()
        self.setPixmap(canvas)

    def place_point(self, point: QPoint, painter: QPainter) -> None:
        try:
            self._polygon.add_vertex(point)
        except SelfIntersectionException:
            Dialog(
                "Проверка на самопересечения",
                "Точка, которую Вы хотите поставить, приведёт к самопересечению многоугольника.",
            ).exec()
        else:
            painter.drawEllipse(point, 2, 2)

            previous_half_edge: HalfEdge = self._polygon.last_vertex.half_edge.previous
            if previous_half_edge is not None:
                painter.drawLine(self._polygon.last_vertex.half_edge.previous.origin, self._polygon.last_vertex)

    def close_polygon(self, painter: QPainter) -> None:
        try:
            self._polygon.close()
        except PolygonClosedException:
            Dialog(
                "Полигон закрыт",
                "Невозможно закрыть полигон: полигон уже закрыт!",
            ).exec()
        except SelfIntersectionException:
            Dialog(
                "Проверка на самопересечения",
                "Закрытие полигона сейчас приведёт к самопересечению. "
                "Измените геометрию полигона и повторите попытку.",
            ).exec()
        except NotEnoughVertexesException:
            Dialog(
                message="Недостаточно точек для закрытия полигона. Их должно быть не менее 4."
            ).exec()
        else:
            painter.drawLine(self._polygon.last_vertex, self._polygon.first_vertex)

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

        for vertex in self._polygon:
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
