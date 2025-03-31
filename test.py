import fitz  # PyMuPDF

# Open an existing PDF or create a new one
doc = fitz.open("frog.pdf")  # Creates a blank PDF
page = doc[0]  # Add a new blank page

# Define start and end points of the line
start = (100, 300)  # x1, y1
end = (300, 300)  # x2, y2

# Draw the line on the page

page.draw_line(start, end)
crop_rect = fitz.Rect((200, 200), (600, 600))
# page.set_mediabox(crop_rect)

# Save the modified document
doc.save("output.pdf")
doc.close()