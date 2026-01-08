import os
import re
import shutil
import unicodedata

# cau hinh duong dan file
INPUT_FILE = "Backup/KTCT.txt"  
OUTPUT_DIR = "data"

# danh sach tieu de cac chuong
TITLES = {
    0: "PHẦN MỞ ĐẦU / KHÁI QUÁT",
    1: "CHƯƠNG 1: ĐỐI TƯỢNG, PHƯƠNG PHÁP & CHỨC NĂNG CỦA KTCT MÁC - LÊNIN",
    2: "CHƯƠNG 2: KINH TẾ THỊ TRƯỜNG & CÁC QUY LUẬT CƠ BẢN",
    3: "CHƯƠNG 3: LÝ LUẬN CỦA C.MÁC VỀ GIÁ TRỊ THẶNG DƯ",
    4: "CHƯƠNG 4: TÍCH LŨY & TÁI SẢN XUẤT TRONG NỀN KTTT",
    5: "CHƯƠNG 5: CẠNH TRANH, ĐỘC QUYỀN & VAI TRÒ CỦA NHÀ NƯỚC",
    6: "CHƯƠNG 6: KINH TẾ THỊ TRƯỜNG ĐỊNH HƯỚNG XHCN Ở VIỆT NAM",
    7: "CHƯƠNG 7: LỢI ÍCH KINH TẾ & HÀI HÒA QUAN HỆ LỢI ÍCH", 
    8: "CHƯƠNG 8: CÔNG NGHIỆP HÓA, HIỆN ĐẠI HÓA Ở VIỆT NAM",
    9: "CHƯƠNG 9: HỘI NHẬP KINH TẾ QUỐC TẾ & XÂY DỰNG NỀN KINH TẾ ĐỘC LẬP TỰ CHỦ"
}

def normalize_text(text):
    # chuan hoa van ban tieng viet
    if not text: return ""
    text = unicodedata.normalize('NFC', text)
    text = text.replace('\u00a0', ' ').replace('\u200b', '')
    return text.strip()

def clear_directory(directory):
    # xoa va tao lai thu muc data
    if os.path.exists(directory): shutil.rmtree(directory)
    os.makedirs(directory)

def is_noise(line):
    # loc cac dong nhieu nhu so trang hoac slide
    line_clean = line.strip().upper()
    if len(line_clean) < 30: 
        keywords = ["SLIDE", "TRANG ", "PAGE ", "GIẢNG VIÊN", "GV:", "LOGOS", "SOẠN BÀI"]
        for kw in keywords:
            if line_clean.startswith(kw) or line_clean.endswith(kw) or line_clean == kw.strip():
                return True
        if re.match(r"^(trang|page|slide)\s*\d+.*", line_clean, re.IGNORECASE):
            return True
    return False

def is_toc_line(line):
    # phat hien dong muc luc
    return "..." in line or "…" in line or re.search(r"\.{4,}\s*\d+$", line)

def get_chapter_number(line):
    # lay so chuong tu dong van ban
    match = re.match(r"^CHƯƠNG\s+([0-9IVX]+)", line, re.IGNORECASE)
    if match:
        chap_str = match.group(1)
        if chap_str.isdigit():
            return int(chap_str)
        else:
            roman_map = {'I':1, 'II':2, 'III':3, 'IV':4, 'V':5, 'VI':6, 
                         'VII':7, 'VIII':8, 'IX':9, 'X':10}
            return roman_map.get(chap_str.upper(), 0)
    return None

def split_word():
    # khoi tao thu muc
    clear_directory(OUTPUT_DIR)
    if not os.path.exists(INPUT_FILE):
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # khoi tao cac thung chua noi dung
    buckets = {i: [] for i in range(0, 10)} 
    current_chap_key = 0 
    
    # duyet qua tung dong de phan loai
    for line in lines:
        clean_line = normalize_text(line)
        
        if not clean_line or is_noise(clean_line): 
            continue

        chap_num = get_chapter_number(clean_line)
        
        if chap_num is not None:
            if is_toc_line(clean_line):
                continue
            
            if 0 < chap_num <= 9:
                current_chap_key = chap_num
            
            buckets[current_chap_key].append(line)
            continue

        buckets[current_chap_key].append(line)

    # ghi du lieu ra cac file rieng biet
    for i in range(0, 10):
        content_lines = buckets[i]
        full_content = "".join(content_lines)
        
        if len(full_content) < 200: 
            continue
            
        filename = f"Chuong_{i}.txt" if i > 0 else "Phan_Mo_Dau.txt"
        path = os.path.join(OUTPUT_DIR, filename)
        
        try:
            with open(path, "w", encoding="utf-8") as f:
                title_str = TITLES.get(i, f"CHƯƠNG {i}")
                header = f"TÀI LIỆU: {title_str}\n{'='*50}\n\n"
                f.write(header + full_content)
        except Exception:
            pass
            
    # thong bao hoan tat
    print(f"[*] da xu ly xong split data: {OUTPUT_DIR}")

if __name__ == "__main__":
    split_word()