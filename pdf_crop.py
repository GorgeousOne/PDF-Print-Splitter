import fitz
from typing import List

def crop_slice_pdf(doc, page_num, pos_xs: List[float], pos_ys: List[float], page_w:float, page_h:float, crop_vert:float = 0, crop_horz:float = 0, bleed:float = 0):
	new_doc = fitz.open()

	for _ in range(len(pos_xs) * len(pos_ys)):
		new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)

	big_w, big_h = doc[page_num].mediabox_size
	print(new_doc.page_count)

	i = 0
	for y in pos_ys:
		for x in pos_xs:
			# i hate y up
			crop_rect = fitz.Rect(x, big_h - (y + page_h), x + page_w, big_h - y)
			page = new_doc[i]
			page.set_mediabox(crop_rect)
			i += 1
	return new_doc

if __name__ == '__main__':
	input_pdf = "frog.pdf"
	doc = fitz.open(input_pdf)
	new_doc = crop_slice_pdf(doc, 0, [0, 200], [0, 200], 200, 200)
	new_doc.save("test-split.pdf")