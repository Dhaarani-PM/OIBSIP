import math
import sqlite3
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from database import DATABASE_FILE


PIE_LABELS = ("Underweight", "Normal Weight", "Overweight", "Obese")
PIE_COLOURS = ("#3B82F6", "#22C55E", "#F59E0B", "#EF4444")


def _bmi_angle(bmi):
    bmi = max(0, min(float(bmi), 40))
    if bmi <= 18.5:
        return 180 - bmi / 18.5 * 45
    if bmi <= 25:
        return 135 - (bmi - 18.5) / 6.5 * 45
    if bmi <= 30:
        return 90 - (bmi - 25) / 5 * 45
    return 45 - (bmi - 30) / 10 * 45


def _draw(canvas, bmi):
    canvas.delete("all")
    cx, cy, radius = 175, 170, 100
    for color, start, end in (("#3B82F6", 180, 135), ("#22C55E", 135, 90), ("#F59E0B", 90, 45), ("#EF4444", 45, 0)):
        for angle in range(start, end, -2):
            x1 = cx + radius * math.cos(math.radians(angle))
            y1 = cy - radius * math.sin(math.radians(angle))
            x2 = cx + radius * math.cos(math.radians(angle - 2))
            y2 = cy - radius * math.sin(math.radians(angle - 2))
            canvas.create_line(x1, y1, x2, y2, width=15, fill=color)
    angle = _bmi_angle(bmi)
    x = cx + 85 * math.cos(math.radians(angle))
    y = cy - 85 * math.sin(math.radians(angle))
    canvas.create_line(cx, cy, x, y, width=4, fill="black", capstyle="round")
    canvas.create_oval(cx - 10, cy - 10, cx + 10, cy + 10, fill="black")
    for x, y, text in ((62, 180, "0"), (100, 82, "18.5"), (175, 52, "25"), (250, 82, "30"), (288, 180, "40")):
        canvas.create_text(x, y, text=text, font=("Segoe UI", 11, "bold"))


def draw_gauge(canvas, bmi=0, duration=1200, frames=60):
    """Animate the gauge to a BMI value over 1.2 seconds."""
    target = max(0, min(float(bmi), 40))
    job = getattr(canvas, "gauge_animation_job", None)
    if job is not None:
        try:
            canvas.after_cancel(job)
        except tk.TclError:
            pass
    if not hasattr(canvas, "gauge_current_bmi"):
        canvas.gauge_current_bmi = target
        _draw(canvas, target)
        return
    start = canvas.gauge_current_bmi
    delay = max(1, duration // frames)

    def animate(frame):
        eased = 1 - (1 - frame / frames) ** 3
        current = start + (target - start) * eased
        canvas.gauge_current_bmi = current
        _draw(canvas, current)
        if frame < frames:
            canvas.gauge_animation_job = canvas.after(delay, lambda: animate(frame + 1))
        else:
            canvas.gauge_animation_job = None
            canvas.gauge_current_bmi = target

    animate(0)


def fetch_bmi_category_counts():
    """Read BMI values directly from SQLite and return the four chart counts."""
    query = """
        SELECT
            COALESCE(SUM(CASE WHEN bmi < 18.5 THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN bmi >= 18.5 AND bmi < 25 THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN bmi >= 25 AND bmi < 30 THEN 1 ELSE 0 END), 0),
            COALESCE(SUM(CASE WHEN bmi >= 30 THEN 1 ELSE 0 END), 0)
        FROM bmi_history
    """
    with sqlite3.connect(DATABASE_FILE) as connection:
        counts = connection.execute(query).fetchone()
    return tuple(int(count or 0) for count in counts)


def create_bmi_distribution_chart(parent):
    """Create the right-side pie-chart card content and return its canvas state."""
    tk.Label(
        parent,
        text="BMI Category Distribution",
        font=("Segoe UI", 12, "bold"),
        bg="white",
        fg="#1F2937",
    ).pack(anchor="w", padx=18, pady=(14, 0))
    figure = Figure(figsize=(5.5, 3.5), dpi=100, facecolor="white")
    axes = figure.add_subplot(111)
    
    figure.subplots_adjust(left=0.04, right=0.62, top=0.90, bottom=0.06)
    canvas = FigureCanvasTkAgg(figure, master=parent)
    canvas.get_tk_widget().pack(expand=True, fill="both", padx=8, pady=(0, 8))
    return axes, canvas


def refresh_bmi_distribution_chart(axes, canvas):
    """Redraw the pie chart from the latest records in the SQLite database."""
    counts = fetch_bmi_category_counts()
    axes.clear()
    axes.set_facecolor("white")

    if sum(counts):
        wedges, _labels, _percentages = axes.pie(
            counts,
            labels=None,
            colors=PIE_COLOURS,
            explode=(0, 0.08, 0, 0),
            autopct="%1.0f%%",
            startangle=90,
            shadow=False,
            pctdistance=0.68,
            textprops={"fontfamily": "Segoe UI", "fontsize": 8, "color": "#1F2937"},
            wedgeprops={"linewidth": 1, "edgecolor": "white"},
        )
        axes.legend(
            wedges,
            PIE_LABELS,
            loc="center left",
            bbox_to_anchor=(1.05, 0.5),
            borderaxespad=0,
            frameon=False,
            prop={"family": "Segoe UI", "size": 8},
        )
    else:
        axes.set_axis_off()
        axes.text(
            0.5,
            0.5,
            "No Data Available",
            ha="center",
            va="center",
            fontfamily="Segoe UI",
            fontsize=12,
            fontweight="bold",
            color="#6B7280",
            transform=axes.transAxes,
        )
    axes.set_aspect("equal", adjustable="box")
    canvas.draw_idle()
