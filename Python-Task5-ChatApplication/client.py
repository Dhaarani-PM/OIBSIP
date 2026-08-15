"""Tkinter client for the local real-time chat server."""

import base64
import queue
import socket
import struct
import threading
import tkinter as tk
import tkinter.font as tkfont
import zlib
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

from PIL import Image, ImageDraw, ImageFilter, ImageTk

from config import HOST, PORT
from emoji import replace_shortcodes
from protocol import decode_messages, send_json


class ChatClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Python Chat Application")
        self.root.geometry("900x580")
        self.root.minsize(720, 450)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.socket = None
        self.send_lock = threading.Lock()
        self.events = queue.Queue()
        self.username = None
        self.current_room = None
        self.room_items = []
        self.private_rooms_supported = True
        self.notifications_enabled = tk.BooleanVar(value=True)
        self.notification_log = []
        self.connected = False
        self.build_login()
        self.connect()
        self.root.after(80, self.process_events)

    def connect(self):
        try:
            self.socket = socket.create_connection((HOST, PORT), timeout=4)
            self.socket.settimeout(None)
            self.connected = True
            threading.Thread(target=self.receive_loop, daemon=True).start()
        except OSError:
            self.connected = False
            self.status_var.set(f"Offline — start server at {HOST}:{PORT}")

    def send(self, payload):
        if not self.connected or not self.socket:
            messagebox.showerror("Not connected", "The server is unavailable. Start server.py and reopen the client.")
            return False
        try:
            send_json(self.socket, payload, self.send_lock)
            return True
        except OSError:
            self.events.put({"type": "disconnected"})
            return False

    def receive_loop(self):
        buffer = ""
        try:
            while True:
                data = self.socket.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="replace")
                messages, buffer = decode_messages(buffer)
                for event in messages:
                    self.events.put(event)
        except OSError:
            pass
        self.events.put({"type": "disconnected"})

    def clear(self):
        for child in self.root.winfo_children():
            child.destroy()

    def create_login_glass(self, left, top, right, bottom, canvas_width, canvas_height):
        """Return a smooth, blurred glass rendering of the background below it."""
        shadow = 12
        radius = 28
        panel_width, panel_height = right - left, bottom - top
        source = self.login_background_source
        background_left = canvas_width // 2 - source.width // 2
        background_top = canvas_height // 2 - source.height // 2

        # Sample the exact part of the centred background behind the panel.
        backdrop = Image.new("RGBA", (panel_width, panel_height), "#041313")
        source_box = (left - background_left, top - background_top,
                      right - background_left, bottom - background_top)
        backdrop.alpha_composite(source.crop(source_box), (0, 0))
        backdrop = backdrop.filter(ImageFilter.GaussianBlur(radius=18))

        # Smooth tint and a hairline border, with no stipple, grain, or pattern.
        glass = Image.alpha_composite(backdrop, Image.new("RGBA", backdrop.size, (3, 22, 20, 178)))
        mask = Image.new("L", backdrop.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, panel_width - 1, panel_height - 1), radius=radius, fill=255)
        glass.putalpha(mask)
        border = ImageDraw.Draw(glass)
        border.rounded_rectangle((0, 0, panel_width - 1, panel_height - 1), radius=radius,
                                outline=(177, 219, 208, 145), width=1)

        rendered = Image.new("RGBA", (panel_width + shadow * 2, panel_height + shadow * 2))
        glow = Image.new("RGBA", rendered.size)
        ImageDraw.Draw(glow).rounded_rectangle(
            (shadow, shadow, shadow + panel_width - 1, shadow + panel_height - 1),
            radius=radius, fill=(0, 10, 9, 115)
        )
        rendered.alpha_composite(glow.filter(ImageFilter.GaussianBlur(radius=8)))
        rendered.alpha_composite(glass, (shadow, shadow))
        return ImageTk.PhotoImage(rendered)

    def build_login(self):
        self.clear()
        self.status_var = tk.StringVar(value="Connecting…")
        self.root.title("NEXORA")
        self.root.configure(bg="#041313")
        asset_root = Path(__file__).resolve().parent
        self.login_background_image = tk.PhotoImage(
            file=str(asset_root / "Background" / "Bgforloginscreen_converted.png")
        )
        self.login_background_source = Image.open(
            asset_root / "Background" / "Bgforloginscreen_converted.png"
        ).convert("RGBA")
        canvas = tk.Canvas(self.root, bg="#041313", bd=0, highlightthickness=0)
        canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        background = canvas.create_image(0, 0, image=self.login_background_image, anchor="center")

        # This image is created from the live background below the panel on
        # resize, then blurred and dark-tinted.  It is not a texture or a
        # separate background asset.
        glass_panel = canvas.create_image(0, 0, anchor="nw")
        title = canvas.create_text(0, 0, text="Welcome back", font=("Segoe UI", 25, "bold"), fill="#f1f8f5")
        subtitle = canvas.create_text(0, 0, text="Please enter your details.", font=("Segoe UI", 10), fill="#b6cbc5")
        username_label = canvas.create_text(0, 0, text="Username", anchor="w", font=("Segoe UI", 10, "bold"), fill="#edf7f4")
        password_label = canvas.create_text(0, 0, text="Password", anchor="w", font=("Segoe UI", 10, "bold"), fill="#edf7f4")
        username_line = canvas.create_line(0, 0, 1, 0, fill="#a6c5bd")
        password_line = canvas.create_line(0, 0, 1, 0, fill="#a6c5bd")
        status = canvas.create_text(0, 0, font=("Segoe UI", 9), fill="#c5dfd8")
        register_text = canvas.create_text(0, 0, text="Don't have an account?  Register here", font=("Segoe UI", 9), fill="#c5e7df", tags="register")
        login_button = self.rounded_rectangle(canvas, 0, 0, 1, 1, 12, fill="#061313", outline="#376f69", width=1, tags="login")
        login_text = canvas.create_text(0, 0, text="Log in", font=("Segoe UI", 11, "bold"), fill="#f3fbf8", tags="login")

        self.username_entry = tk.Entry(canvas, font=("Segoe UI", 10), bd=0, relief="flat", highlightthickness=0,
                                       bg="#061f1d", fg="#f2fbf8", insertbackground="#f2fbf8")
        self.password_entry = tk.Entry(canvas, font=("Segoe UI", 10), bd=0, relief="flat", highlightthickness=0,
                                       bg="#061f1d", fg="#f2fbf8", insertbackground="#f2fbf8", show="●")
        username_window = canvas.create_window(0, 0, anchor="w", window=self.username_entry, height=27)
        password_window = canvas.create_window(0, 0, anchor="w", window=self.password_entry, height=27)

        def layout(event):
            width, height = event.width, event.height
            canvas.coords(background, width // 2, height // 2)
            left, right = int(width * .51), width - 24
            top, bottom = 18, height - 18
            form_width = min(360, right - left - 52)
            form_left = left + max((right - left - form_width) // 2, 26)
            form_center = form_left + form_width // 2
            start_y = max(top + 72, height // 2 - 165)
            self.login_glass_image = self.create_login_glass(left, top, right, bottom, width, height)
            canvas.itemconfigure(glass_panel, image=self.login_glass_image)
            canvas.coords(glass_panel, left - 12, top - 12)
            canvas.coords(title, form_center, start_y)
            canvas.coords(subtitle, form_center, start_y + 38)
            canvas.coords(username_label, form_left, start_y + 90)
            canvas.coords(username_window, form_left, start_y + 110)
            canvas.itemconfigure(username_window, width=form_width)
            canvas.coords(username_line, form_left, start_y + 140, form_left + form_width, start_y + 140)
            canvas.coords(password_label, form_left, start_y + 172)
            canvas.coords(password_window, form_left, start_y + 192)
            canvas.itemconfigure(password_window, width=form_width)
            canvas.coords(password_line, form_left, start_y + 222, form_left + form_width, start_y + 222)
            canvas.coords(login_button, *self.rounded_rectangle_points(form_left, start_y + 258, form_left + form_width, start_y + 308, 12))
            canvas.coords(login_text, form_center, start_y + 283)
            canvas.coords(register_text, form_center, start_y + 337)
            canvas.coords(status, form_center, min(start_y + 370, bottom - 24))

        def update_status(*_):
            try:
                canvas.itemconfigure(status, text=self.status_var.get())
            except tk.TclError:
                pass

        self.status_var.trace_add("write", update_status)
        update_status()
        canvas.bind("<Configure>", layout)
        canvas.tag_bind("login", "<Button-1>", lambda _: self.login())
        canvas.tag_bind("login", "<Enter>", lambda _: canvas.itemconfigure(login_button, fill="#123c39"))
        canvas.tag_bind("login", "<Leave>", lambda _: canvas.itemconfigure(login_button, fill="#061313"))
        canvas.tag_bind("register", "<Button-1>", lambda _: self.build_register())
        canvas.tag_bind("register", "<Enter>", lambda _: canvas.itemconfigure(register_text, fill="#ffffff"))
        canvas.tag_bind("register", "<Leave>", lambda _: canvas.itemconfigure(register_text, fill="#c5e7df"))
        self.password_entry.bind("<Return>", lambda _: self.login())
        self.username_entry.focus()

    def build_register(self):
        self.clear()
        self.root.configure(bg="#041313")
        asset_root = Path(__file__).resolve().parent
        source = Image.open(asset_root / "Background" / "bgforregistration").convert("RGBA")
        canvas = tk.Canvas(self.root, bg="#041313", bd=0, highlightthickness=0)
        canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        background = canvas.create_image(0, 0, anchor="nw")
        glass = canvas.create_image(0, 0, anchor="nw")

        card_width, card_height, radius = 380, 410, 26
        title = canvas.create_text(0, 0, text="Create account", font=("Segoe UI", 20, "bold"), fill="#f1f8f5")
        labels = [
            canvas.create_text(0, 0, text=label, anchor="w", font=("Segoe UI", 10, "bold"), fill="#edf7f4")
            for label in ("Username", "Password", "Confirm password")
        ]
        lines = [canvas.create_line(0, 0, 1, 0, fill="#a6c5bd") for _ in labels]
        entries = []
        entry_windows = []
        for label in ("Username", "Password", "Confirm password"):
            entry = tk.Entry(canvas, font=("Segoe UI", 10), bd=0, relief="flat", highlightthickness=0,
                             bg="#061f1d", fg="#f2fbf8", insertbackground="#f2fbf8",
                             show="●" if "password" in label.lower() else "")
            entries.append(entry)
            entry_windows.append(canvas.create_window(0, 0, anchor="w", window=entry, height=27))
        self.reg_username, self.reg_password, self.reg_confirm = entries
        create_button = self.rounded_rectangle(canvas, 0, 0, 1, 1, 12, fill="#061313", outline="#376f69", width=1, tags="create-account")
        create_text = canvas.create_text(0, 0, text="Create account", font=("Segoe UI", 10, "bold"), fill="#f3fbf8", tags="create-account")
        back_button = self.rounded_rectangle(canvas, 0, 0, 1, 1, 12, fill="#0b2d2a", outline="#668e87", width=1, tags="register-back")
        back_text = canvas.create_text(0, 0, text="Back", font=("Segoe UI", 10, "bold"), fill="#f3fbf8", tags="register-back")

        def layout(event):
            width, height = event.width, event.height
            if width < 2 or height < 2:
                return
            scale = max(width / source.width, height / source.height)
            image_size = (max(1, round(source.width * scale)), max(1, round(source.height * scale)))
            self.registration_background_image = ImageTk.PhotoImage(source.resize(image_size, Image.Resampling.LANCZOS))
            canvas.itemconfigure(background, image=self.registration_background_image)
            canvas.coords(background, (width - image_size[0]) // 2, (height - image_size[1]) // 2)

            left, top = (width - card_width) // 2, (height - card_height) // 2
            display = source.resize(image_size, Image.Resampling.LANCZOS)
            panel_box = (left - (width - image_size[0]) // 2, top - (height - image_size[1]) // 2,
                         left - (width - image_size[0]) // 2 + card_width,
                         top - (height - image_size[1]) // 2 + card_height)
            frosted = display.crop(panel_box).filter(ImageFilter.GaussianBlur(radius=15))
            frosted = Image.alpha_composite(frosted, Image.new("RGBA", frosted.size, (3, 22, 20, 178)))
            mask = Image.new("L", frosted.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, card_width - 1, card_height - 1), radius=radius, fill=255)
            frosted.putalpha(mask)
            ImageDraw.Draw(frosted).rounded_rectangle((0, 0, card_width - 1, card_height - 1), radius=radius,
                                                       outline=(177, 219, 208, 145), width=1)
            self.registration_glass_image = ImageTk.PhotoImage(frosted)
            canvas.itemconfigure(glass, image=self.registration_glass_image)
            canvas.coords(glass, left, top)

            inner_left, inner_right = left + 34, left + card_width - 34
            canvas.coords(title, left + card_width // 2, top + 52)
            for index, (label, line, window) in enumerate(zip(labels, lines, entry_windows)):
                y = top + 105 + index * 76
                canvas.coords(label, inner_left, y)
                canvas.coords(window, inner_left, y + 20)
                canvas.itemconfigure(window, width=inner_right - inner_left)
                canvas.coords(line, inner_left, y + 49, inner_right, y + 49)
            button_top = top + 346
            middle = left + card_width // 2
            canvas.coords(create_button, *self.rounded_rectangle_points(inner_left, button_top, middle - 5, button_top + 42, 12))
            canvas.coords(create_text, (inner_left + middle - 5) // 2, button_top + 21)
            canvas.coords(back_button, *self.rounded_rectangle_points(middle + 5, button_top, inner_right, button_top + 42, 12))
            canvas.coords(back_text, (middle + 5 + inner_right) // 2, button_top + 21)

        canvas.bind("<Configure>", layout)
        canvas.tag_bind("create-account", "<Button-1>", lambda _: self.register())
        canvas.tag_bind("register-back", "<Button-1>", lambda _: self.build_login())
        canvas.tag_bind("create-account", "<Enter>", lambda _: canvas.itemconfigure(create_button, fill="#123c39"))
        canvas.tag_bind("create-account", "<Leave>", lambda _: canvas.itemconfigure(create_button, fill="#061313"))
        self.reg_username.focus()

    def login(self):
        self.send({"type": "login", "username": self.username_entry.get().strip(), "password": self.password_entry.get()})

    def register(self):
        if self.reg_password.get() != self.reg_confirm.get():
            messagebox.showerror("Registration", "Passwords do not match.")
            return
        self.send({"type": "register", "username": self.reg_username.get().strip(), "password": self.reg_password.get()})

    def build_chat(self, rooms):
        self.clear()
        self.status_var = tk.StringVar(value="Connected")
        self.root.configure(bg="#07191d")
        self.icon_images = self.load_icons()
        shell = tk.Frame(self.root, bg="#07191d")
        shell.pack(fill="both", expand=True)

        navigation = tk.Frame(shell, bg="#0a2026", width=84)
        navigation.pack(side="left", fill="y")
        navigation.pack_propagate(False)
        tk.Label(navigation, image=self.icon_images.get("logo"), bg="#0a2026").pack(pady=(20, 30))
        self.nav_button(navigation, "home", "Home", self.show_home).pack(pady=4)
        self.nav_button(navigation, "chat", "Chats", self.show_chat).pack(pady=4)
        self.nav_button(navigation, "notification", "Alerts", self.show_notifications).pack(pady=4)
        self.nav_button(navigation, "settings", "Settings", self.show_settings).pack(pady=4)
        tk.Button(navigation, text="⏻", command=self.close, font=("Segoe UI", 18), bd=0,
                  fg="#dce9e8", bg="#0a2026", activebackground="#163942", cursor="hand2").pack(side="bottom", pady=22)

        workspace = tk.Frame(shell, bg="#07191d", padx=18, pady=16)
        workspace.pack(side="left", fill="both", expand=True)
        asset_root = Path(__file__).resolve().parent
        header = tk.Canvas(workspace, height=58, bg="#0b2427", bd=0, highlightthickness=0)
        header.pack(fill="x", pady=(0, 12))
        header_border = self.rounded_rectangle(header, 1, 1, 1, 57, 15, fill="", outline="#78a69f", width=1)
        header.create_image(38, 30, image=self.icon_images.get("logo"), anchor="center")
        header.create_text(74, 30, text="Nexora", anchor="w", font=("Segoe UI", 19, "bold"), fill="#edf8f6")
        profile_card = self.rounded_rectangle(header, 1, 8, 1, 50, 19, fill="#0b2528", outline="#60847f", width=1)
        username = header.create_text(0, 30, text=self.username, anchor="e", font=("Segoe UI", 10, "bold"), fill="#edf8f6")
        profile = header.create_image(0, 30, image=self.icon_images.get("user"), anchor="center")
        online_dot = header.create_oval(0, 0, 0, 0, fill="#1bd69a", outline="")

        def position_header(event):
            header.coords(header_border, *self.rounded_rectangle_points(1, 1, event.width - 1, event.height - 1, 15))
            card_left = max(event.width - 218, 220)
            header.coords(profile_card, *self.rounded_rectangle_points(card_left, 8, event.width - 14, 50, 19))
            header.coords(profile, card_left + 27, 29)
            header.coords(username, event.width - 42, 30)
            header.coords(online_dot, event.width - 31, 20, event.width - 21, 30)

        header.bind("<Configure>", position_header)

        main = tk.Frame(workspace, bg="#07191d")
        main.pack(fill="both", expand=True)
        sidebar = tk.Frame(main, bg="#15393d", width=235, padx=16, pady=18, highlightbackground="#71918c", highlightthickness=1)
        sidebar.pack(side="left", fill="y", padx=(0, 14))
        sidebar.pack_propagate(False)
        conversation_header = tk.Canvas(sidebar, height=28, bg="#15393d", bd=0, highlightthickness=0)
        conversation_header.pack(fill="x")
        conversation_header.create_text(2, 14, text="CONVERSATIONS", anchor="w", font=("Segoe UI", 9, "bold"), fill="#d0f4ea")
        style = ttk.Style()
        # The Windows native Treeview ignores fieldbackground in some themes,
        # leaving an unwanted white empty area below the room rows.
        style.theme_use("clam")
        style.configure("Glass.Treeview", background="#15393d", fieldbackground="#15393d", foreground="#edf8f6",
                        borderwidth=0, rowheight=50, font=("Segoe UI", 11))
        style.map("Glass.Treeview", background=[("selected", "#1f5e5a")],
                  foreground=[("selected", "#ffffff")])
        self.room_list = ttk.Treeview(sidebar, show="tree", style="Glass.Treeview", selectmode="browse")
        self.room_list.bind("<<TreeviewSelect>>", lambda _: self.join_selected())
        self.room_list.bind("<Button-3>", self.show_room_menu)
        self.room_menu = tk.Menu(self.root, tearoff=0)
        # Pack this first on the bottom so an expanding room list can never
        # consume the control's space when the window is resized.
        self.create_room_button = tk.Button(
            sidebar, text="＋   Create room", command=self.create_room,
            font=("Segoe UI", 10, "bold"), bd=0, padx=10, pady=10,
            fg="white", bg="#236b66", activebackground="#19534f", cursor="hand2",
        )
        self.create_room_button.pack(side="bottom", fill="x")
        self.room_list.pack(fill="both", expand=True, pady=(10, 8))

        # One image is painted once on this canvas. Every chat surface is a
        # translucent drawing over it, so there is no panel-local background.
        self.background_image = tk.PhotoImage(file=str(asset_root / "Background" / "Bg.png"))
        self.content_area = tk.Canvas(main, bg="#07191d", bd=0, highlightthickness=0)
        self.content_area.pack(side="left", fill="both", expand=True)
        self.chat_panel = self.content_area
        # Keep the pre-existing destinations as sibling views of the chat
        # canvas, so the sidebar can switch among them without obscuring it.
        self.home_panel = tk.Frame(main, bg="#1f5350", padx=30, pady=30)
        self.notifications_panel = tk.Frame(main, bg="#1f5350", padx=24, pady=22)
        self.settings_panel = tk.Frame(main, bg="#1f5350", padx=24, pady=22)
        content = self.chat_panel
        self.chat_background = content.create_image(0, 0, image=self.background_image, anchor="center", tags="backdrop")
        # The panel is an RGBA image generated at runtime: it is a smooth,
        # flat alpha layer, not a textured/stippled canvas polygon.
        self.glass_panel = None
        self.glass_image = None
        self.room_var = tk.StringVar(value=f"Current room: {self.current_room or 'None'}")
        room_shadow = content.create_text(2, 20, text=self.room_var.get(), anchor="w", font=("Segoe UI", 12, "bold"), fill="#031113", tags="glass")
        room_title = content.create_text(0, 18, text=self.room_var.get(), anchor="w", font=("Segoe UI", 12, "bold"), fill="#edf8f6", tags="glass")
        self.room_divider = content.create_line(24, 52, 1, 52, fill="#9ccdc3", width=1, tags="glass")
        self.room_var.trace_add(
            "write", lambda *_: (content.itemconfigure(room_shadow, text=self.room_var.get()),
                                   content.itemconfigure(room_title, text=self.room_var.get()))
        )
        self.message_records = []
        self.message_scroll_offset = 0
        self.message_content_height = 0
        self.message_font = tkfont.Font(family="Segoe UI", size=10)
        self.sender_font = tkfont.Font(family="Segoe UI", size=9, weight="bold")
        self.timestamp_font = tkfont.Font(family="Segoe UI", size=8)
        self.chat_box = content
        self.chat_scroll = ttk.Scrollbar(content, orient="vertical", command=self.scroll_messages)
        self.chat_scroll_window = content.create_window(0, 0, anchor="ne", window=self.chat_scroll, tags="glass")
        self.chat_box.bind("<MouseWheel>", self.on_message_wheel)
        self.input_shape = self.rounded_rectangle(content, 0, 0, 1, 1, 16, fill="#124a45", outline="#a2d5ca", width=1,
                                                  tags="glass")
        self.message_entry = tk.Entry(content, font=("Segoe UI", 10), relief="flat", bd=0, bg="#123b38", fg="#edf8f6", insertbackground="#edf8f6")
        self.input_window = content.create_window(0, 0, anchor="w", window=self.message_entry, height=28, tags="glass")
        self.message_entry.bind("<Return>", lambda _: self.send_chat())
        self.send_shape = self.rounded_rectangle(content, 0, 0, 1, 1, 15, fill="#1b766a", outline="#a0ddd2", width=1,
                                                 tags=("glass", "send"))
        self.send_text = content.create_text(0, 0, text="Send", font=("Segoe UI", 10, "bold"), fill="white", tags=("glass", "send"))
        content.tag_bind("send", "<Button-1>", lambda _: self.send_chat())
        content.tag_bind("send", "<Enter>", lambda _: content.itemconfigure(self.send_shape, fill="#259183"))
        content.tag_bind("send", "<Leave>", lambda _: content.itemconfigure(self.send_shape, fill="#1b766a"))
        self.room_title_items = (room_shadow, room_title)
        content.bind("<Configure>", self.layout_chat_canvas)
        status = tk.Label(workspace, textvariable=self.status_var, anchor="w", font=("Segoe UI", 10), fg="#e0fff7", bg="#102c30", padx=16, pady=7,
                          highlightbackground="#71918c", highlightthickness=1)
        status.pack(fill="x", pady=(10, 0))
        self.update_rooms(rooms)
        self.build_secondary_panels()
        self.show_chat()

    def load_icons(self):
        icons = {}
        for name in ("home", "chat", "notification", "settings", "user", "lock", "unlocked"):
            try:
                icon_path = Path(__file__).resolve().parent / "Icons" / f"{name}.png"
                icons[name] = tk.PhotoImage(file=str(icon_path)).subsample(16, 16)
            except tk.TclError:
                continue
        try:
            logo_path = Path(__file__).resolve().parent / "Icons" / "Logo.png"
            icons["logo"] = tk.PhotoImage(file=str(logo_path)).subsample(40, 40)
        except tk.TclError:
            pass
        return icons

    def layout_chat_canvas(self, event):
        """Keep the chat UI as one glass layer over the single canvas backdrop."""
        canvas = self.chat_panel
        width, height = event.width, event.height
        if width < 2 or height < 2:
            return
        canvas.coords(self.chat_background, width // 2, height // 2)
        # Tk Canvas cannot blur the pixels behind an item.  A smooth RGBA
        # teal wash is therefore used as the native, non-duplicated
        # backdrop-style treatment; it softens contrast without putting a
        # second background image inside the chat panel.
        panel_width, panel_height = max(width - 18, 1), max(height - 16, 1)
        self.glass_image = self.make_glass_image(panel_width, panel_height, radius=24)
        if self.glass_panel is not None:
            canvas.delete(self.glass_panel)
        self.glass_panel = canvas.create_image(8, 8, image=self.glass_image, anchor="nw", tags="glass-layer")
        canvas.tag_raise(self.glass_panel, self.chat_background)
        shadow, title = self.room_title_items
        canvas.coords(shadow, 27, 35)
        canvas.coords(title, 25, 33)
        canvas.coords(self.room_divider, 24, 52, width - 28, 52)
        input_top = height - 60
        send_left = width - 96
        canvas.coords(self.input_shape, *self.rounded_rectangle_points(24, input_top, send_left - 10, height - 20, 16))
        canvas.coords(self.input_window, 39, input_top + 20)
        canvas.itemconfigure(self.input_window, width=max(send_left - 64, 1))
        canvas.coords(self.send_shape, *self.rounded_rectangle_points(send_left, input_top, width - 24, height - 20, 15))
        canvas.coords(self.send_text, (send_left + width - 24) // 2, input_top + 20)
        canvas.coords(self.chat_scroll_window, width - 15, 66)
        canvas.itemconfigure(self.chat_scroll_window, height=max(input_top - 74, 1))
        self.refresh_message_bubbles()

    @staticmethod
    def make_glass_image(width, height, radius=24):
        """Build a clean rounded RGBA teal panel without patterns or noise."""
        radius = min(radius, width // 2, height // 2)
        rows = []
        for y in range(height):
            row = bytearray()
            for x in range(width):
                dx = max(radius - x, x - (width - radius - 1), 0)
                dy = max(radius - y, y - (height - radius - 1), 0)
                if dx and dy and dx * dx + dy * dy > radius * radius:
                    row.extend((0, 0, 0, 0))
                else:
                    # 23% emerald tint; only the one global canvas image is
                    # visible beneath it.
                    edge = x in (0, width - 1) or y in (0, height - 1)
                    row.extend((7, 52, 48, 58 if not edge else 150))
            rows.append(b"\x00" + bytes(row))
        raw = b"".join(rows)

        def chunk(kind, data):
            return (struct.pack(">I", len(data)) + kind + data +
                    struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))

        png = (b"\x89PNG\r\n\x1a\n" +
               chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)) +
               chunk(b"IDAT", zlib.compress(raw, 9)) +
               chunk(b"IEND", b""))
        return tk.PhotoImage(data=base64.b64encode(png))

    @staticmethod
    def rounded_rectangle_points(x1, y1, x2, y2, radius):
        """Return a smooth polygon used for the lightweight input shell."""
        return (
            x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
            x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
            x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1,
        )

    def rounded_rectangle(self, canvas, x1, y1, x2, y2, radius, **options):
        return canvas.create_polygon(
            *self.rounded_rectangle_points(x1, y1, x2, y2, radius), smooth=True, **options
        )

    def nav_button(self, parent, icon_name, label, command):
        return tk.Button(parent, text=label, image=self.icon_images.get(icon_name), compound="top", command=command,
                         font=("Segoe UI", 8, "bold"), bd=0, padx=4, pady=6, fg="#dce9e8", bg="#0a2026",
                         activebackground="#163942", activeforeground="white", cursor="hand2", justify="center")

    def build_secondary_panels(self):
        tk.Label(self.home_panel, text="Welcome back", font=("Segoe UI", 22, "bold"), fg="#edf8f6", bg="#1f5350").pack(anchor="w", pady=(10, 6))
        tk.Label(self.home_panel, text="Choose a conversation from the left to continue chatting, or create a new room.",
                 font=("Segoe UI", 11), fg="#d2eee8", bg="#1f5350", wraplength=500, justify="left").pack(anchor="w")
        self.home_room_label = tk.Label(self.home_panel, text="No room selected", font=("Segoe UI", 12, "bold"),
                                        fg="#c9f4e8", bg="#1d4a4b", highlightbackground="#8fbcb5", highlightthickness=1, padx=16, pady=14)
        self.home_room_label.pack(anchor="w", pady=(28, 0))
        tk.Label(self.notifications_panel, text="Notifications", font=("Segoe UI", 18, "bold"), fg="#edf8f6", bg="#1f5350").pack(anchor="w")
        self.notifications_box = tk.Listbox(self.notifications_panel, relief="flat", bd=0, bg="#1f5350", fg="#e2f7f2",
                                            font=("Segoe UI", 10), activestyle="none")
        self.notifications_box.pack(fill="both", expand=True, pady=(14, 0))
        tk.Label(self.settings_panel, text="Settings", font=("Segoe UI", 18, "bold"), fg="#edf8f6", bg="#1f5350").pack(anchor="w")
        tk.Checkbutton(self.settings_panel, text="Play in-app notification alerts for unfocused messages",
                       variable=self.notifications_enabled, font=("Segoe UI", 10), fg="#e2f7f2", bg="#1f5350",
                       activebackground="#1f5350", activeforeground="#ffffff", selectcolor="#34736c").pack(anchor="w", pady=(20, 8))
        tk.Label(self.settings_panel, text="Private-room passwords and account passwords are hashed on the server.\n"
                                      "Messages are stored locally and are not end-to-end encrypted.",
                 font=("Segoe UI", 10), fg="#d2eee8", bg="#1f5350", justify="left").pack(anchor="w", pady=(8, 0))

    def show_panel(self, panel):
        """Show one existing content view while keeping the sidebar in place."""
        for candidate in (getattr(self, "chat_panel", None),
                          getattr(self, "home_panel", None),
                          getattr(self, "notifications_panel", None),
                          getattr(self, "settings_panel", None)):
            if candidate is not None:
                candidate.pack_forget()
        panel.pack(side="left", fill="both", expand=True)

    def show_home(self):
        if hasattr(self, "home_panel"):
            self.home_room_label.configure(text=f"Current room: {self.current_room or 'None'}")
            self.show_panel(self.home_panel)

    def show_chat(self):
        if hasattr(self, "chat_panel"):
            self.show_panel(self.chat_panel)

    def show_notifications(self):
        if hasattr(self, "notifications_panel"):
            self.notifications_box.delete(0, "end")
            entries = self.notification_log or ["No new message notifications yet."]
            for entry in entries:
                self.notifications_box.insert("end", entry)
            self.show_panel(self.notifications_panel)

    def show_settings(self):
        if hasattr(self, "settings_panel"):
            self.show_panel(self.settings_panel)

    def update_rooms(self, rooms):
        if not hasattr(self, "room_list"):
            return
        selected = self.current_room
        self.private_rooms_supported = all(isinstance(room, dict) for room in rooms)
        self.room_items = [
            room if isinstance(room, dict) else {"name": str(room), "is_private": False, "owner_username": None}
            for room in rooms
        ]
        existing_items = self.room_list.get_children()
        if existing_items:
            self.room_list.delete(*existing_items)
        for index, room in enumerate(self.room_items):
            icon_name = "lock" if room["is_private"] else "unlocked"
            self.room_list.insert("", "end", iid=str(index), text=room["name"], image=self.icon_images.get(icon_name))
            if room["name"] == selected:
                self.room_list.selection_set(str(index))
        if not self.private_rooms_supported:
            self.status_var.set("Server restart required for private rooms")

    def show_room_menu(self, event):
        item = self.room_list.identify_row(event.y)
        if not item:
            return
        self.room_list.selection_set(item)
        room = self.room_items[int(item)]
        self.room_menu.delete(0, "end")
        if room.get("owner_username") == self.username:
            self.room_menu.add_command(label="Delete Room", command=lambda: self.confirm_delete_room(room))
            self.room_menu.tk_popup(event.x_root, event.y_root)
        self.room_menu.grab_release()

    def confirm_delete_room(self, room):
        dialog = tk.Toplevel(self.root)
        dialog.title("Delete Room")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.configure(bg="#123b38")
        tk.Label(dialog, text="Delete this room?", font=("Segoe UI", 13, "bold"),
                 bg="#123b38", fg="#f2fbf8").pack(anchor="w", padx=24, pady=(20, 6))
        tk.Label(dialog, text="This will permanently remove the room and its messages.",
                 font=("Segoe UI", 10), bg="#123b38", fg="#c8dfda", wraplength=360,
                 justify="left").pack(anchor="w", padx=24)
        actions = tk.Frame(dialog, bg="#123b38")
        actions.pack(fill="x", padx=24, pady=20)
        tk.Button(actions, text="Cancel", command=dialog.destroy, bd=0, padx=14, pady=7,
                  bg="#285451", fg="#edf8f6", activebackground="#356864").pack(side="right")
        tk.Button(actions, text="Delete", command=lambda: (dialog.destroy(), self.send({"type": "delete_room", "name": room["name"]})),
                  bd=0, padx=14, pady=7, bg="#a84040", fg="white", activebackground="#c04b4b").pack(side="right", padx=(0, 8))

    def handle_deleted_room(self, room):
        if self.current_room != room:
            return
        self.current_room = None
        self.room_var.set("Current room: None")
        self.clear_chat()
        self.status_var.set("This room was deleted.")
        remaining_public = [entry for entry in self.room_items
                            if entry["name"] != room and not entry.get("is_private")]
        if remaining_public:
            self.send({"type": "join_room", "name": remaining_public[0]["name"]})
        else:
            self.show_home()

    def join_selected(self):
        choice = self.room_list.selection()
        if choice:
            room = self.room_items[int(choice[0])]
            if room["is_private"]:
                password = simpledialog.askstring(
                    f"🔒 {room['name']}", "Enter room password:", parent=self.root, show="●"
                )
                if password is None:
                    return
                self.send({"type": "join_room", "name": room["name"], "password": password})
            else:
                self.send({"type": "join_room", "name": room["name"]})

    def create_room(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Create Room")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Create room", font=("Segoe UI", 13, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        ttk.Label(frame, text="Room name").grid(row=1, column=0, sticky="w")
        name_entry = ttk.Entry(frame, width=30)
        name_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(2, 10))
        privacy = tk.StringVar(value="public")
        ttk.Label(frame, text="Privacy").grid(row=3, column=0, sticky="w")
        ttk.Radiobutton(frame, text="🔓 Public room", variable=privacy, value="public").grid(row=4, column=0, columnspan=2, sticky="w")
        ttk.Radiobutton(frame, text="🔒 Private / password protected", variable=privacy, value="private").grid(row=5, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, text="Room password").grid(row=6, column=0, sticky="w", pady=(10, 0))
        password_entry = ttk.Entry(frame, width=30, show="●", state="disabled")
        password_entry.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(2, 12))

        def update_password_state(*_):
            password_entry.configure(state="normal" if privacy.get() == "private" else "disabled")
            if privacy.get() == "public":
                password_entry.delete(0, "end")

        def submit():
            name = name_entry.get().strip()
            is_private = privacy.get() == "private"
            password = password_entry.get()
            if is_private and not password:
                messagebox.showerror("Create room", "A private room password is required.", parent=dialog)
                return
            if is_private and not self.private_rooms_supported:
                messagebox.showerror(
                    "Server restart required",
                    "This connected server is running an older version and cannot create secure private rooms. "
                    "Stop it with Ctrl+C, then start it again with: python server.py",
                    parent=dialog,
                )
                return
            if self.send({"type": "create_room", "name": name, "is_private": is_private, "password": password}):
                dialog.destroy()

        privacy.trace_add("write", update_password_state)
        ttk.Button(frame, text="Create", command=submit).grid(row=8, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(frame, text="Cancel", command=dialog.destroy).grid(row=8, column=1, sticky="ew", padx=(5, 0))
        name_entry.focus()

    def send_chat(self):
        text = self.message_entry.get()
        if self.current_room and self.send({"type": "chat", "message": text}):
            self.message_entry.delete(0, "end")

    def add_line(self, line):
        """Render the existing timestamp/user/message line as a chat bubble."""
        timestamp, sender, message = "", "System", line
        if line.startswith("[") and "] " in line:
            timestamp, _, remainder = line[1:].partition("] ")
            if ": " in remainder:
                sender, message = remainder.split(": ", 1)
            else:
                message = remainder
        self.message_records.append((timestamp, sender, message))
        self.scroll_to_bottom()

    def clear_chat(self):
        self.message_records = []
        self.message_scroll_offset = 0
        self.refresh_message_bubbles()

    def refresh_message_bubbles(self, _event=None):
        """Paint only the visible portion of the independently scrolling history."""
        if not hasattr(self, "chat_box"):
            return
        canvas = self.chat_box
        width = max(canvas.winfo_width(), 320)
        height = max(canvas.winfo_height(), 180)
        canvas.delete("message")
        area_top, area_bottom = 60, max(height - 72, 90)
        viewport_height = max(area_bottom - area_top, 1)
        content_y = 0
        # Reserve the far-right scrollbar column plus a small gutter.  All
        # outgoing bubbles and their timestamps use this same safe edge.
        scrollbar_safe_margin = 42
        message_right_edge = max(width - scrollbar_safe_margin, 180)
        maximum = max(180, min(360, int((message_right_edge - 18) * .52)))
        for timestamp, sender, message in self.message_records:
            outgoing = sender == self.username
            if sender == "System":
                y = area_top + content_y - self.message_scroll_offset
                if area_top - 20 <= y <= area_bottom + 20:
                    canvas.create_text(width // 2, y + 7, text=message, fill="#c7e2dc", font=self.timestamp_font,
                                       tags="message")
                content_y += 30
                continue
            probe = canvas.create_text(0, 0, text=message, width=maximum - 30, anchor="nw",
                                       font=self.message_font, tags="message")
            bounds = canvas.bbox(probe)
            canvas.delete(probe)
            message_height = max((bounds[3] - bounds[1]) if bounds else 18, 18)
            bubble_width = max(150, min(maximum, self.message_font.measure(message) + 34))
            if message_height > 20:
                bubble_width = maximum
            bubble_height = message_height + 38
            y = area_top + content_y - self.message_scroll_offset
            x = message_right_edge - bubble_width if outgoing else 18
            fill = "#18564f" if outgoing else "#17373a"
            outline = "#24a995" if outgoing else "#6d9690"
            if y + bubble_height + 18 >= area_top and y <= area_bottom:
                canvas.create_polygon(*self.rounded_rectangle_points(x, y, x + bubble_width, y + bubble_height, 22),
                                      smooth=True, fill=fill, outline=outline, width=1, tags="message")
                canvas.create_text(x + 17, y + 11, text=sender, anchor="nw", fill="#20d6b5", font=self.sender_font,
                                   tags="message")
                canvas.create_text(x + 17, y + 29, text=message, width=bubble_width - 34, anchor="nw", fill="#f2fbf8",
                                   font=self.message_font, tags="message")
                time_x = x + bubble_width if outgoing else x
                canvas.create_text(time_x, y + bubble_height + 9, text=timestamp, anchor="ne" if outgoing else "nw",
                                   fill="#a1c1bc", font=self.timestamp_font, tags="message")
            content_y += bubble_height + 30
        self.message_content_height = content_y
        max_offset = max(content_y - viewport_height, 0)
        self.message_scroll_offset = min(self.message_scroll_offset, max_offset)
        if content_y <= viewport_height:
            self.chat_scroll.set(0, 1)
        else:
            first = self.message_scroll_offset / content_y
            self.chat_scroll.set(first, min(first + viewport_height / content_y, 1))

    def scroll_messages(self, action, value, _unused=None):
        canvas = self.chat_box
        viewport = max(canvas.winfo_height() - 132, 1)
        max_offset = max(self.message_content_height - viewport, 0)
        if action == "moveto":
            self.message_scroll_offset = float(value) * max_offset
        elif action == "scroll":
            self.message_scroll_offset += int(value) * 36
        self.message_scroll_offset = max(0, min(self.message_scroll_offset, max_offset))
        self.refresh_message_bubbles()

    def on_message_wheel(self, event):
        if event.delta:
            self.scroll_messages("scroll", -max(1, abs(event.delta) // 120) if event.delta > 0 else 1)
        return "break"

    def scroll_to_bottom(self):
        self.refresh_message_bubbles()
        viewport = max(self.chat_box.winfo_height() - 132, 1)
        self.message_scroll_offset = max(self.message_content_height - viewport, 0)
        self.refresh_message_bubbles()

    def notify(self, event):
        if event.get("username") == self.username:
            return
        self.notification_log.append(
            f"[{event['timestamp'][11:16]}] {event['username']} in {event.get('room', 'a room')}: {replace_shortcodes(event['message'])}"
        )
        self.notification_log = self.notification_log[-50:]
        if not self.notifications_enabled.get() or self.root.focus_displayof() is not None:
            return
        self.status_var.set(f"New message from {event['username']} in {event.get('room', '')}")
        try:
            self.root.bell()
        except tk.TclError:
            pass

    def process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event.get("type")
                if kind == "result":
                    if event.get("action") == "login" and event.get("ok"):
                        self.username = event["username"]
                        self.build_chat(event["rooms"])
                    elif event.get("action") == "register":
                        messagebox.showinfo("Registration", event["message"]) if event.get("ok") else messagebox.showerror("Registration", event["message"])
                        if event.get("ok"):
                            self.build_login()
                    elif not event.get("ok"):
                        messagebox.showerror("Chat", event.get("message", "Request failed."))
                elif kind == "error":
                    messagebox.showerror("Chat", event.get("message", "Server error."))
                elif kind == "rooms":
                    self.update_rooms(event["rooms"])
                elif kind == "room_deleted":
                    self.handle_deleted_room(event["room"])
                elif kind == "history":
                    self.show_chat()
                    self.current_room = event["room"]
                    self.room_var.set(f"Current room: {self.current_room}")
                    self.clear_chat()
                    for item in event["messages"]:
                        self.add_line(f"[{item['timestamp'][11:16]}] {item['username']}: {replace_shortcodes(item['message'])}")
                    self.message_entry.focus()
                elif kind == "chat" and event.get("room") == self.current_room:
                    self.add_line(f"[{event['timestamp'][11:16]}] {event['username']}: {replace_shortcodes(event['message'])}")
                    self.notify(event)
                elif kind == "system" and self.current_room:
                    self.add_line(f"[{datetime.now():%H:%M}] System: {event['message']}")
                elif kind == "disconnected":
                    self.connected = False
                    if hasattr(self, "status_var"):
                        self.status_var.set("Disconnected from server")
        except queue.Empty:
            pass
        try:
            self.root.after(80, self.process_events)
        except tk.TclError:
            pass

    def close(self):
        if self.connected:
            self.send({"type": "logout"})
            self.connected = False
        if self.socket:
            try: self.socket.close()
            except OSError: pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ChatClient().run()
