import tkinter as tk
from tkinter import filedialog, Canvas, Scrollbar, messagebox

import fitz
import os
from PIL import Image, ImageTk, ImageDraw
from page_config import Unit, PageSize, cover_area
from pdf_crop import slice_pdf

class PDFViewer:
	def __init__(self, root):
		self.root = root
		self.root.title('PDF Viewer')
		self.root.geometry('1200x800')
		# self.root.state('zoomed') #maximize window
		self.root.configure(padx=20, pady=20)

		self.doc = None
		self.current_page = 0
		self.pdf_image = None

		# Create main frame
		self.main_frame = tk.Frame(root)
		self.main_frame.pack(fill=tk.BOTH, expand=True)

		self.create_nav_widgets()

		# Split view - Canvas on left, info panel on right
		self.split_frame = tk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
		self.split_frame.pack(fill=tk.BOTH, expand=True)

		# Create and place widgets
		self.create_page_view_widgets()
		self.create_slicing_widgets()

		# Current displayed image (must keep reference to prevent garbage collection)
		self.convert_unit()
		self.default_dpi = 96


	def create_nav_widgets(self):
		# Top control panel
		self.nav_frame = tk.Frame(self.main_frame)
		self.nav_frame.pack(fill=tk.X, pady=(0, 10))

		# Button to load PDF file
		self.load_button = tk.Button(
			self.nav_frame,
			text='Load PDF',
			command=self.load_pdf,
			width=15
		)
		self.load_button.pack(side=tk.LEFT, padx=5)

		# Label to show current file
		self.file_label_text = tk.StringVar()
		self.file_label_text.set('No file loaded')
		self.file_label = tk.Label(
			self.nav_frame,
			textvariable=self.file_label_text
		)
		self.file_label.pack(side=tk.LEFT, padx=10)

		# Page navigation frame
		self.page_frame = tk.Frame(self.main_frame)
		self.page_frame.pack(fill=tk.X, pady=5)

		# Page navigation buttons
		self.prev_button = tk.Button(
			self.page_frame,
			text='<< Prev',
			command=self.prev_page,
			state=tk.DISABLED
		)
		self.prev_button.pack(side=tk.LEFT, padx=5)

		self.page_info = tk.StringVar()
		self.page_info.set('Page: 0 / 0')
		self.page_label = tk.Label(self.page_frame, textvariable=self.page_info)
		self.page_label.pack(side=tk.LEFT, padx=20)

		self.next_button = tk.Button(
			self.page_frame,
			text='Next >>',
			command=self.next_page,
			state=tk.DISABLED
		)
		self.next_button.pack(side=tk.LEFT, padx=5)

		# Zoom buttons
		self.zoom_out_button = tk.Button(
			self.page_frame,
			text='-',
			command=self.zoom_out,
			state=tk.DISABLED
		)
		self.zoom_out_button.pack(side=tk.RIGHT, padx=5)

		self.zoom_level_var = tk.StringVar()
		self.zoom_level_var.set('100%')
		self.zoom_label = tk.Label(self.page_frame, textvariable=self.zoom_level_var)
		self.zoom_label.pack(side=tk.RIGHT, padx=10)

		self.zoom_in_button = tk.Button(
			self.page_frame,
			text='+',
			command=self.zoom_in,
			state=tk.DISABLED
		)
		self.zoom_in_button.pack(side=tk.RIGHT, padx=5)

	def create_page_view_widgets(self):
		# Canvas frame with scrollbars
		self.canvas_frame = tk.Frame(self.split_frame)
		self.split_frame.add(self.canvas_frame)
		self.split_frame.paneconfig(self.canvas_frame, width=1920)  # Wider main viewer

		# Create canvas with scrollbars
		self.scrollbar_frame = tk.Frame(self.canvas_frame)
		self.scrollbar_frame.pack(fill=tk.BOTH, expand=True)

		# Add scrollbars
		self.h_scrollbar = Scrollbar(self.scrollbar_frame, orient=tk.HORIZONTAL)
		self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

		self.v_scrollbar = Scrollbar(self.scrollbar_frame)
		self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

		# Create canvas
		self.canvas = Canvas(
			self.scrollbar_frame,
			bg='light gray',
			xscrollcommand=self.h_scrollbar.set,
			yscrollcommand=self.v_scrollbar.set
		)
		self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
		self.canvas.bind_all("<MouseWheel>", self.on_mouse_scroll)

		# Configure scrollbars
		self.h_scrollbar.config(command=self.canvas.xview)
		self.v_scrollbar.config(command=self.canvas.yview)


	def create_slicing_widgets(self):
		# Information panel on right
		self.inputs_frame = tk.LabelFrame(self.split_frame, text='PDF Slicing')
		self.split_frame.add(self.inputs_frame)
		self.split_frame.paneconfig(self.inputs_frame, minsize=200)

		# Dropdown for display unit
		display_units = [f'{unit.name} ({unit.abbreviation})' for unit in Unit]
		self.unit_var = tk.StringVar(value=display_units[2])
		self.unit = Unit.Point
		self.unit_label = tk.Label(self.inputs_frame, text='Display Unit:')
		self.unit_label.pack(anchor='w')

		self.unit_dropdown = tk.OptionMenu(self.inputs_frame, self.unit_var, *display_units, command=self.convert_unit)
		self.unit_dropdown.pack(fill='x')

		# Size information labels
		self.size_info = tk.Label(self.inputs_frame, text='Width: --\nHeight: --')
		self.size_info.pack(pady=10)

		# Dropdown for paper sizes
		paper_sizes = [size.name for size in PageSize]
		self.paper_size_var = tk.StringVar(value=paper_sizes[1])
		self.paper_size_label = tk.Label(self.inputs_frame, text='Paper Size:')
		self.paper_size_label.pack(anchor='w')

		self.paper_size_dropdown = tk.OptionMenu(self.inputs_frame, self.paper_size_var, *paper_sizes, command=self.select_paper_size_preset)
		self.paper_size_dropdown.pack(fill='x')
		
		# Orientation selection
		self.orientation_var = tk.StringVar(value='Portrait')
		self.portrait_radio = tk.Radiobutton(self.inputs_frame, text='Portrait', variable=self.orientation_var, value='Portrait', command=self.update_orientation)
		self.landscape_radio = tk.Radiobutton(self.inputs_frame, text='Landscape', variable=self.orientation_var, value='Landscape', command=self.update_orientation)
		self.portrait_radio.pack(anchor='w')
		self.landscape_radio.pack(anchor='w')

		# Width input
		self.width_var = tk.DoubleVar()
		self.width_label = tk.Label(self.inputs_frame, text='Width:')
		self.width_label.pack(anchor='w')
		self.width_entry = tk.Entry(self.inputs_frame, textvariable=self.width_var)
		self.width_entry.pack(fill='x')
		# self.width_var.trace_add('write', self.set_custom_paper_size)
		self.width_entry.bind("<FocusOut>", self.set_custom_paper_size)

		# Height input
		self.height_var = tk.DoubleVar()
		self.height_label = tk.Label(self.inputs_frame, text='Height:')
		self.height_label.pack(anchor='w')
		self.height_entry = tk.Entry(self.inputs_frame, textvariable=self.height_var)
		self.height_entry.pack(fill='x')
		# self.height_var.trace_add('write', self.set_custom_paper_size)
		self.height_entry.bind("<FocusOut>", self.set_custom_paper_size)

		# Margin horizontal input
		self.margin_h_var = tk.DoubleVar(value=Unit.Millimeter.toPt(7))
		self.margin_h_label = tk.Label(self.inputs_frame, text='Printer Margin Horizontal:')
		self.margin_h_label.pack(anchor='w')
		self.margin_h_entry = tk.Entry(self.inputs_frame, textvariable=self.margin_h_var)
		self.margin_h_entry.pack(fill='x')
		self.margin_h_entry.bind("<FocusOut>", self.update_page_view)

		# Margin vertical input
		self.margin_v_var = tk.DoubleVar(value=Unit.Millimeter.toPt(7))
		self.margin_v_label = tk.Label(self.inputs_frame, text='Printer Margin Vertical:')
		self.margin_v_label.pack(anchor='w')
		self.margin_v_entry = tk.Entry(self.inputs_frame, textvariable=self.margin_v_var)
		self.margin_v_entry.pack(fill='x')
		self.margin_v_entry.bind("<FocusOut>", self.update_page_view)

		# Bleed input
		self.bleed_var = tk.DoubleVar(value=Unit.Millimeter.toPt(3))
		self.bleed_label = tk.Label(self.inputs_frame, text='Overlap:')
		self.bleed_label.pack(anchor='w')
		self.bleed_entry = tk.Entry(self.inputs_frame, textvariable=self.bleed_var)
		self.bleed_entry.pack(fill='x')
		self.bleed_entry.bind("<FocusOut>", self.update_page_view)

		self.slice_count_var = tk.StringVar()
		self.slice_count_label = tk.Label(self.inputs_frame, textvariable=self.slice_count_var, fg='blue')
		self.slice_count_label.pack(pady=10)

		# Add loading indicator
		self.loading_var = tk.StringVar()
		self.loading_label = tk.Label(self.inputs_frame, textvariable=self.loading_var, fg='blue')
		self.loading_label.pack(pady=10)


		self.slice_button = tk.Button(
			self.inputs_frame,
			text='Save sliced PDF',
			command=self.slice_n_dice,
			state=tk.DISABLED
		)
		self.slice_button.pack(padx=10)

		self.length_vars = [self.width_var, self.height_var, self.margin_v_var, self.margin_h_var, self.bleed_var]
		self.select_paper_size_preset()


	def convert_unit(self, *args):
		next_unit = Unit[self.unit_var.get().split()[0]]
		print(self.unit, "->", next_unit)
		
		for var in self.length_vars:
			var.set(self.unit.to(next_unit, var.get()))

		self.unit = next_unit
		self.update_sidebar(self.current_page)

	def select_paper_size_preset(self, *args):
		size_name = self.paper_size_var.get()
		
		if size_name not in PageSize.__members__:
			return
		
		width, height = PageSize[size_name].value
		if self.orientation_var.get() == 'Landscape':
			width, height = height, width
		self.width_var.set(Unit.Point.to(self.unit, width))
		self.height_var.set(Unit.Point.to(self.unit, height))
		self.update_page_view()

	def set_custom_paper_size(self, *args):
		self.paper_size_var.set("Custom")
		self.orientation_var.set("Portrait" if self.height_var.get() > self.width_var.get() else "Landscape")
		self.update_page_view()

	def update_orientation(self):
		width, height = self.width_var.get(), self.height_var.get()
		min_val = min(width, height)
		max_val = max(width, height)
		mode = self.orientation_var.get()
		self.width_var.set(min_val if mode=="Portrait" else max_val)
		self.height_var.set(max_val if mode=="Portrait" else min_val)
		self.update_page_view()

	def load_pdf(self):
		file_path = filedialog.askopenfilename(
			title='Select PDF File',
			filetypes=[('PDF files', '*.pdf'), ('All files', '*.*')]
		)

		if not file_path:
			return

		# Clear any existing cached images
		self.image_cache = {}

		# Show loading indicator
		self.loading_var.set('Loading PDF...')
		self.root.update()

		# Set variables
		self.doc = fitz.open(file_path)
		self.current_page = 0

		# Update UI
		filename = os.path.basename(file_path)
		self.file_label_text.set(f'Loaded: {filename}')
		self.update_navigation_buttons()

		self.zoom_level_var.set('100%')
		self.zoom_level = 1.0
		self.zoom_in_button.config(state=tk.NORMAL)
		self.zoom_out_button.config(state=tk.NORMAL)
		self.slice_button.config(state=tk.NORMAL)

		# Display page size information
		self.update_sidebar(self.current_page)
		self.update_page_view()

		# Clear loading indicator
		self.loading_var.set('')

	def get_display_dpi(self):
		return round(self.default_dpi * self.zoom_level)
	
	def update_page_view(self, *args):
		if not self.doc:
			return
		
		# idk seems to be faster/not slower to just render with higher dpi?
		page = self.doc[self.current_page]
		pix = page.get_pixmap(dpi=self.get_display_dpi())
		display_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

		# Convert to PhotoImage for Tkinter
		self.pdf_image = self.draw_grid(display_img) #ImageTk.PhotoImage(display_img) 

		# Clear canvas and display the image
		self.canvas.delete('all')
		self.canvas.create_image(0, 0, anchor=tk.NW, image=self.pdf_image)

		# Update canvas scrollregion
		self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))


	def draw_grid(self, img: Image):
		# I see a repetitive pattern here
		
		area_w, area_h = self.doc[self.current_page].mediabox_size
		page_w = self.unit.toPt(self.width_var.get())
		page_h = self.unit.toPt(self.height_var.get())
		margin_v = self.unit.toPt(self.margin_v_var.get())
		margin_h = self.unit.toPt(self.margin_h_var.get())
		bleed = self.unit.toPt(self.bleed_var.get())

		pos_xs, pos_ys = cover_area(area_w, area_h, page_w, page_h, margin_v, margin_h, bleed)
		self.slice_count_var.set(f"Current number of split pages: {len(pos_xs) * len(pos_ys)}")
		# Draw the grid overlay
		draw = ImageDraw.Draw(img)

		pixel_scale = self.get_display_dpi() / 72
		for y in pos_ys:
			for x in pos_xs:
				draw.rectangle([x*pixel_scale, y*pixel_scale, (x+page_w)*pixel_scale, (y+page_h)*pixel_scale], outline="red", width=1)

		return ImageTk.PhotoImage(img)

	def slice_n_dice(self):
		file_path = filedialog.asksaveasfilename(
			title='Save Sliced PDF File',
			filetypes=[('PDF files', '*.pdf')]
		)
		if not file_path:
			return
		if not file_path.endswith(".pdf"):
			file_path += ".pdf"

		area_w, area_h = self.doc[self.current_page].mediabox_size
		page_w = self.unit.toPt(self.width_var.get())
		page_h = self.unit.toPt(self.height_var.get())
		margin_v = self.unit.toPt(self.margin_v_var.get())
		margin_h = self.unit.toPt(self.margin_h_var.get())
		bleed = self.unit.toPt(self.bleed_var.get())
		pos_xs, pos_ys = cover_area(area_w, area_h, page_w, page_h, margin_v, margin_h, bleed)

		new_doc = slice_pdf(self.doc, self.current_page, pos_xs, pos_ys, page_w, page_h, margin_v, margin_h, bleed)
		new_doc.save(file_path)

	def update_sidebar(self, page_num):
		if not self.doc or page_num < 0 or page_num >= len(self.doc):
			return

		# Get page dimensions from /MediaBox
		width_pts, height_pts = self.doc[page_num].mediabox_size
		width = Unit.Point.to(self.unit, width_pts)
		height = Unit.Point.to(self.unit, height_pts)
		self.size_info.config(text=f'Width: {width:.2f} {self.unit.abbreviation}\nHeight: {height:.2f} {self.unit.abbreviation}')

	def next_page(self):
		if self.current_page >= len(self.doc) - 1:
			return
		self.current_page += 1
		self.update_sidebar(self.current_page)
		self.update_page_view()
		self.update_navigation_buttons()


	def on_mouse_scroll(self, event):
		if event.state & 0x4:  # Check if Ctrl key is pressed
			self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")  # Horizontal scroll
		else:
			self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")  # Vertical scroll

	def prev_page(self):
		if self.current_page <= 0:
			return
		self.current_page -= 1
		self.update_sidebar(self.current_page)
		self.update_page_view()
		self.update_navigation_buttons()

	def zoom_in(self):
		self.zoom_level = min(10, self.zoom_level * 1.5)
		self.zoom_level_var.set(f'{int(self.zoom_level * 100)}%')
		self.update_page_view()

	def zoom_out(self):
		self.zoom_level = max(0.05, self.zoom_level / 1.5)
		self.zoom_level_var.set(f'{int(self.zoom_level * 100)}%')
		self.update_page_view()

	def update_navigation_buttons(self):
		self.page_info.set(f'Page: {self.current_page + 1} / {len(self.doc)}')
		self.prev_button.config(state= tk.DISABLED if self.current_page <= 0 else tk.NORMAL)
		self.next_button.config(state=tk.DISABLED if self.current_page >= len(self.doc)-1 else tk.NORMAL)

if __name__ == '__main__':
	# Create main window
	root = tk.Tk()
	app = PDFViewer(root)
	root.mainloop()