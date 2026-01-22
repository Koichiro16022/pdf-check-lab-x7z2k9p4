import streamlit as st
import fitz
import os
import urllib.request
import io
# 日本時間設定のために追加
from datetime import datetime, timedelta, timezone

# ページの設定
st.set_page_config(page_title="検査室用PDF比較ツール", layout="centered")

# --- タイトルとガイド ---
st.title("📝 検査室用PDF比較ツール")
st.info("👇 2つのPDFをドロップして、下の「実行して保存」ボタンを押してください。")

# フォントの準備
font_path = "NotoSansCJKjp-Regular.otf"
@st.cache_resource
def load_font():
    if not os.path.exists(font_path):
        font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"
        urllib.request.urlretrieve(font_url, font_path)
    return font_path

f_path = load_font()

# --- 1. 読み込みエリア ---
st.subheader("1. 検査データの読み込み")
file1 = st.file_uploader("【元データ（旧）】をここにドロップ", type="pdf")
file2 = st.file_uploader("【修正後（新）】をここにドロップ", type="pdf")

st.markdown("---")

# --- 2. 実行エリア ---
st.subheader("2. 実行と保存")

# 日本時間（JST）を指定して取得（UTC+9時間）
jst = timezone(timedelta(hours=+9), 'JST')
current_time = datetime.now(jst).strftime("%Y%m%d_%H%M")

output_name = st.text_input("保存するファイル名", value=f"検査比較結果_{current_time}")

def process_pdf(f1, f2):
    doc_orig = fitz.open(stream=f1.read(), filetype="pdf")
    doc_mod = fitz.open(stream=f2.read(), filetype="pdf")
    
    # 判定の許容範囲を30に設定（削除漏れ対策）
    X_TOL, Y_TOL = 30, 30 
    
    for p_no in range(max(len(doc_orig), len(doc_mod))):
        if p_no >= len(doc_mod): continue
        page_mod = doc_mod[p_no]
        rect = page_mod.rect
        
        # ページ不一致の場合の警告
        if p_no >= len(doc_orig):
            warning_msg = "【 未確認 】\n\nページ不一致：\n元データに該当するページがありません。"
            center_rect = fitz.Rect(rect.width * 0.1, rect.height * 0.3, rect.width * 0.9, rect.height * 0.7)
            page_mod.insert_textbox(center_rect, warning_msg, fontsize=30, fontfile=f_path, fontname="jp-g", color=(1, 0, 0), align=fitz.TEXT_ALIGN_CENTER)
            
            inset_rect = fitz.Rect(5, 5, rect.width - 5, rect.height - 5)
            annot = page_mod.add_rect_annot(inset_rect)
            annot.set_colors(stroke=(1, 0, 0))
            annot.set_border(width=8)
            annot.update()
            continue
            
        p_orig = doc_orig[p_no]
        w_orig = p_orig.get_text("words")
        w_mod = page_mod.get_text("words")
        
        # 追加箇所の判定（赤枠）
        for wm in w_mod:
            txt_m = wm[4].strip()
            if not txt_m: continue
            if not any(txt_m == wo[4].strip() and abs(wm[0]-wo[0])<X_TOL and abs(wm[1]-wo[1])<Y_TOL for wo in w_orig):
                annot = page_mod.add_rect_annot(fitz.Rect(wm[:4]))
                annot.set_colors(stroke=(1, 0, 0))
                annot.update()
                
        # 削除箇所の判定（青枠）
        for wo in w_orig:
            txt_o = wo[4].strip()
            if not txt_o: continue
            if not any(txt_o == wm[4].strip() and abs(wo[0]-wm[0])<X_TOL and abs(wo[1]-wm[1])<Y_TOL for wm in w_mod):
                annot = page_mod.add_rect_annot(fitz.Rect(wo[:4]))
                annot.set_colors(stroke=(0, 0, 1))
                annot.update()
                
    out_pdf = io.BytesIO()
    doc_mod.save(out_pdf, garbage=4, deflate=True)
    return out_pdf.getvalue()

if file1 and file2:
    pdf_data = process_pdf(file1, file2)
    st.download_button(
        label="🚀 比較を実行して保存（フォルダ選択）",
        data=pdf_data,
        file_name=f"{output_name}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
else:
