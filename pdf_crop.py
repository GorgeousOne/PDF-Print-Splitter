import fitz
from typing import List
from page_config import Unit

def slice_pdf(doc, page_num, pos_xs: List[float], pos_ys: List[float], page_w:float, page_h:float, margin_y:float = 0, margin_x:float = 0, bleed:float = 0):
	new_doc = fitz.open()

	for _ in range(len(pos_xs) * len(pos_ys)):
		new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

	big_w, big_h = doc[page_num].mediabox_size
	index = 0

	bleed_x = page_w - margin_x - bleed
	bleed_y = page_h - margin_y - bleed
	overlap_x = page_w - margin_x - bleed
	overlap_y = page_h - margin_y - bleed

	for i, y in enumerate(pos_ys):
		for j, x in enumerate(pos_xs):
			# why has mediabox the only coordinate system with y-up in here?
			crop_rect = fitz.Rect((x, big_h - (y + page_h)), (x + page_w,  big_h - y))
			page = new_doc[index]
			page.set_mediabox(crop_rect)
			
			shape = page.new_shape()
			max_x = overlap_x
			max_y = overlap_y

			# left margin
			shape.draw_line((margin_y, 0), (margin_y, page_h))
			# top margin
			shape.draw_line((0, margin_x), (page_w, margin_x))

			if j == len(pos_xs)-1:
				# right margin
				max_x = big_w - x
				shape.draw_line((max_x, 0), (max_x, page_h))

			if i == len(pos_ys)-1:
				# bottom margin
				max_y = big_h - y
				shape.draw_line((0, max_y), (page_w, max_y))


			if j < len(pos_xs)-1:
				# right overlap indicator
				shape.draw_line((bleed_x, 0), (bleed_x, 2*margin_y))
				shape.draw_line((bleed_x, max_y - margin_y), (bleed_x, max_y + margin_y))

			if i < len(pos_ys)-1:
				# bottom overlap indicator
				shape.draw_line((0, bleed_y), (2*margin_x, bleed_y))
				shape.draw_line((max_x - margin_x, bleed_y), (max_x + margin_x, bleed_y))

			shape.finish(width = Unit.Millimeter.toPt(0.1), color=(.75, .75, .75))
			shape.commit()
			index += 1
	return new_doc

if __name__ == '__main__':
	input_pdf = "frog.pdf"
	doc = fitz.open(input_pdf)
	new_doc = slice_pdf(doc, 0, [0, 200, 400], [0, 200], 200, 200, 10, 10, 5)
	new_doc.save("test-split.pdf")