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

def process_pages(pdf_path, start_page, end_page):
    print(f"开始处理页面 {start_page} 到 {end_page}")
    try:
        images = convert_from_path(pdf_path, dpi=300, first_page=start_page, last_page=end_page)
        print(f"成功将页面 {start_page}-{end_page} 转换为图像")
        
        # 收集这个批次的所有文本
        batch_texts = []
        for i, image in enumerate(images, start=start_page):
            print(f"正在处理第 {i} 页...")
            gray_image = ImageOps.grayscale(image)
            text = pytesseract.image_to_string(gray_image, lang='chi_sim+eng')
            if not text.strip():
                print(f"警告：第 {i} 页未识别出文本")
            else:
                print(f"第 {i} 页成功识别出 {len(text)} 个字符")
            batch_texts.append((i, f"=== 第 {i} 页 ===\n{text}\n\n"))
        
        return batch_texts
    except Exception as e:
        print(f"处理页面时出错: {str(e)}")
        raise e

def extract_text_from_pdf(pdf_path, num_pages, output_file):
    print(f"开始提取文本，总页数：{num_pages}")
    max_workers = os.cpu_count() or 4
    memory = psutil.virtual_memory()
    batch_size = max(1, int(memory.available / (500 * 1024 * 1024)))
    print(f"使用 {max_workers} 个线程，每批处理 {batch_size} 页")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 创建一个列表来存储所有页面的文本
        all_texts = []
        futures = []
        
        # 提交任务并记录页码范围
        for start_page in range(1, num_pages + 1, batch_size):
            end_page = min(start_page + batch_size - 1, num_pages)
            future = executor.submit(process_pages, pdf_path, start_page, end_page)
            futures.append((start_page, end_page, future))

        # 按顺序等待结果并收集文本
        for start_page, end_page, future in tqdm(sorted(futures, key=lambda x: x[0]), 
                                               total=len(futures), 
                                               desc="处理进度"):
            try:
                batch_texts = future.result()  # 等待当前批次完成
                all_texts.extend(batch_texts)
            except Exception as e:
                print(f"处理批次 {start_page}-{end_page} 时出错: {str(e)}")
                raise e

        # 按页码排序并写入文件
        all_texts.sort(key=lambda x: x[0])  # 按页码排序
        with open(output_file, 'w', encoding='utf-8') as file:
            for _, text in all_texts:
                file.write(text)

def process_pdfs_from_txt(txt_file_path):
    # 读取txt文件中的PDF路径
    with open(txt_file_path, 'r', encoding='utf-8') as f:
        pdf_paths = f.read().splitlines()
    
    # 遍历每个PDF文件路径
    for pdf_path in pdf_paths:
        if pdf_path.strip() and pdf_path.lower().endswith('.pdf'):
            try:
                process_single_pdf(pdf_path)
            except Exception as e:
                print(f"处理PDF文件 {pdf_path} 时出错: {str(e)}")

def process_single_pdf(pdf_path):
    try:
        # 创建output文件夹（如果不存在）
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # 使用PDF文件名生成输出文件路径，但保存到output文件夹中
        pdf_filename = os.path.basename(pdf_path)
        output_filename = os.path.splitext(pdf_filename)[0] + '.txt'
        output_file = os.path.join(output_dir, output_filename)
        
        # 获取PDF页数
        num_pages = get_num_pages(pdf_path)
        print(f"开始处理PDF文件: {pdf_path}")
        print(f"总页数: {num_pages}")
        
        # 提取文本
        extract_text_from_pdf(pdf_path, num_pages, output_file)
        print(f"文件处理完成，文本已保存至: {output_file}")
        
    except Exception as e:
        raise Exception(f"处理PDF时发生错误: {str(e)}")

def main():
    # 获取用户输入的txt文件路径
    txt_path = input("请输入包含PDF文件路径的txt文件地址: ")
    
    # 检查文件是否存在
    if not os.path.exists(txt_path):
        print("找不到指定的txt文件！")
        return
        
    process_pdfs_from_txt(txt_path)

if __name__ == "__main__":
    main()
