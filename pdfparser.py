import pdfplumber
import pytesseract
from pdf2image import convert_from_path
import os
import pandas as pd
import camelot

pdf_path = "/Users/anousha_puvvala/Downloads/manual_extraction-pages/manual_extraction-pages-2.pdf"


def extract_text(pdf_path):
    extracted_text = ""
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(layout=True)  
            if text:
                extracted_text += text + "\n\n"  
    
    # if theres no selectable text is found, using OCR
    if not extracted_text.strip():
        print("No selectable text found. using ocr")
        images = convert_from_path(pdf_path)
        for img in images:
            ocr_text = pytesseract.image_to_string(img, config="--psm 6")  
            extracted_text += ocr_text + "\n"

    return extracted_text

def extract_tables(pdf_path):
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            table_data = page.extract_tables()
            for table in table_data:
                df = pd.DataFrame(table) 
                df.columns = df.iloc[0]  # first row are column headers
                df = df[1:].reset_index(drop=True)  # removing the first row from data
                tables.append(df)

    camelot_tables = camelot.read_pdf(pdf_path, pages="all")
    for table in camelot_tables:
        tables.append(table.df)  

    return tables

# extracting the images 
def extract_images(pdf_path, output_folder):
    images_extracted = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            for j, image in enumerate(page.images):
                img_data = image["stream"].get_data()
                img_filename = os.path.join(output_folder, f"page_{i+1}_image_{j+1}.png")
                with open(img_filename, "wb") as f:
                    f.write(img_data)
                images_extracted.append(img_filename)

    return images_extracted

output_folder = "/Users/anousha_puvvala/Desktop/extracted_images"
os.makedirs(output_folder, exist_ok=True)

txt_output = "/Users/anousha_puvvala/Desktop/extracted_text.txt"
text_output = extract_text(pdf_path)
with open(txt_output, "w", encoding="utf-8") as file:
    file.write("Extracted Text:\n")
    file.write(text_output + "\n\n")
tables_output = extract_tables(pdf_path)
images_output = extract_images(pdf_path, output_folder)

print("\n Extracted Tables:")
for i, table in enumerate(tables_output):
    print(f"\n Table {i+1}:\n")
    print(table.to_markdown())  

print("\nExtracted Images : ", images_output)