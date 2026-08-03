import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from bmi import calculate_bmi as calculate_bmi_value
from bmi import get_bmi_category
from charts import (
    create_bmi_distribution_chart,
    draw_gauge,
    refresh_bmi_distribution_chart,
)
from database import (
    delete_bmi_record,
    fetch_bmi_records,
    get_bmi_analytics,
    initialize_database,
    save_bmi_record,
)
from export import export_bmi_history


BACKGROUND = "#F4F6F9"
PRIMARY = "#2563EB"
MAX_AGE = 120
MIN_HEIGHT_CM = 50
MAX_HEIGHT_CM = 300
MIN_WEIGHT_KG = 2
MAX_WEIGHT_KG = 500


class BMITrackerApp:
    """The BMI tracker user interface and its local application state."""

    def __init__(self, root):
        self.root = root
        self.history_tree = None
        self.analytics_values = {}
        self.gender = tk.StringVar(root, value="Male")
        self.history_search = tk.StringVar(root)

        self.root.title("Smart BMI Tracker")
        self.root.geometry("1200x920")
        self.root.minsize(1080, 860)
        self.root.configure(bg=BACKGROUND)
        self.configure_styles()
        self.build_shell()
        self.build_calculator_tab()
        self.build_history_tab()
        self.build_analytics_tab()
        self.build_about_tab()

    def configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TNotebook", background=BACKGROUND, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=(20, 10))
        style.map("TNotebook.Tab", background=[("selected", PRIMARY)], foreground=[("selected", "white")])
        style.configure("Page.TLabel", background=BACKGROUND, foreground="#1F2937", font=("Segoe UI", 20, "bold"))
        style.configure("Card.TFrame", background="white")
        style.configure("Card.TLabel", background="white", foreground="#1F2937", font=("Segoe UI", 10, "bold"))
        style.configure("History.Treeview", font=("Segoe UI", 10), rowheight=34, background="white", fieldbackground="white", foreground="#1F2937")
        style.configure("History.Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#EAF0FF", foreground="#1F2937", padding=(8, 10))
        style.map("History.Treeview", background=[("selected", PRIMARY)], foreground=[("selected", "white")])
        for style_name, colour, active_colour in (
            ("Blue.TButton", PRIMARY, "#1D4ED8"),
            ("Green.TButton", "#16A34A", "#15803D"),
            ("Red.TButton", "#DC2626", "#B91C1C"),
        ):
            style.configure(style_name, font=("Segoe UI", 10, "bold"), background=colour, foreground="white", padding=(14, 9), borderwidth=0)
            style.map(style_name, background=[("active", active_colour)])

    def build_shell(self):
        tk.Label(self.root, text="Smart BMI Tracker", font=("Segoe UI", 24, "bold"), bg=PRIMARY, fg="white", pady=15).pack(fill="x")
        notebook = ttk.Notebook(self.root)
        self.notebook = notebook
        self.calculate_tab = tk.Frame(notebook, bg=BACKGROUND)
        self.history_tab = tk.Frame(notebook, bg=BACKGROUND)
        self.analytics_tab = tk.Frame(notebook, bg=BACKGROUND)
        about_tab = tk.Frame(notebook, bg=BACKGROUND)
        notebook.add(self.calculate_tab, text="Calculate")
        notebook.add(self.history_tab, text="History")
        notebook.add(self.analytics_tab, text="Analytics")
        notebook.add(about_tab, text="About BMI")
        notebook.pack(expand=True, fill="both", padx=15, pady=15)
        self.about_tab = about_tab

    def build_calculator_tab(self):
        content = tk.Frame(self.calculate_tab, bg=BACKGROUND)
        content.pack(expand=True, fill="both", padx=20, pady=20)
        for column, weight, minimum in ((0, 2, 270), (1, 4, 420), (2, 2, 300)):
            content.grid_columnconfigure(column, weight=weight, minsize=minimum)
        content.grid_rowconfigure(0, weight=1)

        input_frame = tk.LabelFrame(content, text="Personal Information", font=("Segoe UI", 12, "bold"), bg="white", padx=20, pady=20, bd=1, relief="solid")
        input_frame.grid_columnconfigure(1, weight=1)
        self.name_entry = self.add_entry(input_frame, 0, "Full Name")
        self.age_entry = self.add_entry(input_frame, 1, "Age")
        self.height_entry = self.add_entry(input_frame, 3, "Height (cm)")
        self.weight_entry = self.add_entry(input_frame, 4, "Weight (kg)")
        tk.Label(input_frame, text="Gender", font=("Segoe UI", 11), bg="white").grid(row=2, column=0, sticky="w", pady=10)
        gender_frame = tk.Frame(input_frame, bg="white")
        gender_frame.grid(row=2, column=1, sticky="w", pady=10)
        self.gender_buttons = {}
        for gender_name in ("Male", "Female", "Other"):
            button = tk.Button(gender_frame, text=gender_name, width=8, relief="flat", command=lambda value=gender_name: self.select_gender(value))
            button.pack(side="left", padx=3)
            self.gender_buttons[gender_name] = button
        self.select_gender("Male")
        buttons = tk.Frame(input_frame, bg="white")
        buttons.grid(row=5, column=0, columnspan=2, pady=25)
        tk.Button(buttons, text="Calculate BMI", font=("Segoe UI", 11, "bold"), bg=PRIMARY, fg="white", relief="flat", padx=20, pady=8, command=self.calculate_bmi).pack(side="left", padx=8)
        tk.Button(buttons, text="Clear", font=("Segoe UI", 11, "bold"), bg="#E5E7EB", fg="black", relief="flat", padx=20, pady=8, command=self.clear_fields).pack(side="left", padx=8)

        self.result_frame = tk.LabelFrame(content, text="BMI Result", font=("Segoe UI", 12, "bold"), bg="white", padx=20, pady=20, bd=1, relief="solid")
        tk.Label(self.result_frame, text="Your BMI", font=("Segoe UI", 18, "bold"), bg="white", fg=PRIMARY).pack(pady=(20, 10))
        self.bmi_value = tk.Label(self.result_frame, text="--", font=("Segoe UI", 42, "bold"), bg="white", fg="#1F2937")
        self.bmi_value.pack()
        self.category_label = tk.Label(self.result_frame, text="Waiting for calculation…", font=("Segoe UI", 13), bg="white", fg="#6B7280")
        self.category_label.pack(pady=(5, 10))
        tk.Label(self.result_frame, text="Healthy BMI Range\n18.5 – 24.9", font=("Segoe UI", 11), bg="white", fg="#6B7280", justify="center").pack(pady=(5, 5))
        self.gauge = tk.Canvas(self.result_frame, width=350, height=320, bg="white", highlightthickness=0)
        self.gauge.pack()
        draw_gauge(self.gauge)

        self.advice_frame = tk.LabelFrame(content, text="Health Advice", font=("Segoe UI", 12, "bold"), bg="white", padx=12, pady=20, bd=1, relief="solid")
        self.advice_card = tk.Frame(self.advice_frame, bg="#F8FAFC", bd=1, relief="solid")
        self.advice_card.pack(expand=True, fill="both", padx=6, pady=15)
        self.advice_placeholder = tk.Label(self.advice_card, text="Calculate BMI\n\nto receive personalized\nhealth advice.", font=("Segoe UI", 13), bg="#F8FAFC", fg="#6B7280", justify="center")
        self.advice_placeholder.pack(expand=True, fill="both")
        self.advice_rows = [self.make_advice_row("#FFF7ED", "#C2410C"), self.make_advice_row("#ECFDF5", "#16A34A"), self.make_advice_row("#EFF6FF", PRIMARY)]
        self.advice_dividers = [tk.Frame(self.advice_card, bg="#D1D5DB", height=1), tk.Frame(self.advice_card, bg="#D1D5DB", height=1)]

        input_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.result_frame.grid(row=0, column=1, sticky="nsew", padx=8)
        self.advice_frame.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

    @staticmethod
    def add_entry(parent, row, label):
        tk.Label(parent, text=label, font=("Segoe UI", 11), bg="white").grid(row=row, column=0, sticky="w", pady=10)
        entry = ttk.Entry(parent, width=30)
        entry.grid(row=row, column=1, sticky="ew", pady=10)
        return entry

    def select_gender(self, value):
        self.gender.set(value)
        for gender_name, button in self.gender_buttons.items():
            selected = gender_name == value
            button.config(bg=PRIMARY if selected else "#E5E7EB", fg="white" if selected else "black")

    def make_advice_row(self, icon_background, title_colour):
        row = tk.Frame(self.advice_card, bg="#F8FAFC")
        icon = tk.Label(row, text="", font=("Segoe UI Emoji", 24), bg=icon_background, width=2)
        icon.grid(row=0, column=0, rowspan=2, padx=(0, 15))
        title = tk.Label(row, text="", font=("Segoe UI", 13, "bold"), bg="#F8FAFC", fg=title_colour, wraplength=175, justify="left")
        title.grid(row=0, column=1, sticky="w")
        description = tk.Label(row, text="", font=("Segoe UI", 10), bg="#F8FAFC", fg="#555555", justify="left")
        description.grid(row=1, column=1, sticky="w")
        return row, icon, title, description

    def update_advice(self, bmi):
        self.advice_placeholder.pack_forget()
        for index, advice_row in enumerate(self.advice_rows):
            advice_row[0].pack(fill="x", padx=15, pady=(20, 10) if index == 0 else 10)
            if index < len(self.advice_dividers):
                self.advice_dividers[index].pack(fill="x", padx=20, pady=15)
        if bmi < 18.5:
            tips = (("🥛", "Increase healthy calories", "Eat protein, nuts\nand dairy foods."), ("🏋", "Strength training", "Build muscle with\nlight workouts."), ("💧", "Stay hydrated", "Drink enough water\nevery day."))
        elif bmi < 25:
            tips = (("🍎", "Maintain balanced diet", "Keep eating healthy\nmeals."), ("🚶", "Exercise daily", "30 minutes of\nactivity."), ("😴", "Sleep well", "Sleep 7–8 hours\ndaily."))
        elif bmi < 30:
            tips = (("🍴", "Reduce sugary foods", "Avoid sweets and\nsoft drinks."), ("🚶", "Walk daily", "Walk at least\n30 minutes."), ("🥗", "Eat vegetables", "Increase fiber and\nvitamins."))
        else:
            tips = (("🥦", "Healthy diet", "Avoid processed\nfoods."), ("🏃", "Exercise regularly", "150 minutes per\nweek."), ("💧", "Drink water", "Stay hydrated\nthroughout the day."))
        for widgets, tip in zip(self.advice_rows, tips):
            widgets[1].config(text=tip[0])
            widgets[2].config(text=tip[1])
            widgets[3].config(text=tip[2])

    def build_history_tab(self):
        self.history_tab.grid_columnconfigure(0, weight=1)
        self.history_tab.grid_rowconfigure(2, weight=1)
        ttk.Label(self.history_tab, text="BMI History", style="Page.TLabel").grid(row=0, column=0, sticky="w", padx=25, pady=(25, 15))
        search_card = ttk.Frame(self.history_tab, style="Card.TFrame", padding=18)
        search_card.grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 15))
        search_card.grid_columnconfigure(1, weight=1)
        ttk.Label(search_card, text="Search by Name", style="Card.TLabel").grid(row=0, column=0, padx=(0, 10))
        search_entry = ttk.Entry(search_card, textvariable=self.history_search)
        search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        search_entry.bind("<Return>", lambda _event: self.load_history(self.history_search.get()))
        ttk.Button(search_card, text="Search", style="Blue.TButton", command=lambda: self.load_history(self.history_search.get())).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(search_card, text="Show All", style="Blue.TButton", command=self.show_all_history).grid(row=0, column=3)
        table_card = ttk.Frame(self.history_tab, style="Card.TFrame", padding=15)
        table_card.grid(row=2, column=0, sticky="nsew", padx=25, pady=(0, 15))
        table_card.grid_columnconfigure(0, weight=1)
        table_card.grid_rowconfigure(0, weight=1)
        columns = ("date", "name", "age", "gender", "height", "weight", "bmi", "category")
        self.history_tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse", style="History.Treeview")
        headings = ("Date", "Name", "Age", "Gender", "Height (cm)", "Weight (kg)", "BMI", "Category")
        widths = (160, 165, 60, 90, 105, 105, 75, 155)
        for column, heading, width in zip(columns, headings, widths):
            self.history_tree.heading(column, text=heading)
            self.history_tree.column(column, width=width, minwidth=60, anchor="center", stretch=True)
        for column in ("date", "name", "category"):
            self.history_tree.column(column, anchor="w")
        self.history_tree.tag_configure("even", background="#FFFFFF")
        self.history_tree.tag_configure("odd", background="#F1F5F9")
        scrollbar = ttk.Scrollbar(table_card, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        actions = ttk.Frame(self.history_tab, style="Card.TFrame", padding=15)
        actions.grid(row=3, column=0, sticky="ew", padx=25, pady=(0, 25))
        ttk.Button(actions, text="Delete Selected", style="Red.TButton", command=self.delete_history_record).pack(side="left")
        ttk.Button(actions, text="Export CSV", style="Green.TButton", command=self.export_history).pack(side="left", padx=10)
        ttk.Button(actions, text="Refresh", style="Blue.TButton", command=self.load_history).pack(side="left")
        self.load_history()

    def show_all_history(self):
        self.history_search.set("")
        self.load_history()

    def load_history(self, search_name=""):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for index, record in enumerate(fetch_bmi_records(search_name)):
            tag = "even" if index % 2 == 0 else "odd"
            self.history_tree.insert("", "end", iid=str(record[0]), values=record[1:], tags=(tag,))

    def delete_history_record(self):
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("No record selected", "Select a BMI record first.")
            return
        if messagebox.askyesno("Delete record", "Delete the selected BMI record?"):
            delete_bmi_record(int(selection[0]))
            self.load_history(self.history_search.get())
            self.refresh_analytics()

    @staticmethod
    def export_history():
        destination = filedialog.asksaveasfilename(title="Export BMI History", defaultextension=".csv", initialfile="bmi_history.csv", filetypes=[("CSV files", "*.csv")])
        if destination:
            count = export_bmi_history(destination)
            messagebox.showinfo("Export complete", f"{count} BMI record(s) exported.")

    def build_analytics_tab(self):
       
        self.analytics_canvas = tk.Canvas(self.analytics_tab, bg=BACKGROUND, highlightthickness=0)
        analytics_scrollbar = ttk.Scrollbar(self.analytics_tab, orient="vertical", command=self.analytics_canvas.yview)
        self.analytics_canvas.configure(yscrollcommand=analytics_scrollbar.set)
        self.analytics_canvas.pack(side="left", expand=True, fill="both")
        analytics_scrollbar.pack(side="right", fill="y")

        analytics_content = tk.Frame(self.analytics_canvas, bg=BACKGROUND)
        content_window = self.analytics_canvas.create_window((0, 0), window=analytics_content, anchor="nw")
        analytics_content.bind(
            "<Configure>",
            lambda _event: self.analytics_canvas.configure(scrollregion=self.analytics_canvas.bbox("all")),
        )
        self.analytics_canvas.bind(
            "<Configure>",
            lambda event: self.analytics_canvas.itemconfigure(content_window, width=event.width),
        )
        self.root.bind_all("<MouseWheel>", self.scroll_analytics, add="+")

        analytics_content.grid_columnconfigure(0, weight=1)
        analytics_content.grid_rowconfigure(2, weight=1, minsize=310)
        ttk.Label(analytics_content, text="BMI Analytics", style="Page.TLabel").grid(row=0, column=0, sticky="w", padx=25, pady=(25, 10))
        cards = tk.Frame(analytics_content, bg=BACKGROUND)
        cards.grid(row=1, column=0, sticky="ew", padx=25, pady=(0, 12))
        for row in range(2):
            cards.grid_rowconfigure(row, weight=1)
        for column in range(3):
            cards.grid_columnconfigure(column, weight=1)
        card_data = (("▣", "Total Records", "#2563EB", "total"), ("⚖", "Average BMI", "#16A34A", "average"), ("↓", "Underweight", "#F97316", "underweight"), ("✓", "Normal Weight", "#14B8A6", "normal"), ("↑", "Overweight", "#8B5CF6", "overweight"), ("!", "Obese", "#DC2626", "obese"))
        for index, card in enumerate(card_data):
            self.make_summary_card(cards, index // 3, index % 3, *card)
        chart_area = tk.Frame(analytics_content, bg=BACKGROUND)
        chart_area.grid(row=2, column=0, sticky="nsew", padx=25, pady=(0, 12))
        chart_area.grid_columnconfigure(0, weight=1)
        chart_area.grid_columnconfigure(1, weight=1)
        chart_area.grid_rowconfigure(0, weight=1)
        line_card = tk.Frame(chart_area, bg="white", highlightbackground="#E5E7EB", highlightthickness=1)
        pie_card = tk.Frame(chart_area, bg="white", highlightbackground="#E5E7EB", highlightthickness=1)
        line_card.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        pie_card.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        line_figure = Figure(figsize=(5, 3.4), dpi=100, facecolor="white")
        self.line_axes = line_figure.add_subplot(111)
        line_figure.subplots_adjust(bottom=0.24)
        self.line_canvas = FigureCanvasTkAgg(line_figure, master=line_card)
        self.line_canvas.get_tk_widget().pack(expand=True, fill="both")
      
        self.pie_axes, self.pie_canvas = create_bmi_distribution_chart(pie_card)
        insights_card = tk.Frame(analytics_content, bg="white", highlightbackground="#E5E7EB", highlightthickness=1)
        insights_card.grid(row=3, column=0, sticky="ew", padx=25, pady=(0, 25))
        tk.Label(insights_card, text="Insights", font=("Segoe UI", 12, "bold"), bg="white", fg="#1F2937").pack(anchor="w", padx=18, pady=(14, 4))
        self.insights_label = tk.Label(insights_card, text="Add BMI records to see personalised insights.", font=("Segoe UI", 10), bg="white", fg="#4B5563", justify="left")
        self.insights_label.pack(anchor="w", padx=18, pady=(0, 14))
        ttk.Button(insights_card, text="Refresh Analytics", style="Blue.TButton", command=self.refresh_analytics).pack(anchor="e", padx=18, pady=(0, 14))
        self.refresh_analytics()

    def scroll_analytics(self, event):
        """Scroll only while the Analytics tab is the selected notebook page."""
        if self.notebook.select() == str(self.analytics_tab):
            self.analytics_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def build_about_tab(self):
        """Build a responsive, scrollable explanation of BMI and its limits."""
        about_canvas = tk.Canvas(self.about_tab, bg=BACKGROUND, highlightthickness=0)
        about_scrollbar = ttk.Scrollbar(self.about_tab, orient="vertical", command=about_canvas.yview)
        about_canvas.configure(yscrollcommand=about_scrollbar.set)
        about_canvas.pack(side="left", expand=True, fill="both")
        about_scrollbar.pack(side="right", fill="y")

        content = tk.Frame(about_canvas, bg=BACKGROUND)
        content_window = about_canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda _event: about_canvas.configure(scrollregion=about_canvas.bbox("all")))

        def resize_content(event):
            about_canvas.itemconfigure(content_window, width=event.width)
            intro.configure(wraplength=max(500, event.width - 90))
            disclaimer_text.configure(wraplength=max(500, event.width - 100))

        about_canvas.bind("<Configure>", resize_content)
        self.about_canvas = about_canvas
        self.root.bind_all("<MouseWheel>", self.scroll_about, add="+")
        content.grid_columnconfigure(0, weight=1)

        tk.Label(
            content,
            text="📘 About Body Mass Index (BMI)",
            font=("Segoe UI", 22, "bold"),
            bg=BACKGROUND,
            fg="#1F2937",
        ).grid(row=0, column=0, sticky="w", padx=32, pady=(28, 8))
        intro = tk.Label(
            content,
            text=(
                "Body Mass Index (BMI) is a simple health indicator that estimates whether "
                "a person's weight is appropriate for their height. Although BMI does not "
                "directly measure body fat, it is widely used by healthcare professionals "
                "as a quick screening tool."
            ),
            font=("Segoe UI", 11),
            bg=BACKGROUND,
            fg="#4B5563",
            justify="left",
            anchor="w",
            wraplength=1000,
        )
        intro.grid(row=1, column=0, sticky="ew", padx=32, pady=(0, 20))

        formula_card = self.make_about_card(content, 2, "BMI Formula")
        formula_box = tk.Frame(formula_card, bg="#EFF6FF", highlightbackground="#BFDBFE", highlightthickness=1)
        formula_box.pack(fill="x", padx=20, pady=(0, 16))
        tk.Label(formula_box, text="BMI = Weight (kg) / Height² (m²)", font=("Segoe UI", 17, "bold"), bg="#EFF6FF", fg=PRIMARY).pack(padx=18, pady=16)
        tk.Label(formula_card, text="Example:", font=("Segoe UI", 11, "bold"), bg="white", fg="#1F2937").pack(anchor="w", padx=20)
        tk.Label(formula_card, text="Weight = 60 kg\nHeight = 1.70 m\n\nBMI = 60 / (1.70 × 1.70)\nBMI = 20.76", font=("Segoe UI", 11), bg="white", fg="#4B5563", justify="left").pack(anchor="w", padx=20, pady=(6, 20))

        categories_card = self.make_about_card(content, 3, "BMI Categories")
        table = tk.Frame(categories_card, bg="#E5E7EB")
        table.pack(fill="x", padx=20, pady=(0, 20))
        for column, (heading, width) in enumerate((("Category", 28), ("BMI Range", 22), ("Color", 16))):
            tk.Label(table, text=heading, width=width, font=("Segoe UI", 10, "bold"), bg="#EAF0FF", fg="#1F2937", anchor="w", padx=12, pady=10).grid(row=0, column=column, sticky="ew", padx=1, pady=1)
            table.grid_columnconfigure(column, weight=1)
        category_rows = (
            ("🔵 Underweight", "Below 18.5", "Blue", "#3B82F6"),
            ("🟢 Normal Weight", "18.5 – 24.9", "Green", "#22C55E"),
            ("🟠 Overweight", "25.0 – 29.9", "Orange", "#F59E0B"),
            ("🔴 Obese", "30 and above", "Red", "#EF4444"),
        )
        for row_number, (category, bmi_range, colour_name, colour) in enumerate(category_rows, start=1):
            row_background = "#FFFFFF" if row_number % 2 else "#F8FAFC"
            for column, value in enumerate((category, bmi_range, colour_name)):
                foreground = colour if column == 2 else "#374151"
                tk.Label(table, text=value, font=("Segoe UI", 10), bg=row_background, fg=foreground, anchor="w", padx=12, pady=9).grid(row=row_number, column=column, sticky="ew", padx=1, pady=1)

        tips_card = self.make_about_card(content, 4, "Healthy Lifestyle Tips")
        tips = (
            "🥗  Eat a balanced diet rich in fruits and vegetables.",
            "🚶  Exercise for at least 30 minutes every day.",
            "💧  Drink plenty of water.",
            "😴  Sleep 7–9 hours each night.",
            "🩺  Get regular health checkups.",
        )
        for tip in tips:
            tk.Label(tips_card, text=tip, font=("Segoe UI", 11), bg="white", fg="#374151", anchor="w", justify="left").pack(fill="x", padx=20, pady=5)
        tk.Frame(tips_card, bg="white", height=10).pack()

        disclaimer_card = tk.Frame(content, bg="#FFFBEB", highlightbackground="#FDE68A", highlightthickness=1)
        disclaimer_card.grid(row=5, column=0, sticky="ew", padx=32, pady=(0, 18))
        tk.Label(disclaimer_card, text="⚠ Disclaimer", font=("Segoe UI", 12, "bold"), bg="#FFFBEB", fg="#92400E").pack(anchor="w", padx=20, pady=(16, 5))
        disclaimer_text = tk.Label(disclaimer_card, text="This application is intended for educational purposes only. BMI is only a screening tool and should not replace professional medical advice.", font=("Segoe UI", 10), bg="#FFFBEB", fg="#78350F", justify="left", anchor="w", wraplength=1000)
        disclaimer_text.pack(fill="x", padx=20, pady=(0, 16))

        tk.Label(content, text="Developed using Python, Tkinter, SQLite and Matplotlib.", font=("Segoe UI", 9), bg=BACKGROUND, fg="#6B7280").grid(row=6, column=0, pady=(0, 28))

    @staticmethod
    def make_about_card(parent, row, title):
        """Create a white card with a consistent title and responsive width."""
        card = tk.Frame(parent, bg="white", highlightbackground="#E5E7EB", highlightthickness=1)
        card.grid(row=row, column=0, sticky="ew", padx=32, pady=(0, 18))
        tk.Label(card, text=title, font=("Segoe UI", 13, "bold"), bg="white", fg="#1F2937").pack(anchor="w", padx=20, pady=(16, 12))
        return card

    def scroll_about(self, event):
        """Scroll the About BMI page with the mouse wheel when it is visible."""
        if self.notebook.select() == str(self.about_tab):
            self.about_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def make_summary_card(self, parent, row, column, icon, title, accent, key):
        card = tk.Frame(parent, bg="white", highlightbackground="#E5E7EB", highlightthickness=1)
        card.grid(row=row, column=column, sticky="nsew", padx=7, pady=7)
        tk.Label(card, text=icon, font=("Segoe UI Symbol", 20), bg="white", fg=accent).pack(anchor="w", padx=16, pady=(14, 0))
        tk.Label(card, text=title, font=("Segoe UI", 10, "bold"), bg="white", fg="#6B7280").pack(anchor="w", padx=16, pady=(8, 0))
        value = tk.Label(card, text="0", font=("Segoe UI", 21, "bold"), bg="white", fg="#1F2937")
        value.pack(anchor="w", padx=16, pady=(2, 14))
        self.analytics_values[key] = value

    def refresh_analytics(self):
        data = get_bmi_analytics()
        for key, value in (("total", data["total_records"]), ("average", f"{data['average_bmi']:.1f}" if data["total_records"] else "--"), ("underweight", data["underweight"]), ("normal", data["normal"]), ("overweight", data["overweight"]), ("obese", data["obese"])):
            self.analytics_values[key].config(text=str(value))
        refresh_bmi_distribution_chart(self.pie_axes, self.pie_canvas)
        self.line_axes.clear()
        records = data["trend_records"]
        if records:
            positions = list(range(1, len(records) + 1))
            bmi_values = [record[2] for record in records]
            labels_for_line = [record[1].split(",")[0] for record in records]
            self.line_axes.plot(positions, bmi_values, marker="o", color=PRIMARY, linewidth=2.5, markersize=5)
            self.line_axes.fill_between(positions, bmi_values, color="#DBEAFE", alpha=0.7)
            shown = min(len(records), 8)
            self.line_axes.set_xticks(positions[-shown:])
            self.line_axes.set_xticklabels(labels_for_line[-shown:], rotation=25, ha="right", fontsize=8)
            self.line_axes.set_ylabel("BMI", fontsize=9)
            self.line_axes.grid(axis="y", alpha=0.25)
        else:
            self.line_axes.text(0.5, 0.5, "No BMI records yet", ha="center", va="center", color="#6B7280", transform=self.line_axes.transAxes)
        self.line_axes.set_title("BMI Trend Over Time", fontsize=12, fontweight="bold", color="#1F2937", pad=12)
        for spine_name in ("top", "right"):
            self.line_axes.spines[spine_name].set_visible(False)
        self.line_canvas.draw_idle()
        if not data["total_records"]:
            self.insights_label.config(text="Add BMI records to see personalised insights.")
            return
        most_common = max(data["category_counts"], key=data["category_counts"].get)
        self.insights_label.config(text=(f"• Most users are {most_common}.\n• Average BMI is {data['average_bmi']:.1f}.\n• Highest BMI recorded is {data['highest_bmi']:.1f}.\n• Lowest BMI recorded is {data['lowest_bmi']:.1f}."))

    def calculate_bmi(self):
        try:
            name = self.name_entry.get().strip() or "Unknown"
            age = int(self.age_entry.get())
            height = float(self.height_entry.get())
            weight = float(self.weight_entry.get())
            if not 1 <= age <= MAX_AGE or not MIN_HEIGHT_CM <= height <= MAX_HEIGHT_CM or not MIN_WEIGHT_KG <= weight <= MAX_WEIGHT_KG:
                raise ValueError
            bmi = calculate_bmi_value(height, weight)
        except ValueError:
            self.bmi_value.config(text="--")
            self.category_label.config(text="Enter a valid age, height, and weight.", fg="#DC2626")
            return
        category, colour = get_bmi_category(age, bmi)
        self.bmi_value.config(text=str(bmi))
        self.category_label.config(text=category, fg=colour)
        draw_gauge(self.gauge, bmi)
        self.update_advice(bmi)
        save_bmi_record(name, age, self.gender.get(), height, weight, bmi, category)
        self.load_history()
        self.refresh_analytics()

    def clear_fields(self):
        for entry in (self.name_entry, self.age_entry, self.height_entry, self.weight_entry):
            entry.delete(0, tk.END)
        self.select_gender("Male")
        self.bmi_value.config(text="--")
        self.category_label.config(text="Waiting for calculation…", fg="#6B7280")
        for row, *_widgets in self.advice_rows:
            row.pack_forget()
        for divider in self.advice_dividers:
            divider.pack_forget()
        self.advice_placeholder.pack(expand=True, fill="both")
        draw_gauge(self.gauge)


def main():
    initialize_database()
    root = tk.Tk()
    BMITrackerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
