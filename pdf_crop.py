import fitz
from typing import List
from page_config import Unit

def slice_pdf(doc, page_num, pos_xs: List[float], pos_ys: List[float], page_w:float, page_h:float, margin_y:float = 0, margin_x:float = 0, bleed:float = 0):
	new_doc = fitz.open()

	for _ in range(len(pos_xs) * len(pos_ys)):
		new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

	big_w, big_h = doc[page_num].mediabox_size
	index = 0

	for i, y in enumerate(pos_ys):
		for j, x in enumerate(pos_xs):
			# why has mediabox the only coordinate system with y-up in here?
			crop_rect = fitz.Rect((x, big_h - (y + page_h)), (x + page_w,  big_h - y))
			page = new_doc[index]
			page.set_mediabox(crop_rect)
			
			shape = page.new_shape()

			bleed_x = page_w - margin_x - bleed
			bleed_y = page_h - margin_y - bleed
			content_max_x = page_w - margin_x
			content_max_y = page_h - margin_y

			# left margin
			shape.draw_line((margin_y, 0), (margin_y, page_h))
			# top margin
			shape.draw_line((0, margin_x), (page_w, margin_x))

			if j == len(pos_xs)-1:
				# right margin
				shape.draw_line((content_max_x, 0), (content_max_x, page_h))
			else:
				# right overlap indicator
				shape.draw_line((bleed_x, 0), (bleed_x, 2*margin_y))
				shape.draw_line((bleed_x, content_max_y - bleed - margin_y), (bleed_x, page_h))

			if i == len(pos_ys)-1:
				# bottom margin
				shape.draw_line((0, content_max_y), (page_w, content_max_y))
			else:
				# bottom overlap indicator
				shape.draw_line((0, bleed_y), (2*margin_x, bleed_y))
				shape.draw_line((content_max_x - bleed - margin_x, bleed_y), (page_w, bleed_y))

			shape.finish(width = Unit.Millimeter.toPt(0.1), color=(.75, .75, .75))
			shape.commit()
			index += 1
	return new_doc

if __name__ == '__main__':
	input_pdf = "frog.pdf"
	doc = fitz.open(input_pdf)
	new_doc = slice_pdf(doc, 0, [0, 200, 400], [0, 200], 200, 200, 10, 10, 5)
	new_doc.save("test-split.pdf")