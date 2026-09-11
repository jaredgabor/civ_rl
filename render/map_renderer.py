import math
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, RegularPolygon


class HexMapRenderer:
    def __init__(self, hex_size=1.0):
        self.hex_size = float(hex_size)
        # 30 degrees => pointy-top hexes with flat left/right edges.
        self.hex_orientation = math.pi / 3
        self.terrain_colors = {
            1: "#3b82f6",  # OCEAN
            2: "#84cc16",  # PLAINS
            3: "#22c55e",  # PLAINS-WOODS
            4: "#a16207",  # HILLS
            5: "#15803d",  # HILLS-WOODS
            6: "#525252",  # MOUNTAINS
        }
        self.default_color = "#ff00ff"

    def tile_center(self, row, col):
        # odd-r horizontal layout (odd rows shifted right by half hex width)
        x = self.hex_size * math.sqrt(3) * (col + 0.5 * (row % 2))
        y = self.hex_size * 1.5 * row
        return x, y

    def tile_vertices(self, row, col):
        cx, cy = self.tile_center(row, col)
        s = self.hex_size
        half = 0.5 * s
        xoff = (math.sqrt(3) / 2.0) * s

        # Pointy-top hex (flat left/right): only three distinct x offsets.
        offsets = [
            (0.0, s),
            (xoff, half),
            (xoff, -half),
            (0.0, -s),
            (-xoff, -half),
            (-xoff, half),
        ]
        return [(cx + dx, cy + dy) for dx, dy in offsets]

    def _shared_edge_points(self, a, b, tolerance=1e-6):
        av = self.tile_vertices(*a)
        bv = self.tile_vertices(*b)
        shared = []
        for ax, ay in av:
            for bx, by in bv:
                if (ax - bx) ** 2 + (ay - by) ** 2 <= tolerance:
                    shared.append((ax, ay))
                    break
        if len(shared) >= 2:
            return shared[0], shared[1]
        return None

    def render(
        self,
        hex_map,
        ax=None,
        units=None,
        cities=None,
        show_tile_coords=False,
    ):
        '''
        Render a HexMap with terrain colors and optional overlays.

        :param hex_map: engine.map.HexMap
        :param ax: Optional matplotlib axis
        :param units: Optional dict[(row, col)] -> hp
        :param cities: Optional dict[(row, col)] -> hp
        :param show_tile_coords: If true, draw row/col labels in each tile
        :return: (fig, ax)
        '''
        if plt is None:
            raise ImportError(
                "matplotlib is required for HexMapRenderer. Install it with: pip install matplotlib"
            )

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 8))
        else:
            fig = ax.figure

        units = units or {}
        cities = cities or {}

        for row in range(hex_map.height):
            for col in range(hex_map.width):
                terrain_id = int(hex_map.terrain[row, col])
                face_color = self.terrain_colors.get(terrain_id, self.default_color)
                cx, cy = self.tile_center(row, col)

                hex_patch = RegularPolygon(
                    (cx, cy),
                    numVertices=6,
                    radius=self.hex_size,
                    orientation=self.hex_orientation,
                    facecolor=face_color,
                    edgecolor="black",
                    linewidth=0.8,
                )
                ax.add_patch(hex_patch)

                if show_tile_coords:
                    coord_offset = 0.8
                    ax.text(
                        cx,
                        cy + coord_offset * self.hex_size,
                        f"{row},{col}",
                        ha="center",
                        va="center",
                        fontsize=6,
                        color="black",
                    )

        # Future-proof unit rendering: circle + HP text
        for (row, col), hp in units.items():
            if not hex_map.in_bounds(row, col):
                continue
            cx, cy = self.tile_center(row, col)
            marker = Circle(
                (cx, cy),
                radius=self.hex_size * 0.35,
                facecolor="#111827",
                edgecolor="white",
                linewidth=1.0,
                zorder=5,
            )
            ax.add_patch(marker)
            ax.text(
                cx,
                cy,
                str(hp),
                color="white",
                fontsize=8,
                ha="center",
                va="center",
                zorder=6,
            )

        # City rendering: star + optional HP text
        city_positions = set(getattr(hex_map, "city_positions", set()))
        city_positions.update(cities.keys())
        for row, col in city_positions:
            if not hex_map.in_bounds(row, col):
                continue
            cx, cy = self.tile_center(row, col)
            city_radius = self.hex_size * 0.42
            star_up = RegularPolygon(
                (cx, cy),
                numVertices=3,
                radius=city_radius,
                orientation=math.pi / 2,
                facecolor="black", ### "#ef4444",
                edgecolor="black",
                linewidth=0.8,
                zorder=7,
            )
            star_down = RegularPolygon(
                (cx, cy),
                numVertices=3,
                radius=city_radius,
                orientation=-math.pi / 2,
                facecolor="black", ### "#ef4444",
                edgecolor="black",
                linewidth=0.8,
                zorder=7,
            )
            ax.add_patch(star_up)
            ax.add_patch(star_down)
            if (row, col) in cities:
                ax.text(
                    cx,
                    cy,
                    str(cities[(row, col)]),
                    color="white",
                    fontsize=7,
                    ha="center",
                    va="center",
                    zorder=8,
                )

        # River rendering on shared edges between neighboring tiles.
        print('doing rivers')
        for edge in getattr(hex_map, "rivers", set()):
            if len(edge) != 2:
                continue
            a, b = edge
            points = self._shared_edge_points(a, b)
            if points is None:
                continue
            p1, p2 = points
            ax.plot(
                [p1[0], p2[0]],
                [p1[1], p2[1]],
                color="#1d4ed8",
                linewidth=6.0,
                solid_capstyle="round",
                zorder=9,
            )

        ax.set_aspect("equal")
        ax.axis("off")

        xs = []
        ys = []
        for row in range(hex_map.height):
            for col in range(hex_map.width):
                x, y = self.tile_center(row, col)
                xs.append(x)
                ys.append(y)

        if xs and ys:
            margin = self.hex_size * 1.25
            ax.set_xlim(min(xs) - margin, max(xs) + margin)
            ax.set_ylim(max(ys) + margin, min(ys) - margin)

        return fig, ax
