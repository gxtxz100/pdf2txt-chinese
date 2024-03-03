import pytesseract
from pdf2image import convert_from_path
from PIL import ImageOps
from PyPDF2 import PdfReader
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import os
import psutil

def get_num_pages(pdf_path):
    reader = PdfReader(pdf_path)
    return len(reader.pages)

def process_and_write_page(pdf_path, start_page, end_page, output_file):
    images = convert_from_path(pdf_path, dpi=300, first_page=start_page, last_page=end_page)
    with open(output_file, 'a', encoding='utf-8') as file:
        for i, image in enumerate(images, start=start_page):
            gray_image = ImageOps.grayscale(image)
            text = pytesseract.image_to_string(gray_image, lang='chi_sim+eng')
            print(f"\nPage {i} Text:\n{text}")  # Print recognized text
            file.write(text + "\n")

def extract_text_from_pdf(pdf_path, num_pages, output_file):
    max_workers = os.cpu_count() or 4
    memory = psutil.virtual_memory()

    # Adjust batch_size based on available memory
    batch_size = max(1, int(memory.available / (500 * 1024 * 1024)))  # 500MB per batch

    with ThreadPoolExecutor(max_workers=max_workers) as executor, open(output_file, 'w', encoding='utf-8') as file:
        file.write("")  # Clear the file or ensure it's created
        futures = []
        for start_page in range(1, num_pages + 1, batch_size):
            end_page = min(start_page + batch_size - 1, num_pages)
            futures.append(executor.submit(process_and_write_page, pdf_path, start_page, end_page, output_file))

        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing Pages"):
            pass  # The actual writing is done in process_and_write_page, just wait for all to complete

pdf_path = './vvv.pdf'  # Replace with your PDF file path
output_file = 'extracted_text.txt'  # The file where the extracted text will be saved
num_pages = get_num_pages(pdf_path)
extract_text_from_pdf(pdf_path, num_pages, output_file)

print("Text extraction and saving complete.")
