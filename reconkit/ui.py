import re
import shutil
import textwrap
from typing import Iterable

class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

def color(text: str, code: str, enabled: bool = True) -> str:
    return f"{code}{text}{C.RESET}" if enabled else text

def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)

def term_width(default: int = 104) -> int:
    return max(72, min(shutil.get_terminal_size((default, 24)).columns, 150))

def hr(title: str = "", *, colorize: bool = True) -> str:
    width = term_width()
    if not title:
        return color("─" * width, C.DIM, colorize)
    label = f" {title} "
    left = "─" * 3
    right = "─" * max(1, width - len(strip_ansi(label)) - len(left))
    return f"{color(left, C.DIM, colorize)}{color(label, C.BOLD + C.CYAN, colorize)}{color(right, C.DIM, colorize)}"

def box(lines: Iterable[str], *, title: str = "", accent: str = C.CYAN, colorize: bool = True) -> str:
    content = list(lines)
    width = min(term_width(), max([len(strip_ansi(line)) for line in content] + [len(title), 54]) + 4)
    top_label = f" {title} " if title else ""
    top = "╭" + top_label + "─" * max(0, width - len(top_label) - 2) + "╮"
    bottom = "╰" + "─" * (width - 2) + "╯"
    out = [color(top, accent, colorize)]
    for line in content:
        pad = width - 4 - len(strip_ansi(line))
        out.append(color("│ ", accent, colorize) + line + " " * max(0, pad) + color(" │", accent, colorize))
    out.append(color(bottom, accent, colorize))
    return "\n".join(out)

def visible_len(text: object) -> int:
    return len(strip_ansi(str(text)))

def truncate_visible(text: object, width: int) -> str:
    raw = str(text)
    plain = strip_ansi(raw)
    if len(plain) <= width:
        return raw
    return plain[: max(0, width - 1)] + "…"

def wrap_cell(value: object, width: int) -> list[str]:
    plain = strip_ansi(str(value))
    if not plain:
        return [""]
    wrapped: list[str] = []
    for line in plain.splitlines() or [plain]:
        parts = textwrap.wrap(line, width=width, break_long_words=True, break_on_hyphens=False)
        wrapped.extend(parts or [""])
    return wrapped or [""]

def fit_widths(headers: list[str], rows: list[list[str]], max_widths: list[int] | None) -> list[int]:
    columns = len(headers)
    available = term_width() - (columns - 1) * 3
    natural = [len(header) for header in headers]
    for row in rows:
        for idx, value in enumerate(row):
            natural[idx] = max(natural[idx], min(visible_len(value), 60))
    if max_widths:
        natural = [min(natural[idx], max_widths[idx]) for idx in range(columns)]
    min_widths = [max(4, min(len(headers[idx]), 12)) for idx in range(columns)]
    widths = natural[:]
    while sum(widths) > available and any(widths[idx] > min_widths[idx] for idx in range(columns)):
        idx = max(range(columns), key=lambda item: widths[item] - min_widths[item])
        widths[idx] -= 1
    return [max(min_widths[idx], widths[idx]) for idx in range(columns)]

def table(headers: list[str], rows: list[list[str]], *, colorize: bool = True, max_widths: list[int] | None = None, wrap: bool = True) -> str:
    if not rows:
        return color("No results.", C.DIM, colorize)
    widths = fit_widths(headers, rows, max_widths)

    def render_line(cells: list[object], *, header: bool = False) -> str:
        chunks = []
        for idx, cell in enumerate(cells):
            value = truncate_visible(cell, widths[idx]) if header or not wrap else str(cell)
            pad = widths[idx] - visible_len(value)
            chunks.append(value + " " * max(0, pad))
        line = " │ ".join(chunks)
        return color(line, C.BOLD + C.WHITE, colorize) if header else line

    output = [render_line(headers, header=True)]
    output.append(color("─┼─".join("─" * width for width in widths), C.DIM, colorize))
    for row in rows:
        wrapped_cells = [wrap_cell(value, widths[idx]) if wrap else [truncate_visible(value, widths[idx])] for idx, value in enumerate(row)]
        height = max(len(cell) for cell in wrapped_cells)
        for line_idx in range(height):
            line_cells = []
            for col_idx, cell_lines in enumerate(wrapped_cells):
                value = cell_lines[line_idx] if line_idx < len(cell_lines) else ""
                line_cells.append(value + " " * max(0, widths[col_idx] - visible_len(value)))
            output.append(" │ ".join(line_cells))
    return "\n".join(output)

def pill(label: str, value: str, accent: str, *, colorize: bool = True) -> str:
    return color(f" {label} ", C.BOLD + accent, colorize) + " " + color(value, C.WHITE, colorize)
