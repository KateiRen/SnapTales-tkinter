from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk


SCRIPT_FONTS = [
    "Pacifico",
    "Dancing Script",
    "Great Vibes",
]

DISPLAY_FONTS = [
    "Playfair Display",
    "Montserrat",
    "Raleway",
    "Bebas Neue",
]

FONT_FILE_CANDIDATES = {
    "Pacifico": ["Pacifico-Regular.ttf", "pacifico.ttf", "segoesc.ttf", "BRUSHSCI.TTF"],
    "Dancing Script": ["DancingScript-Regular.ttf", "dancingscript.ttf", "GABRIOLA.TTF", "segoesc.ttf"],
    "Great Vibes": ["GreatVibes-Regular.ttf", "greatvibes.ttf", "segoesc.ttf", "BRUSHSCI.TTF"],
    "Playfair Display": ["PlayfairDisplay-Regular.ttf", "playfairdisplay.ttf", "georgia.ttf", "times.ttf"],
    "Montserrat": ["Montserrat-Regular.ttf", "montserrat.ttf", "arial.ttf", "calibri.ttf"],
    "Raleway": ["Raleway-Regular.ttf", "raleway.ttf", "calibri.ttf", "verdana.ttf"],
    "Bebas Neue": ["BebasNeue-Regular.ttf", "bebasneue.ttf", "impact.ttf", "arialbd.ttf"],
}

PRESET_COLORS = [
    "#111111",
    "#ffffff",
    "#d62828",
    "#f77f00",
    "#fcbf49",
    "#1d3557",
    "#2a9d8f",
]

EXPORT_FILE_SUFFIXES = {
    "as_is": "",
    "paper_10x15_original": "10x15",
    "paper_10x15_max": "10x15max",
    "paper_13x18_original": "13x18",
    "paper_13x18_max": "13x18max",
}


def mm_to_px(mm: float, dpi: int = 300) -> int:
    return int(round(mm / 25.4 * dpi))


def create_border_texture(width: int, height: int) -> Image.Image:
    base = Image.new("RGB", (width, height), "#f7f4ee")
    noise = Image.effect_noise((width, height), 10).convert("L")
    grain = ImageOps.colorize(noise, black="#ebe7df", white="#fffdf8")
    return Image.blend(base, grain, 0.22)


def create_app_icon(size: int = 128) -> Image.Image:
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(icon)

    card_w = int(size * 0.72)
    card_h = int(size * 0.80)
    x0 = (size - card_w) // 2
    y0 = (size - card_h) // 2
    x1 = x0 + card_w
    y1 = y0 + card_h

    side = max(2, int(card_w * (4.5 / 88.0)))
    top = max(2, int(card_h * (4.5 / 107.0)))
    bottom = max(5, int(card_h * (23.5 / 107.0)))
    photo_w = card_w - side * 2
    photo_h = card_h - top - bottom

    draw.rounded_rectangle((x0, y0, x1, y1), radius=max(4, size // 14), fill=(247, 244, 238, 255))
    draw.rounded_rectangle(
        (x0 + side, y0 + top, x0 + side + photo_w, y0 + top + photo_h),
        radius=max(2, size // 22),
        fill=(92, 146, 166, 255),
    )
    draw.polygon(
        [
            (x0 + side + int(photo_w * 0.15), y0 + top + int(photo_h * 0.78)),
            (x0 + side + int(photo_w * 0.42), y0 + top + int(photo_h * 0.46)),
            (x0 + side + int(photo_w * 0.62), y0 + top + int(photo_h * 0.68)),
            (x0 + side + int(photo_w * 0.86), y0 + top + int(photo_h * 0.42)),
            (x0 + side + int(photo_w * 0.86), y0 + top + int(photo_h * 0.96)),
            (x0 + side + int(photo_w * 0.15), y0 + top + int(photo_h * 0.96)),
        ],
        fill=(52, 94, 117, 255),
    )
    draw.ellipse(
        (
            x0 + side + int(photo_w * 0.62),
            y0 + top + int(photo_h * 0.12),
            x0 + side + int(photo_w * 0.80),
            y0 + top + int(photo_h * 0.30),
        ),
        fill=(255, 239, 178, 255),
    )

    return icon


def place_on_photo_paper(
    polaroid: Image.Image,
    paper_width_mm: int,
    paper_height_mm: int,
    maximize: bool,
    dpi: int = 300,
) -> Image.Image:
    paper_w = mm_to_px(paper_width_mm, dpi)
    paper_h = mm_to_px(paper_height_mm, dpi)
    result = Image.new("RGB", (paper_w, paper_h), "white")

    if maximize:
        scale = min(paper_w / polaroid.width, paper_h / polaroid.height)
        target_w = int(polaroid.width * scale)
        target_h = int(polaroid.height * scale)
    else:
        target_w = mm_to_px(88, dpi)
        target_h = mm_to_px(107, dpi)
        fit_scale = min(1.0, paper_w / target_w, paper_h / target_h)
        target_w = int(target_w * fit_scale)
        target_h = int(target_h * fit_scale)

    resized = polaroid.resize((target_w, target_h), Image.Resampling.LANCZOS)
    pos_x = (paper_w - target_w) // 2
    pos_y = (paper_h - target_h) // 2
    result.paste(resized, (pos_x, pos_y))
    return result


@dataclass
class PolaroidMetrics:
    side_border: int
    top_border: int
    bottom_border: int
    photo_size: int


class SnapTalesApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SnapTales")
        self.root.geometry("1400x920")

        self.image_path: Path | None = None
        self.original_image: Image.Image | None = None
        self.cropped_square: Image.Image | None = None
        self.polaroid_image: Image.Image | None = None
        self.export_variants: dict[str, Image.Image] = {}

        self.crop_rect: tuple[float, float, float] | None = None
        self.drag_mode: str | None = None
        self.drag_offset = (0.0, 0.0)
        self.drag_start = (0.0, 0.0)
        self.pending_result_update_id: str | None = None

        self.crop_scale = 1.0
        self.crop_offset = (0.0, 0.0)
        self.crop_canvas_size = (1, 1)

        self.crop_tk_image: ImageTk.PhotoImage | None = None
        self.result_tk_image: ImageTk.PhotoImage | None = None
        self.export_preview_tk: ImageTk.PhotoImage | None = None
        self.app_icon_tk: ImageTk.PhotoImage | None = None
        self.thumbnail_tk_images: dict[str, ImageTk.PhotoImage] = {}
        self.export_selection_vars: dict[str, tk.BooleanVar] = {}

        self.crop_canvas: tk.Canvas | None = None
        self.result_canvas: tk.Canvas | None = None
        self.export_preview_canvas: tk.Canvas | None = None
        self.mode_labels: dict[str, str] = {}

        self.font_var = tk.StringVar(value=SCRIPT_FONTS[0])
        self.text_var = tk.StringVar(value="Your funny SnapTale here")
        self.color_mode_var = tk.StringVar(value="preset")
        self.preset_color_var = tk.StringVar(value=PRESET_COLORS[0])
        self.custom_color = "#111111"
        self.h_align_var = tk.StringVar(value="center")
        self.v_align_var = tk.StringVar(value="center")
        self.export_mode_var = tk.StringVar(value="as_is")

        self.status_var = tk.StringVar(value="Open a photo to begin.")

        self.configure_windows_app_id()
        self.apply_app_icon()

        self.default_save_dir = self.prepare_default_save_folder()

        self.build_ui()

    def configure_windows_app_id(self) -> None:
        if sys.platform != "win32":
            return
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KateiRen.SnapTales")
        except Exception:
            pass

    def apply_app_icon(self) -> None:
        icon_image = create_app_icon(128)
        self.app_icon_tk = ImageTk.PhotoImage(icon_image)
        self.root.iconphoto(True, self.app_icon_tk)

    def prepare_default_save_folder(self) -> Path:
        pictures = Path.home() / "Pictures"
        if not pictures.exists():
            return Path.home()
        target = pictures / "SnapTales"
        if target.exists():
            return target

        should_create = messagebox.askyesno(
            "Create Save Folder",
            "SnapTales can save into Pictures/SnapTales. Create the folder now?",
        )
        if should_create:
            target.mkdir(parents=True, exist_ok=True)
            return target
        return pictures

    def build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(self.root)
        notebook.grid(row=0, column=0, sticky="nsew")

        editor_tab = ttk.Frame(notebook, padding=12)
        save_tab = ttk.Frame(notebook, padding=12)
        notebook.add(editor_tab, text="Step 1: Create")
        notebook.add(save_tab, text="Step 2: Save")

        self.build_editor_tab(editor_tab)
        self.build_save_tab(save_tab)

        status = ttk.Label(self.root, textvariable=self.status_var, anchor="w")
        status.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))

    def build_editor_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=0)
        parent.columnconfigure(1, weight=1)
        parent.columnconfigure(2, weight=1)
        parent.rowconfigure(0, weight=1)

        controls = ttk.LabelFrame(parent, text="Controls", padding=10)
        controls.grid(row=0, column=0, sticky="ns", padx=(0, 12))

        ttk.Button(controls, text="Open Photo", command=self.open_photo).grid(
            row=0, column=0, sticky="ew", pady=(0, 10)
        )
        ttk.Label(controls, text="Add your caption").grid(row=1, column=0, sticky="w")
        text_entry = ttk.Entry(controls, textvariable=self.text_var, width=26)
        text_entry.grid(row=2, column=0, sticky="ew", pady=(4, 10))
        text_entry.bind("<KeyRelease>", lambda _event: self.update_result())

        ttk.Label(controls, text="Choose your style").grid(
            row=3, column=0, sticky="w"
        )
        font_values = SCRIPT_FONTS + DISPLAY_FONTS
        font_combo = ttk.Combobox(
            controls,
            textvariable=self.font_var,
            values=font_values,
            state="readonly",
            width=24,
        )
        font_combo.grid(row=4, column=0, sticky="ew", pady=(4, 10))
        font_combo.bind("<<ComboboxSelected>>", lambda _event: self.update_result())

        ttk.Label(controls, text="Colors").grid(row=5, column=0, sticky="w")
        colors_row = ttk.Frame(controls)
        colors_row.grid(row=6, column=0, sticky="w", pady=(4, 8))
        for color in PRESET_COLORS:
            btn = tk.Radiobutton(
                colors_row,
                bg=color,
                width=2,
                indicatoron=False,
                selectcolor=color,
                variable=self.preset_color_var,
                value=color,
                command=self.on_preset_color_changed,
            )
            btn.pack(side="left", padx=2)

        custom_row = ttk.Frame(controls)
        custom_row.grid(row=7, column=0, sticky="ew")
        ttk.Button(custom_row, text="Custom Color", command=self.pick_custom_color).pack(
            side="left"
        )

        ttk.Label(controls, text="Horizontal alignment").grid(
            row=8, column=0, sticky="w", pady=(12, 0)
        )
        h_row = ttk.Frame(controls)
        h_row.grid(row=9, column=0, sticky="w", pady=(4, 4))
        for value, label in [("left", "Left"), ("center", "Center"), ("right", "Right")]:
            ttk.Radiobutton(
                h_row,
                text=label,
                variable=self.h_align_var,
                value=value,
                command=self.update_result,
            ).pack(side="left", padx=(0, 8))

        ttk.Label(controls, text="Vertical alignment").grid(
            row=10, column=0, sticky="w", pady=(8, 0)
        )
        v_row = ttk.Frame(controls)
        v_row.grid(row=11, column=0, sticky="w", pady=(4, 0))
        for value, label in [("top", "Top"), ("center", "Center"), ("bottom", "Bottom")]:
            ttk.Radiobutton(
                v_row,
                text=label,
                variable=self.v_align_var,
                value=value,
                command=self.update_result,
            ).pack(side="left", padx=(0, 8))

        crop_frame = ttk.LabelFrame(parent, text="Crop (drag to move, corner to resize)")
        crop_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        crop_frame.columnconfigure(0, weight=1)
        crop_frame.rowconfigure(0, weight=1)

        self.crop_canvas = tk.Canvas(crop_frame, bg="#1a1a1a", highlightthickness=0)
        self.crop_canvas.grid(row=0, column=0, sticky="nsew")
        self.crop_canvas.bind("<Configure>", self.on_crop_canvas_resize)
        self.crop_canvas.bind("<ButtonPress-1>", self.on_crop_mouse_down)
        self.crop_canvas.bind("<B1-Motion>", self.on_crop_mouse_drag)
        self.crop_canvas.bind("<ButtonRelease-1>", self.on_crop_mouse_up)

        result_frame = ttk.LabelFrame(parent, text="Result")
        result_frame.grid(row=0, column=2, sticky="nsew")
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.result_canvas = tk.Canvas(result_frame, bg="#f2f2f2", highlightthickness=0)
        self.result_canvas.grid(row=0, column=0, sticky="nsew")
        self.result_canvas.bind("<Configure>", lambda _event: self.refresh_result_canvas())

    def build_save_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=0)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(1, weight=1)

        ttk.Label(
            parent,
            text="Choose the formats you wnat to save",
            font=("Segoe UI", 12, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        options = ttk.LabelFrame(parent, text="Output Formats", padding=8)
        options.grid(row=1, column=0, sticky="ns", padx=(0, 12))

        self.mode_labels = {
            "as_is": "As is",
            "paper_10x15_max": "10x15 cm - maximize",
            "paper_10x15_original": "10x15 cm - original size",
            "paper_13x18_max": "13x18 cm - maximize",
            "paper_13x18_original": "13x18 cm - original size",
        }

        row = 0
        for key, label in self.mode_labels.items():
            self.export_selection_vars[key] = tk.BooleanVar(value=(key == "as_is"))
            ttk.Checkbutton(
                options,
                text=label,
                variable=self.export_selection_vars[key],
                command=lambda mode=key: self.on_export_option_clicked(mode),
            ).grid(row=row, column=0, sticky="w", pady=2)
            thumb = ttk.Label(options)
            thumb.grid(row=row, column=1, padx=(8, 0), pady=2)
            thumb.bind("<Button-1>", lambda _event, mode=key: self.on_export_preview_clicked(mode))
            self.thumbnail_tk_images[key] = None
            setattr(self, f"thumb_{key}", thumb)
            row += 1

        ttk.Button(options, text="Save Selected", command=self.save_selected).grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=(12, 0)
        )

        preview = ttk.LabelFrame(parent, text="Selected Preview")
        preview.grid(row=1, column=1, sticky="nsew")
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(0, weight=1)
        self.export_preview_canvas = tk.Canvas(preview, bg="#f7f7f7", highlightthickness=0)
        self.export_preview_canvas.grid(row=0, column=0, sticky="nsew")
        self.export_preview_canvas.bind("<Configure>", lambda _event: self.refresh_export_preview())

    def on_export_option_clicked(self, mode: str) -> None:
        self.export_mode_var.set(mode)
        self.refresh_export_preview()

    def on_export_preview_clicked(self, mode: str) -> None:
        self.export_mode_var.set(mode)
        self.refresh_export_preview()

    def open_photo(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select Photo",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        self.image_path = Path(file_path)
        self.original_image = Image.open(file_path).convert("RGB")
        self.initialize_crop_rect()
        self.refresh_crop_canvas()
        self.update_result()
        self.status_var.set(f"Loaded: {self.image_path.name}")

    def initialize_crop_rect(self) -> None:
        if not self.original_image:
            return
        width, height = self.original_image.size
        size = min(width, height) * 0.8
        x = (width - size) / 2
        y = (height - size) / 2
        self.crop_rect = (x, y, size)

    def on_crop_canvas_resize(self, _event: tk.Event) -> None:
        self.refresh_crop_canvas()

    def refresh_crop_canvas(self) -> None:
        self.crop_canvas.delete("all")
        if not self.original_image:
            self.crop_canvas.create_text(
                self.crop_canvas.winfo_width() // 2,
                self.crop_canvas.winfo_height() // 2,
                text="Open a photo to start",
                fill="white",
                font=("Segoe UI", 14),
            )
            return

        canvas_w = max(1, self.crop_canvas.winfo_width())
        canvas_h = max(1, self.crop_canvas.winfo_height())
        img_w, img_h = self.original_image.size

        self.crop_scale = min(canvas_w / img_w, canvas_h / img_h)
        scaled_w = int(img_w * self.crop_scale)
        scaled_h = int(img_h * self.crop_scale)
        offset_x = (canvas_w - scaled_w) // 2
        offset_y = (canvas_h - scaled_h) // 2
        self.crop_offset = (offset_x, offset_y)
        self.crop_canvas_size = (canvas_w, canvas_h)

        preview = self.original_image.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)
        self.crop_tk_image = ImageTk.PhotoImage(preview)
        self.crop_canvas.create_image(offset_x, offset_y, anchor="nw", image=self.crop_tk_image)

        if not self.crop_rect:
            return

        x, y, size = self.crop_rect
        x1, y1 = self.image_to_canvas(x, y)
        x2, y2 = self.image_to_canvas(x + size, y + size)

        self.crop_canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline="#00e5ff",
            width=2,
        )

        self.crop_canvas.create_rectangle(
            x2 - 7,
            y2 - 7,
            x2 + 7,
            y2 + 7,
            fill="#00e5ff",
            outline="#00e5ff",
        )

    def image_to_canvas(self, x: float, y: float) -> tuple[float, float]:
        ox, oy = self.crop_offset
        return x * self.crop_scale + ox, y * self.crop_scale + oy

    def canvas_to_image(self, x: float, y: float) -> tuple[float, float]:
        ox, oy = self.crop_offset
        return (x - ox) / self.crop_scale, (y - oy) / self.crop_scale

    def on_crop_mouse_down(self, event: tk.Event) -> None:
        if not self.original_image or not self.crop_rect:
            return
        img_x, img_y = self.canvas_to_image(event.x, event.y)
        img_w, img_h = self.original_image.size
        if img_x < 0 or img_y < 0 or img_x > img_w or img_y > img_h:
            return

        x, y, size = self.crop_rect
        handle_radius = max(10 / self.crop_scale, 4)
        in_handle = abs(img_x - (x + size)) <= handle_radius and abs(img_y - (y + size)) <= handle_radius
        in_rect = x <= img_x <= x + size and y <= img_y <= y + size

        if in_handle:
            self.drag_mode = "resize"
        elif in_rect:
            self.drag_mode = "move"
            self.drag_offset = (img_x - x, img_y - y)
        else:
            self.drag_mode = "new"
            self.drag_start = (img_x, img_y)
            self.crop_rect = (img_x, img_y, 1)

    def on_crop_mouse_drag(self, event: tk.Event) -> None:
        if not self.original_image or not self.crop_rect or not self.drag_mode:
            return

        img_x, img_y = self.canvas_to_image(event.x, event.y)
        img_w, img_h = self.original_image.size
        x, y, size = self.crop_rect

        if self.drag_mode == "move":
            dx, dy = self.drag_offset
            new_x = min(max(0, img_x - dx), img_w - size)
            new_y = min(max(0, img_y - dy), img_h - size)
            self.crop_rect = (new_x, new_y, size)
        elif self.drag_mode == "resize":
            new_size = max(5, img_x - x, img_y - y)
            new_size = min(new_size, img_w - x, img_h - y)
            self.crop_rect = (x, y, new_size)
        elif self.drag_mode == "new":
            sx, sy = self.drag_start
            width = img_x - sx
            height = img_y - sy
            square = max(abs(width), abs(height), 5)
            new_x = sx if width >= 0 else sx - square
            new_y = sy if height >= 0 else sy - square
            new_x = min(max(0, new_x), img_w - square)
            new_y = min(max(0, new_y), img_h - square)
            square = min(square, img_w - new_x, img_h - new_y)
            self.crop_rect = (new_x, new_y, square)

        self.refresh_crop_canvas()
        self.schedule_result_update()

    def on_crop_mouse_up(self, _event: tk.Event) -> None:
        self.drag_mode = None
        self.schedule_result_update(immediate=True)

    def schedule_result_update(self, immediate: bool = False) -> None:
        if not self.original_image or not self.crop_rect:
            return

        if self.pending_result_update_id:
            self.root.after_cancel(self.pending_result_update_id)
            self.pending_result_update_id = None

        if immediate:
            self.update_result()
            return

        self.pending_result_update_id = self.root.after(60, self.run_scheduled_result_update)

    def run_scheduled_result_update(self) -> None:
        self.pending_result_update_id = None
        self.update_result()

    def update_result(self) -> None:
        if not self.original_image or not self.crop_rect:
            return

        x, y, size = self.crop_rect
        box = (int(x), int(y), int(x + size), int(y + size))
        self.cropped_square = self.original_image.crop(box)

        self.polaroid_image, metrics = self.build_polaroid(self.cropped_square)
        self.apply_text_to_polaroid(metrics)
        self.refresh_result_canvas()
        self.refresh_export_variants()
        self.refresh_export_preview()

    def build_polaroid(self, square_image: Image.Image) -> tuple[Image.Image, PolaroidMetrics]:
        photo_size = square_image.width
        side_border = max(1, round(photo_size * (4.5 / 79.0)))
        top_border = max(1, round(photo_size * (4.5 / 79.0)))
        bottom_border = max(1, round(photo_size * (23.5 / 79.0)))

        full_w = photo_size + side_border * 2
        full_h = photo_size + top_border + bottom_border

        base = create_border_texture(full_w, full_h)
        base.paste(square_image, (side_border, top_border))
        return base, PolaroidMetrics(side_border, top_border, bottom_border, photo_size)

    def apply_text_to_polaroid(self, metrics: PolaroidMetrics) -> None:
        if not self.polaroid_image:
            return

        text = self.text_var.get().strip()
        if not text:
            return

        draw = ImageDraw.Draw(self.polaroid_image)
        area_x = metrics.side_border
        area_y = metrics.top_border + metrics.photo_size
        area_w = self.polaroid_image.width - 2 * metrics.side_border
        area_h = metrics.bottom_border
        pad_x = max(8, int(area_w * 0.04))
        pad_y = max(4, int(area_h * 0.08))
        max_w = max(20, area_w - 2 * pad_x)
        max_h = max(12, area_h - 2 * pad_y)

        font = self.find_best_fit_font(draw, text, max_w, max_h)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if self.h_align_var.get() == "left":
            text_x = area_x + pad_x
        elif self.h_align_var.get() == "right":
            text_x = area_x + area_w - pad_x - text_w
        else:
            text_x = area_x + (area_w - text_w) // 2

        if self.v_align_var.get() == "top":
            text_y = area_y + pad_y
        elif self.v_align_var.get() == "bottom":
            text_y = area_y + area_h - pad_y - text_h
        else:
            text_y = area_y + (area_h - text_h) // 2

        draw.text((text_x, text_y), text, font=font, fill=self.get_active_color())

    def find_best_fit_font(self, draw: ImageDraw.ImageDraw, text: str, max_w: int, max_h: int) -> ImageFont.ImageFont:
        for size in range(max_h, 9, -1):
            font = self.load_font(self.font_var.get(), size)
            bbox = draw.textbbox((0, 0), text, font=font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            if width <= max_w and height <= max_h:
                return font
        return self.load_font(self.font_var.get(), 10)

    def load_font(self, font_name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        fonts_dir = Path(__file__).parent / "fonts"
        win_fonts = Path("C:/Windows/Fonts")

        candidates = FONT_FILE_CANDIDATES.get(font_name, []) + ["segoeui.ttf", "arial.ttf"]
        for file_name in candidates:
            local_path = fonts_dir / file_name
            if local_path.exists():
                return ImageFont.truetype(str(local_path), size=size)

            win_path = win_fonts / file_name
            if win_path.exists():
                return ImageFont.truetype(str(win_path), size=size)

        return ImageFont.load_default()

    def get_active_color(self) -> str:
        if self.color_mode_var.get() == "custom":
            return self.custom_color
        return self.preset_color_var.get()

    def on_preset_color_changed(self) -> None:
        self.color_mode_var.set("preset")
        self.update_result()

    def pick_custom_color(self) -> None:
        color = colorchooser.askcolor(title="Pick custom color", initialcolor=self.custom_color)
        if color and color[1]:
            self.custom_color = color[1]
            self.color_mode_var.set("custom")
            self.update_result()

    def refresh_result_canvas(self) -> None:
        self.result_canvas.delete("all")
        if not self.polaroid_image:
            self.result_canvas.create_text(
                self.result_canvas.winfo_width() // 2,
                self.result_canvas.winfo_height() // 2,
                text="Result appears here after Step 2-4",
                fill="#555555",
                font=("Segoe UI", 13),
            )
            return

        canvas_w = max(1, self.result_canvas.winfo_width())
        canvas_h = max(1, self.result_canvas.winfo_height())
        scale = min(canvas_w / self.polaroid_image.width, canvas_h / self.polaroid_image.height)
        target_w = int(self.polaroid_image.width * scale)
        target_h = int(self.polaroid_image.height * scale)
        preview = self.polaroid_image.resize((target_w, target_h), Image.Resampling.LANCZOS)

        self.result_tk_image = ImageTk.PhotoImage(preview)
        x = (canvas_w - target_w) // 2
        y = (canvas_h - target_h) // 2
        self.result_canvas.create_image(x, y, anchor="nw", image=self.result_tk_image)

    def refresh_export_variants(self) -> None:
        if not self.polaroid_image:
            self.export_variants = {}
            return

        self.export_variants = {
            "as_is": self.polaroid_image.copy(),
            "paper_10x15_max": place_on_photo_paper(self.polaroid_image, 100, 150, maximize=True),
            "paper_10x15_original": place_on_photo_paper(self.polaroid_image, 100, 150, maximize=False),
            "paper_13x18_max": place_on_photo_paper(self.polaroid_image, 130, 180, maximize=True),
            "paper_13x18_original": place_on_photo_paper(self.polaroid_image, 130, 180, maximize=False),
        }
        self.refresh_thumbnails()

    def refresh_thumbnails(self) -> None:
        for key, image in self.export_variants.items():
            thumb = image.copy()
            thumb.thumbnail((130, 130), Image.Resampling.LANCZOS)
            tk_thumb = ImageTk.PhotoImage(thumb)
            self.thumbnail_tk_images[key] = tk_thumb
            label: ttk.Label = getattr(self, f"thumb_{key}")
            label.configure(image=tk_thumb)

    def refresh_export_preview(self) -> None:
        self.export_preview_canvas.delete("all")
        if not self.export_variants:
            self.export_preview_canvas.create_text(
                self.export_preview_canvas.winfo_width() // 2,
                self.export_preview_canvas.winfo_height() // 2,
                text="Create a result first in Step 1-4",
                fill="#666666",
                font=("Segoe UI", 13),
            )
            return

        mode = self.export_mode_var.get()
        if mode not in self.export_variants:
            mode = "as_is"
            self.export_mode_var.set(mode)

        image = self.export_variants[mode]
        canvas_w = max(1, self.export_preview_canvas.winfo_width())
        canvas_h = max(1, self.export_preview_canvas.winfo_height())
        scale = min(canvas_w / image.width, canvas_h / image.height)
        target_w = int(image.width * scale)
        target_h = int(image.height * scale)
        preview = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
        self.export_preview_tk = ImageTk.PhotoImage(preview)

        x = (canvas_w - target_w) // 2
        y = (canvas_h - target_h) // 2
        self.export_preview_canvas.create_image(x, y, anchor="nw", image=self.export_preview_tk)

    def save_selected(self) -> None:
        if not self.export_variants:
            messagebox.showwarning("Nothing to save", "Create a result first in Step 1-4.")
            return

        selected_modes = [
            mode
            for mode, selected_var in self.export_selection_vars.items()
            if selected_var.get()
        ]
        if not selected_modes:
            messagebox.showwarning("No formats selected", "Select at least one format to save.")
            return

        target_folder = filedialog.askdirectory(
            title="Select folder to save all selected formats",
            initialdir=str(self.default_save_dir),
            mustexist=True,
        )
        if not target_folder:
            return

        source_name = self.image_path.stem if self.image_path else "SnapTales"
        save_dir = Path(target_folder)
        saved_files: list[str] = []

        for mode in selected_modes:
            image = self.export_variants[mode]
            suffix = EXPORT_FILE_SUFFIXES.get(mode, mode)
            suffix_part = f"_{suffix}" if suffix else ""
            file_name = f"{source_name}_SnapTale{suffix_part}.jpg"
            file_path = save_dir / file_name
            image.save(file_path, format="JPEG", quality=95)
            saved_files.append(file_name)

        self.status_var.set(f"Saved {len(saved_files)} file(s) to {save_dir}")
        messagebox.showinfo(
            "Saved",
            "Saved files:\n" + "\n".join(saved_files),
        )


def main() -> None:
    root = tk.Tk()
    SnapTalesApp(root)
    root.minsize(1200, 760)
    root.mainloop()


if __name__ == "__main__":
    main()
