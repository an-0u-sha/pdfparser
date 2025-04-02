from mistralai import Mistral
import os
import json
import csv
import requests
import pandas as pd
import io
import re
from pdf2image import convert_from_path
from PIL import Image

pdf_images = convert_from_path(pdf_path) 

# setting up API key
api_key = os.environ["MISTRAL_API_KEY"]
pdf_path = "/Users/anousha_puvvala/Downloads/clinical-accessories-datasheet-carescape-respiratory-modules-doc2146306.pdf"
client = Mistral(api_key=api_key)

# uploading the pdf
with open(pdf_path, "rb") as f:
    uploaded_pdf = client.files.upload(
        file={
            "file_name": os.path.basename(pdf_path),
            "content": f.read(),
        },
        purpose="ocr"
    )

file_id = uploaded_pdf.id

# generating signed URL for OCR processing
signed_url_response = client.files.get_signed_url(file_id=file_id)
signed_url = signed_url_response.url  

# processing OCR
ocr_response = client.ocr.process(
    model="mistral-ocr-latest",
    document={
        "type": "document_url",
        "document_url": signed_url,
    }
)

# conversion to dict
ocr_dict = ocr_response.model_dump()

output_text_file = "/Users/anousha_puvvala/Desktop/extracted_text.txt"
tables_dir = "/Users/anousha_puvvala/Desktop/extracted_tables"
images_dir = "/Users/anousha_puvvala/Desktop/extracted_images"

os.makedirs(tables_dir, exist_ok=True)
os.makedirs(images_dir, exist_ok=True)

def convert_latex_subscripts(text):
    pattern = r'\$\\mathrm{([A-Za-z]+)}_{(\d+)}\$'
    converted_text = re.sub(pattern, r'\1<sub>\2</sub>', text)   
    return converted_text
    
#cropping image from PDF using bounding box data 
def crop_image_from_pdf(page_img, img_data, save_path):
    try:
        # page size
        img_width, img_height = page_img.size

        x1, y1 = img_data["top_left_x"], img_data["top_left_y"]
        x2, y2 = img_data["bottom_right_x"], img_data["bottom_right_y"]

        #obtaining bbox values
        left, top = min(x1, x2), min(y1, y2)
        right, bottom = max(x1, x2), max(y1, y2)
        cropped_img = page_img.crop((left, top, right, bottom))
        cropped_img.save(save_path)
        print(f"Image saved: {save_path}")

    except Exception as e:
        print(f"Cropping failed: {e}")

output_content = []

for page_index, page in enumerate(ocr_dict.get("pages", [])):
    page_text = f"\n\nPage {page_index + 1}\n{'=' * 40}\n"

    # extraction of text without tables
    if "markdown" in page:
        lines = page["markdown"].split("\n")
        clean_text = []
        table_text = []
        inside_table = False

        # extracting image references from markdown (`![img-0.jpeg](img-0.jpeg)`)
        image_references = re.findall(r"!\[.*?\]\((.*?)\)", page["markdown"])
        
        for line in lines:
            line=line.strip()
            # removing image references from the txt file (e.g., ![img-0.jpeg](img-0.jpeg))
            if re.match(r"!\[.*?\]\(.*?\)", line):
                continue
            if "|" in line:  # detection of table-like formatting
                table_text.append(line)
                inside_table = True
            elif inside_table:
                if table_text:
                    table_str = "\n".join(table_text)
                    try:
                        table_df = pd.read_csv(io.StringIO(table_str), sep="|", engine="python", skipinitialspace=True)
                        table_file = os.path.join(tables_dir, f"table_page{page_index+1}.csv")
                        table_df.to_csv(table_file, index=False)
                        print(f"Table saved: {table_file}")
                    except Exception as e:
                        print(f"Failed to process table on Page {page_index+1}: {e}")
                    table_text = []  # resetting table storage
                inside_table = False
            else:
                clean_text.append(line)

        page_text += "\n".join(clean_text)

    if "images" in page and isinstance(page["images"], list) and page["images"]:
        for img_index, img_data in enumerate(page["images"]):
           if all(k in img_data for k in ["top_left_x", "top_left_y", "bottom_right_x", "bottom_right_y"]):
                img_filename = f"page_{page_index+1}_img_{img_index+1}.jpeg"
                img_path = os.path.join(images_dir, img_filename)

                # cropping image using bbox
                crop_image_from_pdf(pdf_images[page_index], img_data, img_path)

    output_content.append(page_text)
    
cleaned_text = convert_latex_subscripts("\n\n".join(output_content))
#saving formatted ocr text 
with open(output_text_file, "w", encoding="utf-8") as f:
    f.write("\n\n".join(output_content) if output_content else "No text extracted.")

print(f"OCR text output saved to: {output_text_file}")
