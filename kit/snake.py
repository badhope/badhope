# -*- coding: utf-8 -*-
"""贡献蛇动画（Platane/snk 的完整 Python 移植）。

移植范围（与 TS 源逐文件对应）：
- 数据抓取：tokenless HTML 抓取 `github.com/users/<u>/contributions`，
  正则提取 `data-date`/`data-level`（`fetchContributionHtml.ts`）
- 网格：`cellsToGrid.ts`，data 为 bytearray，索引 x*height+y
- 求解器：`packages/solver/*`（getBestRoute → clearResidualColoredLayer /
  clearCleanColoredLayer → getBestTunnel / getPathTo / getPathToPose / outside）
- SVG 动画：`packages/svg-creator/*`——CSS 变量 + `prefers-color-scheme: dark`
  媒体查询、逐格 fill 关键帧、逐节 transform 关键帧、进食进度条 scaleX 关键帧

确定性：算法是纯函数；抓取用 kit/net（ETag 缓存）。
"""

import re

AROUND4 = ((1, 0), (0, -1), (-1, 0), (0, 1))


# --------------------------------------------------------------------------
# grid（@snk/types/grid.ts）
# --------------------------------------------------------------------------
class Grid:
    __slots__ = ("width", "height", "data")

    def __init__(self, width, height, data=None):
        self.width = width
        self.height = height
        self.data = bytearray(width * height) if data is None else data

    def copy(self):
        return Grid(self.width, self.height, bytearray(self.data))

    def get(self, x, y):
        return self.data[x * self.height + y]

    def set(self, x, y, color):
        self.data[x * self.height + y] = color

    def set_empty(self, x, y):
        self.data[x * self.height + y] = 0

    def is_inside(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def is_inside_large(self, m, x, y):
        return -m <= x < self.width + m and -m <= y < self.height + m


def get_color_safe(grid, x, y):
    return grid.get(x, y) if grid.is_inside(x, y) else 0


def set_empty_safe(grid, x, y):
    if grid.is_inside(x, y):
        grid.set_empty(x, y)


# --------------------------------------------------------------------------
# snake（@snk/types/snake.ts）—— bytearray，头在 [0],[1]，偏移 +2
# --------------------------------------------------------------------------
def snake_head_x(snake):
    return snake[0] - 2


def snake_head_y(snake):
    return snake[1] - 2


def snake_length(snake):
    return len(snake) // 2


def next_snake(snake, dx, dy):
    copy = bytearray(len(snake))
    for i in range(2, len(snake)):
        copy[i] = snake[i - 2]
    copy[0] = snake[0] + dx
    copy[1] = snake[1] + dy
    return copy


def snake_will_self_collide(snake, dx, dy):
    nx, ny = snake[0] + dx, snake[1] + dy
    for i in range(2, len(snake) - 2, 2):
        if snake[i] == nx and snake[i + 1] == ny:
            return True
    return False


def snake_to_cells(snake):
    return [(snake[i * 2] - 2, snake[i * 2 + 1] - 2)
            for i in range(len(snake) // 2)]


def create_snake_from_cells(points):
    snake = bytearray(len(points) * 2)
    for i in range(len(points) - 1, -1, -1):
        snake[i * 2] = points[i][0] + 2
        snake[i * 2 + 1] = points[i][1] + 2
    return snake


def _unwrap(m):
    """M 链 → [head..tail] snake 列表（BFS 回溯）。"""
    out = []
    while m is not None:
        out.append(m[0])
        m = m[1]
    return out


def _unwrap_points(m):
    out = []
    while m is not None:
        out.append((m[0][0] - 2, m[0][1] - 2))
        m = m[1]
    return out


# --------------------------------------------------------------------------
# outside（packages/solver/outside.ts）
# --------------------------------------------------------------------------
def create_outside(grid, color=0):
    outside = Grid(grid.width, grid.height)
    for i in range(len(outside.data)):
        outside.data[i] = 1
    fill_outside(outside, grid, color)
    return outside


def fill_outside(outside, grid, color=0):
    changed = True
    while changed:
        changed = False
        for x in range(outside.width - 1, -1, -1):
            for y in range(outside.height - 1, -1, -1):
                if (grid.get(x, y) <= color and outside.get(x, y) != 0
                        and any(_is_outside(outside, x + dx, y + dy)
                                for dx, dy in AROUND4)):
                    outside.set(x, y, 0)
                    changed = True
    return outside


def _is_outside(outside, x, y):
    if not outside.is_inside(x, y):
        return True
    return outside.get(x, y) == 0


# --------------------------------------------------------------------------
# 通用优先级插入（utils/sortPush.ts）—— 稳定二分插入
# --------------------------------------------------------------------------
def sort_push(arr, item, key):
    lo, hi = 0, len(arr)
    if not arr or key(item) <= key(arr[0]):
        arr.insert(0, item)
        return
    while hi - lo > 1:
        mid = -(-((lo + hi) // 2))
        if key(item) == key(arr[mid]):
            lo = hi = mid
        elif key(item) > key(arr[mid]):
            lo = mid
        else:
            hi = mid
    arr.insert(-(-((lo + hi) // 2)), item)


# --------------------------------------------------------------------------
# getBestTunnel.ts
# --------------------------------------------------------------------------
def _get_snake_escape_path(grid, outside, snake0, color):
    """到达 outside 的路径，权重惩罚吃当前层颜色。"""
    open_list = [(snake0, 0)]
    close_list = [snake0]
    parents = {bytes(snake0): None}

    while open_list:
        open_list.sort(key=lambda m: m[1])
        snake, w = open_list.pop(0)
        x, y = snake_head_x(snake), snake_head_y(snake)
        if _is_outside(outside, x, y):
            chain, cur = [], bytes(snake)
            while cur is not None:
                chain.append(cur)
                cur = parents.get(cur)
            return list(reversed(chain))

        for dx, dy in AROUND4:
            c = get_color_safe(grid, x + dx, y + dy)
            if c <= color and not snake_will_self_collide(snake, dx, dy):
                nsnake = next_snake(snake, dx, dy)
                key = bytes(nsnake)
                if key not in parents:
                    parents[key] = bytes(snake)
                    sort_push(open_list, (nsnake, w + 1 + (1000 if c == color else 0)),
                              lambda m: m[1])
                    close_list.append(nsnake)
    return None


def get_best_tunnel(grid, outside, x, y, color, snake_n):
    cell = (x, y)
    snake0 = create_snake_from_cells([cell] * snake_n)

    one = _get_snake_escape_path(grid, outside, snake0, color)
    if not one:
        return None

    snake_i_cells = [snake_to_cells(s)[0] for s in one[:snake_n]]
    while len(snake_i_cells) < snake_n:
        snake_i_cells.append(snake_i_cells[-1])
    snake_i = create_snake_from_cells(snake_i_cells)

    grid_i = grid.copy()
    for px, py in [snake_to_cells(s)[0] for s in one]:
        set_empty_safe(grid_i, px, py)

    two = _get_snake_escape_path(grid_i, outside, snake_i, color)
    if not two:
        return None

    points = [snake_to_cells(s)[0] for s in one]
    points.pop(0)
    points.reverse()
    points.extend(snake_to_cells(s)[0] for s in two)

    _trim_tunnel_start(grid, points)
    _trim_tunnel_end(grid, points)
    return points


def _trim_tunnel_start(grid, tunnel):
    while tunnel:
        x, y = tunnel[0]
        if not grid.is_inside(x, y) or grid.get(x, y) == 0:
            tunnel.pop(0)
        else:
            break


def _trim_tunnel_end(grid, tunnel):
    while tunnel:
        i = len(tunnel) - 1
        x, y = tunnel[i]
        if not grid.is_inside(x, y) or grid.get(x, y) == 0 or \
                any(p == (x, y) for p in tunnel[:i]):
            tunnel.pop()
        else:
            break


# --------------------------------------------------------------------------
# clearCleanColoredLayer.ts
# --------------------------------------------------------------------------
def get_tunnellable_points_clean(grid, outside, snake_n, color):
    points = []
    for x in range(grid.width - 1, -1, -1):
        for y in range(grid.height - 1, -1, -1):
            c = grid.get(x, y)
            if c != 0 and c <= color and (x, y) not in [(p[0], p[1]) for p in points]:
                tunnel = get_best_tunnel(grid, outside, x, y, color, snake_n)
                if tunnel:
                    for p in tunnel:
                        if grid.is_inside(p[0], p[1]) and grid.get(p[0], p[1]) != 0:
                            points.append(p)
    return points


def clear_clean_colored_layer(grid, outside, snake0, color):
    snake_n = snake_length(snake0)
    points = get_tunnellable_points_clean(grid, outside, snake_n, color)
    chain = [snake0]

    while points:
        path = _get_path_to_next_point(grid, chain[0], color, points)
        if path is None:
            break
        path.pop()
        for snake in path:
            hx, hy = snake_head_x(snake), snake_head_y(snake)
            set_empty_safe(grid, hx, hy)
        chain[:0] = path

    fill_outside(outside, grid)
    chain.pop()
    return chain


def _get_path_to_next_point(grid, snake0, color, points):
    point_set = {(p[0], p[1]) for p in points}
    start = bytes(snake0)
    parents = {start: None}
    open_list = [snake0]

    while open_list:
        snake = open_list.pop(0)
        key = bytes(snake)
        x, y = snake_head_x(snake), snake_head_y(snake)
        if (x, y) in point_set:
            points[:] = [p for p in points if (p[0], p[1]) != (x, y)]
            chain = []
            cur = key
            while cur is not None:
                chain.append(cur)
                cur = parents.get(cur)
            return list(reversed([bytearray(c) for c in chain]))
        for dx, dy in AROUND4:
            nx, ny = x + dx, y + dy
            if (grid.is_inside_large(2, nx, ny)
                    and not snake_will_self_collide(snake, dx, dy)
                    and get_color_safe(grid, nx, ny) <= color):
                nsnake = next_snake(snake, dx, dy)
                nkey = bytes(nsnake)
                if nkey not in parents:
                    parents[nkey] = key
                    open_list.append(nsnake)
    return None


# --------------------------------------------------------------------------
# clearResidualColoredLayer.ts
# --------------------------------------------------------------------------
def _get_priority(grid, color, tunnel):
    n_color = n_less = 0
    seen = set()
    for i, (x, y) in enumerate(tunnel):
        if (x, y) in seen:
            continue
        seen.add((x, y))
        c = get_color_safe(grid, x, y)
        if c != 0:
            if c == color:
                n_color += 1
            else:
                n_less += color - c
    if n_color == 0:
        return 99999
    return n_less / n_color


def _get_tunnellable_points_residual(grid, outside, snake_n, color):
    points = []
    for x in range(grid.width - 1, -1, -1):
        for y in range(grid.height - 1, -1, -1):
            c = grid.get(x, y)
            if c != 0 and c < color:
                tunnel = get_best_tunnel(grid, outside, x, y, color, snake_n)
                if tunnel:
                    points.append({"x": x, "y": y, "priority": _get_priority(grid, color, tunnel),
                                   "tunnel": tunnel})
    return points


def _get_next_tunnel(tunnels, snake):
    min_distance = float("inf")
    closest = None
    x, y = snake_head_x(snake), snake_head_y(snake)
    priority = tunnels[0]["priority"]
    for t in tunnels:
        if t["priority"] != priority:
            break
        head = t["tunnel"][0]
        d = (head[0] - x) ** 2 + (head[1] - y) ** 2
        if d < min_distance:
            min_distance = d
            closest = t["tunnel"]
    return closest


def clear_residual_colored_layer(grid, outside, snake0, color):
    snake_n = snake_length(snake0)
    tunnels = _get_tunnellable_points_residual(grid, outside, snake_n, color)
    tunnels.sort(key=lambda t: -t["priority"])
    chain = [snake0]

    def _get_path_to(grid_, snake_, tx, ty):
        """A* 到目标格（只走空格/网格外），返回 snake 链（reversed）。"""
        start = bytes(snake_)
        parents = {start: None}
        open_list = [(start, 0)]
        while open_list:
            open_list.sort(key=lambda m: m[1])
            snake, w = open_list.pop(0)
            cx, cy = snake_head_x(snake), snake_head_y(snake)
            if cx == tx and cy == ty:
                chain, cur = [], bytes(snake)
                while cur is not None:
                    chain.append(cur)
                    cur = parents.get(cur)
                return list(reversed([bytearray(c) for c in chain]))
            for dx, dy in AROUND4:
                nx, ny = cx + dx, cy + dy
                if (grid_.is_inside_large(2, nx, ny)
                        and not snake_will_self_collide(snake, dx, dy)
                        and (not grid_.is_inside(nx, ny) or grid_.get(nx, ny) == 0)):
                    nsnake = next_snake(snake, dx, dy)
                    nkey = bytes(nsnake)
                    if nkey not in parents:
                        parents[nkey] = bytes(snake)
                        sort_push(open_list, (nsnake, w + 1), lambda m: m[1])
        return None

    while tunnels:
        snake_head = chain[0]
        t = _get_next_tunnel(tunnels, snake_head)
        path = _get_path_to(grid, snake_head, t[0][0], t[0][1])
        if path is None:
            break
        chain[:0] = path

        snake = chain[0]
        for i in range(1, len(t)):
            dx = t[i][0] - snake_head_x(snake)
            dy = t[i][1] - snake_head_y(snake)
            snake = next_snake(snake, dx, dy)
            chain.insert(0, snake)

        for x, y in t:
            set_empty_safe(grid, x, y)
        fill_outside(outside, grid)

        for i in range(len(tunnels) - 1, -1, -1):
            pt = tunnels[i]
            if grid.get(pt["x"], pt["y"]) == 0:
                tunnels.pop(i)
                continue
            tunnel = get_best_tunnel(grid, outside, pt["x"], pt["y"], color, snake_n)
            if not tunnel:
                tunnels.pop(i)
            else:
                pt["tunnel"] = tunnel
                pt["priority"] = _get_priority(grid, color, tunnel)
        tunnels.sort(key=lambda t: -t["priority"])

    chain.pop()
    return chain


# --------------------------------------------------------------------------
# getBestRoute.ts
# --------------------------------------------------------------------------
def get_best_route(grid0, snake0):
    grid = grid0.copy()
    outside = create_outside(grid)
    chain = [snake0]

    colors = sorted({c for c in grid.data if c > 0})
    for color in colors:
        if color > 1:
            chain[:0] = clear_residual_colored_layer(grid, outside, chain[0], color)
        chain[:0] = clear_clean_colored_layer(grid, outside, chain[0], color)

    chain.reverse()
    return chain


def get_path_to_pose(snake0, target, grid=None):
    """getPathToPose.ts：走到 target 姿态并穿过 target 格，形成闭环。"""
    if bytes(snake0) == bytes(target):
        return []
    target_cells = list(reversed(snake_to_cells(target)))
    snake_n = snake_length(snake0)
    hx0, hy0 = snake_head_x(snake0), snake_head_y(snake0)
    hx1, hy1 = snake_head_x(target), snake_head_y(target)
    box = (min(hx0, hx1) - snake_n - 1, min(hy0, hy1) - snake_n - 1,
           max(hx0, hx1) + snake_n + 1, max(hy0, hy1) + snake_n + 1)
    t0 = target_cells[0]
    forbidden = set(target_cells[1:4])

    start = bytes(snake0)
    parents = {start: None}
    open_list = [snake0]
    while open_list:
        snake = open_list.pop(0)
        key = bytes(snake)
        x, y = snake_head_x(snake), snake_head_y(snake)
        if (x, y) == t0:
            chain, cur = [], key
            while cur is not None:
                chain.append(cur)
                cur = parents.get(cur)
            path = list(reversed([bytearray(c) for c in chain]))
            # getTunnelPath(path[0], targetCells)
            snake = path[0]
            for i in range(1, len(target_cells)):
                dx = target_cells[i][0] - snake_head_x(snake)
                dy = target_cells[i][1] - snake_head_y(snake)
                snake = next_snake(snake, dx, dy)
                path.insert(0, snake)
            path.pop(0)
            path.reverse()
            return path
        for dx, dy in AROUND4:
            nx, ny = x + dx, y + dy
            if (not snake_will_self_collide(snake, dx, dy)
                    and (grid is None or (grid.is_inside_large(2, nx, ny)
                                          and get_color_safe(grid, nx, ny) == 0))
                    and (grid is not None or (box[0] <= nx <= box[2] and box[1] <= ny <= box[3]))
                    and (nx, ny) not in forbidden):
                nsnake = next_snake(snake, dx, dy)
                nkey = bytes(nsnake)
                if nkey not in parents:
                    parents[nkey] = key
                    sort_push(open_list, nsnake, lambda s: 0)
    return []


# --------------------------------------------------------------------------
# 抓取（fetchContributionHtml.ts）+ cellsToGrid.ts
# --------------------------------------------------------------------------
_FETCH_RE = re.compile(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d)"')


def fetch_contribution_cells(handle, base_url="https://github.com"):
    """tokenless 抓取贡献格。返回 [{x,y,level}]；失败抛 OSError。"""
    import datetime
    from .net import default_client
    url = "%s/users/%s/contributions" % (base_url.rstrip("/"), handle)
    body, _ = default_client().get(url, headers={"User-Agent": "profile-kit/2.0"})
    html = body.decode("utf-8", "replace")
    matches = _FETCH_RE.findall(html)
    if not matches:
        raise OSError("no contribution cells found for %s" % handle)
    dates = sorted(date for date, _ in matches)
    origin = datetime.date.fromisoformat(dates[0])
    cells = []
    for date, level in matches:
        d = datetime.date.fromisoformat(date)
        x = (d - origin).days // 7
        y = d.weekday() + 1 if d.weekday() != 6 else 0  # GitHub: 周日在第 0 行
        cells.append({"x": x, "y": y, "level": int(level)})
    return cells


def cells_to_grid(cells):
    width = max((c["x"] for c in cells), default=-1) + 1
    height = max((c["y"] for c in cells), default=-1) + 1
    grid = Grid(width, height)
    for c in cells:
        if c["level"] > 0:
            grid.set(c["x"], c["y"], c["level"])
    return grid


def generate(handle, palette="github-dark", step_duration_ms=100, theme=None):
    """完整管线：抓取 → 求解 → SVG。返回 (svg, grid) 或 (None, None)。"""
    cells = fetch_contribution_cells(handle)
    grid = cells_to_grid(cells)
    snake0 = create_snake_from_cells([(0, -1)] * 4)
    chain = get_best_route(grid, snake0)
    chain.extend(get_path_to_pose(chain[0], snake0, grid))
    svg = render_snake_svg(grid, chain, palette=palette, step_duration_ms=step_duration_ms,
                           theme=theme)
    return svg, grid


# --------------------------------------------------------------------------
# SVG 动画（packages/svg-creator/*）
# --------------------------------------------------------------------------
PALETTES = {
    "github": {"colorEmpty": "#ebedf0", "colorDots": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
               "colorSnake": "purple", "colorDotBorder": "#1b1f230a", "dark": True},
    "github-dark": {"colorEmpty": "#161b22", "colorDots": ["#161b22", "#01311f", "#034525", "#0f6d31", "#00c647"],
                    "colorSnake": "purple", "colorDotBorder": "#1b1f230a", "dark": False},
    "aurora": {"colorEmpty": "#131D3D", "colorDots": ["#131D3D", "#24356B", "#4FE3C1", "#6C8CFF", "#D9B876"],
               "colorSnake": "#F2DC9E", "colorDotBorder": "#1b1f230a", "dark": False},
}


def _merge_keyframes(keyframes):
    merged = {}
    for t, style in keyframes:
        merged.setdefault(style, []).append(t)
    return sorted(merged.items(), key=lambda kv: kv[1][0])


def _create_animation(name, keyframes):
    body = "".join(
        ",".join("%.2f%%" % round(t * 100, 2) for t in ts) + "{%s}" % style
        for style, ts in _merge_keyframes(keyframes))
    return "@keyframes %s{%s}" % (name, body)


def render_snake_svg(grid, chain, palette="github", step_duration_ms=100, size_cell=16,
                     size_dot=12, size_dot_border_radius=2, theme=None):
    opts = dict(PALETTES.get(palette, PALETTES["github"]))
    # aurora 调色板跟随主题：snake 卡与其他卡共享同一套配色
    if palette == "aurora" and theme:
        opts["colorEmpty"] = theme.get("panel2", opts["colorEmpty"])
        opts["colorDots"] = [theme.get("panel2", opts["colorDots"][0]),
                             theme.get("deep_blue", opts["colorDots"][1]),
                             theme.get("teal", opts["colorDots"][2]),
                             theme.get("indigo", opts["colorDots"][3]),
                             theme.get("gold", opts["colorDots"][4])]
        opts["colorSnake"] = theme.get("gold_bright", opts["colorSnake"])
    dark = opts.pop("dark", False)
    duration = step_duration_ms * len(chain)

    living = [{"x": x, "y": y, "t": None, "color": grid.get(x, y)}
              for x in range(grid.width) for y in range(grid.height)]
    work = grid.copy()
    for i, snake in enumerate(chain):
        x, y = snake_head_x(snake), snake_head_y(snake)
        if work.is_inside(x, y) and work.get(x, y) != 0:
            work.set_empty(x, y)
            for cell in living:
                if cell["x"] == x and cell["y"] == y:
                    cell["t"] = i / len(chain)
                    break

    styles = [":root{--cb:%s;--cs:%s;--ce:%s;%s}" % (
        opts["colorDotBorder"], opts["colorSnake"], opts["colorEmpty"],
        "".join("--c%d:%s;" % (i, c) for i, c in enumerate(opts["colorDots"])))]
    if dark:
        styles.append("@media (prefers-color-scheme: dark){:root{--cb:%s;--cs:%s;--ce:%s;%s}}" % (
            opts["colorDotBorder"], opts["colorSnake"], "#161b22",
            "".join("--c%d:%s;" % (i, c) for i, c in enumerate(
                ["#161b22", "#01311f", "#034525", "#0f6d31", "#00c647"]))))

    # grid dots
    elements = []
    dot_id = 0
    styles.append(".c{shape-rendering:geometricPrecision;fill:var(--ce);stroke-width:1px;"
                  "stroke:var(--cb);animation:none %dms linear infinite;}" % duration)
    for cell in living:
        cls, fill = "c", None
        if cell["t"] is not None:
            fid = "c%x" % dot_id
            dot_id += 1
            styles.append(_create_animation(fid, [
                (cell["t"] - 0.0001, "fill:var(--c%d)" % cell["color"]),
                (cell["t"] + 0.0001, "fill:var(--ce)"),
                (1, "fill:var(--ce)"),
            ]))
            styles.append(".c.%s{fill:var(--c%d);animation-name:%s}" % (fid, cell["color"], fid))
            cls = "c " + fid
        m = (size_cell - size_dot) / 2
        elements.append('<rect class="%s" x="%d" y="%d" rx="%d" ry="%d"/>'
                        % (cls, cell["x"] * size_cell + m, cell["y"] * size_cell + m,
                           size_dot_border_radius, size_dot_border_radius))

    # snake segments
    snake_n = snake_length(chain[0]) if chain else 0
    parts = [[] for _ in range(snake_n)]
    for snake in chain:
        cells = snake_to_cells(snake)
        for i in range(len(cells) - 1, -1, -1):
            parts[i].append(cells[i])
    for i, positions in enumerate(parts):
        d_min = size_dot * 0.8
        d_max = size_cell * 0.9
        i_max = min(4, len(chain))
        u = (1 - min(i, i_max) / i_max) ** 2
        s = (1 - u) * d_min + u * d_max
        m = (size_cell - s) / 2
        r = min(4.5, 4 * s / size_dot) if size_dot else 4.5
        elements.append('<rect class="s s%d" x="%.1f" y="%.1f" width="%.1f" height="%.1f" '
                        'rx="%.1f" ry="%.1f"/>' % (i, m, m, s, s, r, r))
        styles.append(".s{shape-rendering:geometricPrecision;fill:var(--cs);"
                      "animation:none linear %dms infinite}" % duration)
        positions_filtered = [
            (px, py) for i2, (px, py) in enumerate(positions)
            if i2 - 1 < 0 or i2 + 1 >= len(positions)
            or not (abs((positions[i2 - 1][0] + positions[i2 + 1][0]) / 2 - px) < 0.01
                    and abs((positions[i2 - 1][1] + positions[i2 + 1][1]) / 2 - py) < 0.01)
        ]
        styles.append(_create_animation("s%d" % i, [
            (i2 / len(positions), "transform:translate(%dpx,%dpx)" % (px * size_cell, py * size_cell))
            for i2, (px, py) in enumerate(positions_filtered)
        ]))

    # 进食进度条（stack.ts）
    stack = sorted([c for c in living if c["t"] is not None], key=lambda c: c["t"])
    styles.append(".u{transform-origin:0 0;transform:scale(0,1);"
                  "animation:none linear %dms infinite}" % duration)
    blocks = []
    for cell in stack:
        if blocks and blocks[-1][0] == cell["color"]:
            blocks[-1][1].append(cell["t"])
        else:
            blocks.append([cell["color"], [cell["t"]]])
    stack_width = grid.width * size_cell
    stack_y = (grid.height + 2) * size_cell
    m = stack_width / max(1, len(stack))
    nx = 0
    for i, (color, ts) in enumerate(blocks):
        uid = "u%x" % i
        x = nx * m
        nx += len(ts)
        elements.append('<rect class="u %s" height="%d" width="%.1f" x="%.1f" y="%d"/>'
                        % (uid, size_dot, len(ts) * m + 0.6, x, stack_y))
        kfs = []
        for j, t in enumerate(ts):
            kfs.append((t - 0.0001, "transform:scale(%.3f,1)" % (j / len(ts))))
            kfs.append((t + 0.0001, "transform:scale(%.3f,1)" % ((j + 1) / len(ts))))
        kfs.append((1, "transform:scale(1,1)"))
        styles.append(_create_animation(uid, kfs))
        styles.append(".u.%s{fill:var(--c%d);animation-name:%s;transform-origin:%.1fpx 0}"
                      % (uid, color, uid, x))

    width = (grid.width + 2) * size_cell
    height = (grid.height + 5) * size_cell
    viewBox = "%d %d %d %d" % (-size_cell, -2 * size_cell, width, height)
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s" width="%d" height="%d">'
            "<desc>Generated by profile-kit (port of Platane/snk)</desc><style>%s</style>%s</svg>"
            % (viewBox, width, height, "\n".join(styles), "".join(elements)))
