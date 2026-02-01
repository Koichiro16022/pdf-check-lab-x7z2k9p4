import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
from pdf2image import convert_from_bytes
import pytesseract
import difflib

# --- ページ設定 ---
st.set_page_config(page_title="零 (ZERO) - Smart Comparison", layout="wide")
st.title("零 (ZERO) - ページ別・高精度比較")

# --- テキスト抽出関数（モード切替対応） ---
def get_pdf_text_for_page(file_bytes, page_num, use_ocr=False):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page = doc.load_page(page_num)
    
    if use_ocr:
        # OCRモード：そのページだけ画像化して解析
        with st.spinner(f"{page_num+1}ページ目をOCR解析中..."):
            # 指定ページのみを画像変換（1ページ単位なので高速）
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 解像度2倍
            img_bytes = pix.tobytes("png")
            import io
            from PIL import Image
            img = Image.open(io.BytesIO(img_bytes))
            text = pytesseract.image_to_string(img, lang='jpn+eng')
    else:
        # 通常モード：デジタルテキスト抽出
        text = page.get_text()
    
    doc.close()
    return text

# --- サイドバー：設定 ---
st.sidebar.header("1. ファイルアップロード")
file1 = st.sidebar.file_uploader("原本PDF", type=["pdf"], key="pdf1")
file2 = st.sidebar.file_uploader("比較用PDF", type=["pdf"], key="pdf2")

if file1 and file2:
    # ページ数確認
    doc1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
    page_count = len(doc1)
    doc1.close()

    st.sidebar.divider()
    st.sidebar.header("2. 比較設定")
    current_page = st.sidebar.number_input("表示ページ", min_value=1, max_value=page_count, value=1) - 1
    use_ocr = st.sidebar.checkbox("このページにOCRを適用する", help="デジタル文字が読み取れない、または画像の場合にチェックしてください")

    # --- メイン比較処理 ---
    col1, col2 = st.columns(2)
    
    # ページ内容の取得
    with col1:
        st.subheader(f"原本 ({current_page + 1}ページ目)")
        text1 = get_pdf_text_for_page(file1.getvalue(), current_page, use_ocr)
        st.text_area("原本テキスト", text1, height=300, key=f"t1_{current_page}")

    with col2:
        st.subheader(f"比較用 ({current_page + 1}ページ目)")
        text2 = get_pdf_text_for_page(file2.getvalue(), current_page, use_ocr)
        st.text_area("比較用テキスト", text2, height=300, key=f"t2_{current_page}")

    # 比較実行
    if st.button(f"{current_page + 1}ページ目の差異を確認"):
        st.divider()
        diff = difflib.ndiff(text1.splitlines(), text2.splitlines())
        diff_data = [{"状態": "追加" if l.startswith('+ ') else "削除", "内容": l[2:]} 
                     for l in diff if l.startswith('+ ') or l.startswith('- ')]
        
        if diff_data:
            st.table(pd.DataFrame(diff_data))
        else:
            st.success("このページに差異は見つかりませんでした。")

else:
    st.info("サイドバーからPDFをアップロードしてください。")

# --- フッター ---
st.sidebar.markdown("---")
st.sidebar.caption(f"Project: 零 (ZERO) | Page Control Mode")
