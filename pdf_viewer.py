import tkinter as tk
from tkinter import filedialog, Canvas, Scrollbar

import fitz
import os
from PIL import Image, ImageTk, ImageDraw
from page_config import MediaSize, PageConfig

class PDFViewer:
	def __init__(self, root):
		self.root = root
		self.root.title('PDF Viewer')
		self.root.geometry('800x600')
		# self.root.state('zoomed')
		self.root.configure(padx=20, pady=20)

		# Create main frame
		self.main_frame = tk.Frame(root)
		self.main_frame.pack(fill=tk.BOTH, expand=True)

		self.create_nav_widgets()

		# Split view - Canvas on left, info panel on right
		self.split_frame = tk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
		self.split_frame.pack(fill=tk.BOTH, expand=True)

		# Create and place widgets
		self.create_canvas_widgets()
		self.create_pdf_widgets()

		# Initialize variables
		self.current_pdf = None
		self.current_page = 0
		self.zoom_level = 1.0  # For zoom functionality

		# Image cache dictionary to store original page images
		# Keys will be page numbers, values will be PIL Image objects
		self.image_cache = {}

		# Current displayed image (must keep reference to prevent garbage collection)
		self.current_image = None


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

	def create_canvas_widgets(self):
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


	def create_pdf_widgets(self):
		# Information panel on right
		self.info_frame = tk.LabelFrame(self.split_frame, text='PDF')
		self.split_frame.add(self.info_frame)
		self.split_frame.paneconfig(self.info_frame, minsize=200)

		# Size information labels
		self.size_info = tk.Label(self.info_frame, text='Width: -- pt\nHeight: -- pt')
		self.size_info.pack(pady=10)

		# Dropdown for paper sizes
		self.paper_size_var = tk.StringVar(value='A4')
		self.paper_size_label = tk.Label(self.info_frame, text='Paper Size:')
		self.paper_size_label.pack(anchor='w')

		paper_sizes = [size.name for size in MediaSize]
		paper_sizes.append("Custom")

		self.paper_size_dropdown = tk.OptionMenu(self.info_frame, self.paper_size_var, *paper_sizes)
		self.paper_size_dropdown.pack(fill='x')

		# Orientation selection
		self.orientation_var = tk.StringVar(value='Portrait')
		self.portrait_radio = tk.Radiobutton(self.info_frame, text='Portrait', variable=self.orientation_var, value='Portrait', command=self.update_dimensions)
		self.landscape_radio = tk.Radiobutton(self.info_frame, text='Landscape', variable=self.orientation_var, value='Landscape', command=self.update_dimensions)
		self.portrait_radio.pack(anchor='w')
		self.landscape_radio.pack(anchor='w')

		# Width input
		self.width_var = tk.IntVar()
		self.width_label = tk.Label(self.info_frame, text='Width:')
		self.width_label.pack(anchor='w')
		self.width_entry = tk.Entry(self.info_frame, textvariable=self.width_var)
		self.width_entry.pack(fill='x')
		self.width_var.trace_add('write', self.set_custom_size)

		# Height input
		self.height_var = tk.IntVar()
		self.height_label = tk.Label(self.info_frame, text='Height:')
		self.height_label.pack(anchor='w')
		self.height_entry = tk.Entry(self.info_frame, textvariable=self.height_var)
		self.height_entry.pack(fill='x')
		self.height_var.trace_add('write', self.set_custom_size)

		# Margin horizontal input
		self.margin_h_var = tk.IntVar()
		self.margin_h_label = tk.Label(self.info_frame, text='Printer Margin Horizontal:')
		self.margin_h_label.pack(anchor='w')
		self.margin_h_entry = tk.Entry(self.info_frame, textvariable=self.margin_h_var)
		self.margin_h_entry.pack(fill='x')

		# Margin vertical input
		self.margin_v_var = tk.IntVar()
		self.margin_v_label = tk.Label(self.info_frame, text='Printer Margin Vertical:')
		self.margin_v_label.pack(anchor='w')
		self.margin_v_entry = tk.Entry(self.info_frame, textvariable=self.margin_v_var)
		self.margin_v_entry.pack(fill='x')

		# Bleed input
		self.bleed_var = tk.IntVar()
		self.bleed_label = tk.Label(self.info_frame, text='Overlap:')
		self.bleed_label.pack(anchor='w')
		self.bleed_entry = tk.Entry(self.info_frame, textvariable=self.bleed_var)
		self.bleed_entry.pack(fill='x')

		# Add loading indicator
		self.loading_var = tk.StringVar()
		self.loading_label = tk.Label(self.info_frame, textvariable=self.loading_var, fg='blue')
		self.loading_label.pack(pady=10)

	def set_custom_size(self, *args):
		self.paper_size_var.set('Custom')

	def update_orientation(self):
		pass
	def update_dimensions(self):
		size_name = self.paper_size_var.get()

		print(MediaSize.__members__)
		if size_name in MediaSize.__members__:
			width, height = MediaSize[size_name].value
			if self.orientation_var.get() == 'Landscape':
				width, height = height, width
		else:
			width, height = self.width_var.get(), self.height_var.get()

		self.width_var.set(width)
		self.height_var.set(height)

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
		self.current_pdf = fitz.open(file_path)
		self.current_page = 0
		self.zoom_level = 1.0

		# Update UI
		filename = os.path.basename(file_path)
		self.file_label_text.set(f'Loaded: {filename}')
		self.zoom_level_var.set('100%')

		# Enable navigation and zoom buttons
		self.update_navigation_buttons()
		self.zoom_in_button.config(state=tk.NORMAL)
		self.zoom_out_button.config(state=tk.NORMAL)

		# Display page size information
		self.update_sidebar(self.current_page)
		self.update_page_view()

		# Clear loading indicator
		self.loading_var.set('')


	def load_page_image(self, page_num):
		'''Load a page image into the cache if not already present'''
		if self.current_pdf is None or page_num < 0 or page_num > len(self.current_pdf) - 1:
			return False

		# Check if the page is already in the cache
		if page_num in self.image_cache:
			return True

		# Show loading indicator
		self.loading_var.set(f'Loading page {page_num + 1}...')
		self.root.update()

		# Convert PDF page to image using the in-memory PDF data
		page = self.current_pdf[page_num]
		pix = page.get_pixmap()
		self.image_cache[page_num] = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
		self.loading_var.set('')
		return True


	def update_page_view(self):
		if not self.load_page_image(self.current_page):
			return

		# Get the original image from cache
		original = self.image_cache[self.current_page]

		# Apply zoom by creating a resized copy
		new_width = int(original.width * self.zoom_level)
		new_height = int(original.height * self.zoom_level)
		display_img = original.resize((new_width, new_height), Image.LANCZOS)

		# Convert to PhotoImage for Tkinter
		self.current_image = self.draw_grid(display_img) #ImageTk.PhotoImage(display_img)

		# Clear canvas and display the image
		self.canvas.delete('all')
		self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image)

		# Update canvas scrollregion
		self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))


	def draw_grid(self, img: Image):
		# Convert DPI from PDF to pixels (assuming 72 DPI in PDF)
		dpi = 72  # Default PyMuPDF resolution
		cm_to_px = lambda cm: int((cm / 2.54) * dpi)  # Convert cm to pixels
		grid_spacing = cm_to_px(5)  # 5 cm grid spacing

		# Draw the grid overlay
		draw = ImageDraw.Draw(img)
		width, height = img.size

		# Draw vertical lines
		for x in range(0, width, grid_spacing):
			draw.line([(x, 0), (x, height)], fill="red", width=1)

		# Draw horizontal lines
		for y in range(0, height, grid_spacing):
			draw.line([(0, y), (width, y)], fill="red", width=1)
		return ImageTk.PhotoImage(img)


	def update_sidebar(self, page_num):
		if not self.current_pdf or page_num < 0 or page_num >= len(self.current_pdf):
			return

		# Get page dimensions from /MediaBox
		width_pts, height_pts = self.current_pdf[page_num].mediabox_size
		self.size_info.config(text=f'Width: {width_pts:.2f} points\nHeight: {height_pts:.2f} points')

	def next_page(self):
		if self.current_page >= len(self.current_pdf) - 1:
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
		self.page_info.set(f'Page: {self.current_page + 1} / {len(self.current_pdf)}')
		self.prev_button.config(state= tk.DISABLED if self.current_page <= 0 else tk.NORMAL)
		self.next_button.config(state=tk.DISABLED if self.current_page >= len(self.current_pdf)-1 else tk.NORMAL)

if __name__ == '__main__':
	# Create main window
	root = tk.Tk()
	app = PDFViewer(root)
	root.mainloop()