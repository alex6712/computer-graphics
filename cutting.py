import math
from enum import Enum
from random import randint
from typing import Iterable

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QMouseEvent,
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
    QCheckBox,
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
    def x(self, x: float) -> None:
        self._x = x

    @property
    def y(self) -> float:
        return self._y

    @y.setter
    def y(self, y: float) -> None:
        self._y = y

    def length(self) -> float:
        return math.sqrt(self._x**2 + self._y**2)

    def dot_product(self, other: "Vector2D") -> float:
        return self.x * other.x + self.y * other.y

    def cross_product(self, other: "Vector2D") -> float:
        return self.x * other.y - self.y * other.x

    @staticmethod
    def from_points(start: QPoint, end: QPoint) -> "Vector2D":
        return Vector2D(
            end.x() - start.x(),
            end.y() - start.y(),
        )

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
    def __init__(
            self, index: int, half_edge: "HalfEdge" = None, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        self._index: int = index

        self._half_edge: HalfEdge | None = half_edge

        self._type: VertexType | None = None

    @property
    def index(self) -> int:
        return self._index

    @property
    def half_edge(self) -> "HalfEdge":
        return self._half_edge

    @half_edge.setter
    def half_edge(self, half_edge: "HalfEdge") -> None:
        self._half_edge = half_edge

    @property
    def type(self) -> VertexType | None:
        return self._type

    @type.setter
    def type(self, type_: VertexType | None) -> None:
        self._type = type_

    def to_tuple(self) -> tuple[int, int]:
        return self.x(), self.y()

    def __repr__(self) -> str:
        return f"{self.to_tuple()}"

    @staticmethod
    def from_point(index: int, point: QPoint) -> "Vertex":
        return Vertex(index, None, point)


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


class PolygonIsNotClosedException(Exception):
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

        self._cuts: list[tuple[Vertex, Vertex]] = list()

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, color: QColor) -> None:
        self._color = color

    def set_random_color(self) -> None:
        self._color = QColor(randint(63, 220), randint(63, 220), randint(63, 220))

    def add_vertex(self, point: QPoint) -> None:
        if self.is_closed():
            raise PolygonClosedException()

        new_vertex: Vertex = Vertex.from_point(self._vertex_count, point)

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

    def iter_vertexes(self) -> Iterable[Vertex]:
        current_vertex: Vertex = self._first_vertex

        while True:
            if current_vertex is None:
                break

            yield current_vertex

            if current_vertex.half_edge.next is None:
                break

            if (
                self.is_closed()
                and self._first_vertex.half_edge.previous.origin is current_vertex
            ):
                break

            current_vertex = current_vertex.half_edge.next.origin

    def peek_cuts(self) -> list[tuple[Vertex, Vertex]]:
        return self._cuts.copy()

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

        highest_vertex: Vertex = sorted(
            self.iter_vertexes(),
            key=lambda _vertex: (_vertex.y(), _vertex.x()),
        )[0]

        next_vertex: Vertex = highest_vertex.half_edge.next.origin
        previous_vertex: Vertex = highest_vertex.half_edge.previous.origin

        vector_to_next: Vector2D = Vector2D.from_points(highest_vertex, next_vertex)
        vector_to_previous: Vector2D = Vector2D.from_points(
            highest_vertex, previous_vertex
        )

        if left_turn(vector_to_next, vector_to_previous) == 1:
            self._clockwise = False

    def is_closed(self) -> bool:
        return self._closed

    def intersects(self, line: LineString, no_vertexes: bool = True) -> bool:
        edges: list[LineString] = list()

        previous_vertex: Vertex | None = self._first_vertex
        for current_vertex in self.iter_vertexes():
            if current_vertex is self._first_vertex:
                continue

            edges.append(
                LineString([previous_vertex.to_tuple(), current_vertex.to_tuple()])
            )

            previous_vertex = current_vertex

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
        if not self.is_closed():
            raise PolygonIsNotClosedException()

        self._cuts.clear()

        polygon: Polygon = Polygon()

        for _vertex in self.iter_vertexes():
            polygon.add_vertex(_vertex)

        polygon.close()

        current_vertex: Vertex = polygon._first_vertex
        while polygon._vertex_count > 3:
            next_vertex: Vertex = current_vertex.half_edge.next.origin
            previous_vertex: Vertex = current_vertex.half_edge.previous.origin

            current_to_next: Vector2D = Vector2D.from_points(
                current_vertex, next_vertex
            )
            current_to_previous: Vector2D = Vector2D.from_points(
                current_vertex, previous_vertex
            )

            predicate: int = left_turn(current_to_next, current_to_previous)
            if not polygon._clockwise:
                predicate *= -1

            if predicate == 1:
                current_vertex = next_vertex
                continue

            next_to_previous: Vector2D = Vector2D.from_points(
                next_vertex, previous_vertex
            )
            previous_to_current: Vector2D = Vector2D.from_points(
                previous_vertex, current_vertex
            )

            for random_vertex in polygon.iter_vertexes():
                if random_vertex in (previous_vertex, current_vertex, next_vertex):
                    continue

                random_to_current: Vector2D = Vector2D.from_points(
                    random_vertex, current_vertex
                )
                random_to_next: Vector2D = Vector2D.from_points(
                    random_vertex, next_vertex
                )
                random_to_previous: Vector2D = Vector2D.from_points(
                    random_vertex, previous_vertex
                )

                cross_products: list[float] = [
                    random_to_current.cross_product(current_to_next),
                    random_to_next.cross_product(next_to_previous),
                    random_to_previous.cross_product(previous_to_current),
                ]

                if 0 in cross_products:
                    break

                if len({cross_product > 0 for cross_product in cross_products}) == 1:
                    break
            else:
                polygon._vertex_count -= 1

                if current_vertex is polygon._first_vertex:
                    polygon._first_vertex = next_vertex

                previous_half_edge: HalfEdge = previous_vertex.half_edge
                next_half_edge: HalfEdge = next_vertex.half_edge

                previous_half_edge.next = next_half_edge

                next_half_edge.previous = previous_half_edge

                previous_half_edge_twin: HalfEdge = previous_half_edge.twin
                next_half_edge_twin: HalfEdge = next_half_edge.twin

                previous_half_edge_twin.origin = next_vertex
                previous_half_edge_twin.previous = next_half_edge_twin

                next_half_edge_twin.next = previous_half_edge_twin

                self._cuts.append((previous_vertex, next_vertex))

            current_vertex = next_vertex

    @staticmethod
    def random_polygon() -> "Polygon":
        vertex_number: int = randint(10, 20)

        canvas_width, canvas_height = Canvas.get_size()

        vertexes: list[QPoint] = list()
        while len(vertexes) < vertex_number:
            vertexes.append(QPoint(randint(0, canvas_width), randint(0, canvas_height)))

        leftmost_vertex: QPoint = vertexes[0]
        rightmost_vertex: QPoint = vertexes[0]

        for current_vertex in vertexes[1:]:
            if current_vertex.x() < leftmost_vertex.x():
                leftmost_vertex = current_vertex

            if current_vertex.x() > rightmost_vertex.x():
                rightmost_vertex = current_vertex

        above_line_vertexes: list[QPoint] = list()
        below_line_vertexes: list[QPoint] = list()

        vertexes.remove(leftmost_vertex)
        vertexes.remove(rightmost_vertex)

        for current_vertex in vertexes:
            leftmost_to_current_vector: Vector2D = Vector2D(
                current_vertex.x() - leftmost_vertex.x(),
                current_vertex.y() - leftmost_vertex.y(),
            )
            leftmost_to_rightmost_vector: Vector2D = Vector2D(
                rightmost_vertex.x() - leftmost_vertex.x(),
                rightmost_vertex.y() - leftmost_vertex.y(),
            )

            vector_product: float = leftmost_to_current_vector.cross_product(
                leftmost_to_rightmost_vector
            )

            if vector_product > 0:
                above_line_vertexes.append(current_vertex)
            else:
                below_line_vertexes.append(current_vertex)

        above_line_vertexes.sort(key=lambda p: p.x())
        below_line_vertexes.sort(key=lambda p: p.x(), reverse=True)

        polygon: Polygon = Polygon()
        polygon.set_random_color()

        for current_vertex in (
            leftmost_vertex,
            *above_line_vertexes,
            rightmost_vertex,
            *below_line_vertexes,
        ):
            polygon.add_vertex(current_vertex)

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

        self.setMouseTracking(True)

        self.setFixedSize(*Canvas._size)

        _canvas: QPixmap = QPixmap(*Canvas._size)
        _canvas.fill(QColor(*Canvas._background_color))

        self._info_canvas: QPixmap = QPixmap(*Canvas._size)
        self._info_canvas.fill(QColor(0, 0, 0, 0))

        self._polygon_canvas: QPixmap = QPixmap(*Canvas._size)
        self._polygon_canvas.fill(QColor(0, 0, 0, 0))

        self.setPixmap(_canvas)

        self.place_grid()

        self._triangulate_permanent: bool = False

        self._polygon: Polygon = raw_polygon
        self._triangles: list[Polygon] = list()

        self._dragging_vertex: QPoint | None = None

        self._mouse_pos: QPoint | None = None

    @classmethod
    def get_size(cls) -> tuple[int, int]:
        return cls._size

    @property
    def triangulate_permanent(self) -> bool:
        return self._triangulate_permanent

    @triangulate_permanent.setter
    def triangulate_permanent(self, triangulate_permanent: bool) -> None:
        self._triangulate_permanent = triangulate_permanent

    def replace_polygon(self, new_polygon: Polygon) -> None:
        self._polygon = new_polygon

        if self._polygon.is_closed():
            self._try_triangulate_polygon()

        self._update_polygon_canvas()

        self.redraw_canvas()

    def place_grid(self, grid_step: int = 30) -> None:
        canvas: QPixmap = self.pixmap()
        painter: QPainter = QPainter(canvas)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(100, 100, 100, 40), 2, Qt.PenStyle.SolidLine))
        painter.setBrush(QBrush(QColor(100, 100, 100, 40), Qt.BrushStyle.SolidPattern))

        for i in range(grid_step, Canvas._size[1], grid_step):
            painter.drawLine(QPoint(0, i), QPoint(Canvas._size[0], i))

        for i in range(grid_step, Canvas._size[0], grid_step):
            painter.drawLine(QPoint(i, 0), QPoint(i, Canvas._size[1]))

        painter.end()
        self.setPixmap(canvas)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        def is_close(p: QPoint, q: QPoint, r: float) -> bool:
            d: QPoint = p - q

            return d.x() ** 2 + d.y() ** 2 <= r**2

        if event.button() == Qt.MouseButton.LeftButton:
            closest_vertex: QPoint | None = None
            for vertex in self._polygon.iter_vertexes():
                if is_close(event.pos(), vertex, 5):
                    closest_vertex = vertex

                    break

            if closest_vertex is not None:
                self._dragging_vertex = closest_vertex

                self._update_info_canvas()
            else:
                self._try_add_vertex(QPoint(event.pos()))

                self._update_polygon_canvas()
        elif event.button() == Qt.MouseButton.RightButton:
            self._try_close_polygon()

            if self._polygon.is_closed():
                self._try_triangulate_polygon()

            self._update_polygon_canvas()

        self.redraw_canvas()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._mouse_pos = event.pos()

        if self._dragging_vertex is not None:
            self._dragging_vertex.setX(event.pos().x())
            self._dragging_vertex.setY(event.pos().y())

            self._update_polygon_canvas()

        self._update_info_canvas()

        if self.triangulate_permanent and self._polygon.is_closed():
            self._try_triangulate_polygon()

        self.redraw_canvas()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._dragging_vertex is not None:
            self._dragging_vertex = None

            self._update_info_canvas()

            if not self.triangulate_permanent and self._polygon.is_closed():
                self._try_triangulate_polygon()

            self._update_polygon_canvas()

        self.redraw_canvas()

    def _try_add_vertex(self, point: QPoint) -> None:
        try:
            self._polygon.add_vertex(point)
        except PolygonClosedException:
            Dialog(
                "Полигон закрыт",
                "Полигон закрыт: невозможно поставить ещё одну точку.",
            ).exec()
        except SelfIntersectionException:
            Dialog(
                "Проверка на самопересечения",
                "Точка, которую Вы хотите поставить, приведёт к самопересечению многоугольника.",
            ).exec()

    def _try_close_polygon(self) -> None:
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
                "Закрытие полигона сейчас приведёт к самопересечению.\n"
                "Измените геометрию полигона и повторите попытку.",
            ).exec()
        except NotEnoughVertexesException:
            Dialog(
                message="Недостаточно точек для закрытия полигона. Их должно быть не менее 4."
            ).exec()

    def _try_triangulate_polygon(self) -> None:
        try:
            self._polygon.triangulate()
        except PolygonIsNotClosedException:
            Dialog(
                "Полигон не закрыт",
                "Полигон не закрыт: невозможно запустить триангуляцию.\nЗакройте полигон и попробуйте снова.",
            ).exec()

    def redraw_canvas(self) -> None:
        self.clear_canvas()

        canvas = self.pixmap()
        painter: QPainter = QPainter(canvas)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.drawPixmap(0, 0, self._polygon_canvas)
        painter.drawPixmap(0, 0, self._info_canvas)

        painter.end()
        self.setPixmap(canvas)

    def _update_info_canvas(self) -> None:
        self._info_canvas.fill(QColor(0, 0, 0, 0))

        info_canvas_painter: QPainter = QPainter(self._info_canvas)

        info_canvas_painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._mouse_pos is not None:
            info_canvas_painter.setPen(
                QPen(QColor(255, 255, 255, 127), 4, Qt.PenStyle.SolidLine)
            )
            info_canvas_painter.setBrush(
                QBrush(QColor(255, 255, 255, 127), Qt.BrushStyle.SolidPattern)
            )

            font: QFont = QFont()
            font.setPointSize(12)
            info_canvas_painter.setFont(font)

            info_canvas_painter.drawText(
                self._mouse_pos + QPoint(20, 20),
                f"({self._mouse_pos.x()}; {self._mouse_pos.y()})",
            )

        if self._dragging_vertex is not None:
            info_canvas_painter.setPen(
                QPen(QColor(255, 255, 255, 127), 2, Qt.PenStyle.DashDotDotLine)
            )
            info_canvas_painter.setBrush(
                QBrush(QColor(255, 255, 255, 127), Qt.BrushStyle.SolidPattern)
            )

            info_canvas_painter.drawLine(
                QPoint(self._dragging_vertex.x(), 0),
                QPoint(self._dragging_vertex.x(), Canvas._size[1]),
            )

            info_canvas_painter.drawLine(
                QPoint(0, self._dragging_vertex.y()),
                QPoint(Canvas._size[0], self._dragging_vertex.y()),
            )

        info_canvas_painter.end()

    def _update_polygon_canvas(self) -> None:
        self._polygon_canvas.fill(QColor(0, 0, 0, 0))

        polygon_canvas_painter: QPainter = QPainter(self._polygon_canvas)

        polygon_canvas_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        polygon_canvas_painter.setPen(
            QPen(QColor(self._polygon.color), 4, Qt.PenStyle.SolidLine)
        )
        polygon_canvas_painter.setBrush(
            QBrush(QColor(self._polygon.color), Qt.BrushStyle.SolidPattern)
        )

        previous_vertex: Vertex | None = None
        for vertex in self._polygon.iter_vertexes():
            polygon_canvas_painter.drawEllipse(vertex, 2, 2)

            if previous_vertex is not None:
                polygon_canvas_painter.drawLine(previous_vertex, vertex)

            previous_vertex = vertex

        if self._polygon.is_closed():
            polygon_canvas_painter.drawLine(
                self._polygon.last_vertex, self._polygon.first_vertex
            )

        if self._dragging_vertex is None or self.triangulate_permanent:
            polygon_canvas_painter.setPen(QPen(QColor("red"), 4, Qt.PenStyle.SolidLine))
            polygon_canvas_painter.setBrush(
                QBrush(QColor("red"), Qt.BrushStyle.SolidPattern)
            )

            for cut in self._polygon.peek_cuts():
                polygon_canvas_painter.drawLine(cut[0], cut[1])

        polygon_canvas_painter.end()

    def clear_canvas(self) -> None:
        canvas = self.pixmap()
        canvas.fill(QColor(*Canvas._background_color))
        self.setPixmap(canvas)

        self.place_grid()


class Dialog(QDialog):
    def __init__(
            self,
            title: str = "Ошибка",
            message: str = "Непредвиденная ошибка!",
            with_cancel: bool = False,
    ):
        super().__init__()

        self.setWindowTitle(title)

        if with_cancel:
            button = (
                    QDialogButtonBox.StandardButton.Ok
                    | QDialogButtonBox.StandardButton.Cancel
            )
        else:
            button = QDialogButtonBox.StandardButton.Ok

        self.button_box = QDialogButtonBox(button)
        self.button_box.accepted.connect(self.accept)  # noqa

        if with_cancel:
            self.button_box.rejected.connect(self.reject)  # noqa

        self.layout = QVBoxLayout()

        message = QLabel(message)
        message.setStyleSheet("QLabel {font-size: 18px; margin: auto;}")

        self.layout.addWidget(message)
        self.layout.addWidget(self.button_box)
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
            "QPushButton {margin: auto; padding: 10px; font-size: 18px;}"
        )

        info_button = QPushButton("Справка")
        info_button.clicked.connect(self.info_clicked)  # noqa
        info_button.setStyleSheet(
            "QPushButton {margin: auto; padding: 10px; font-size: 18px;}"
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
            "QPushButton {margin: auto; padding: 10px; font-size: 18px;}"
        )

        self.triangulate_mode_check_box = QCheckBox("Триангулировать постоянно")
        self.triangulate_mode_check_box.clicked.connect(  # noqa
            self.triangulate_mode_changed
        )
        self.triangulate_mode_check_box.setStyleSheet(
            "QCheckBox {margin: auto; padding: 10px; font-size: 18px;}"
        )

        bottom_widgets.addWidget(random_button)
        bottom_widgets.addWidget(self.triangulate_mode_check_box)

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

    def triangulate_mode_changed(self) -> None:
        want_to_enable: bool = self.triangulate_mode_check_box.isChecked()

        if want_to_enable:
            want_to_enable &= Dialog(
                "Предупреждение",
                "При включении данной функции может пострадать производительность.\n"
                "Вы действительно хотите её включить?",
                with_cancel=True,
            ).exec()

        if not want_to_enable:
            self.triangulate_mode_check_box.setChecked(False)

        self.canvas.triangulate_permanent = want_to_enable


if __name__ == "__main__":
    app = QApplication([])

    window = Cutting()
    window.show()

    app.exec()
