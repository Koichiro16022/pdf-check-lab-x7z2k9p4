import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
from pdf2image import convert_from_bytes
import pytesseract
import difflib

# --- ページ設定 ---
st.set_page_config(page_title="零 (ZERO) - PDF Comparison", layout="wide")
st.title("零 (ZERO) - PDF高精度比較 (OCR搭載版)")

# --- テキスト抽出関数（自動OCR切り替え・10文字閾値） ---
def get_pdf_text_optimized(file_bytes):
    # ① デジタルテキスト抽出を試行
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    # ② 10文字未満（画像PDF）と判断した場合、自動でOCRを実行
    if len(text.strip()) < 10:
        with st.spinner("⚠️ 画像を検出しました。無料OCRで解析中...（しばらくお待ちください）"):
            # PDFを画像に変換
            images = convert_from_bytes(file_bytes)
            ocr_text = ""
            for img in images:
                # 日本語・英語対応
                ocr_text += pytesseract.image_to_string(img, lang='jpn+eng')
            return ocr_text
    
    return text

# --- サイドバー：ファイルアップロード ---
st.sidebar.header("比較用PDFをアップロード")
file1 = st.sidebar.file_uploader("原本PDF (原本)", type=["pdf"], key="pdf1")
file2 = st.sidebar.file_uploader("比較用PDF (最新)", type=["pdf"], key="pdf2")

# --- メイン処理 ---
if file1 and file2:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("原本の解析結果")
        text1 = get_pdf_text_optimized(file1.read())
        st.text_area("原本テキスト", text1, height=300)

    with col2:
        st.subheader("比較用の解析結果")
        text2 = get_pdf_text_optimized(file2.read())
        st.text_area("比較用テキスト", text2, height=300)

    # 比較実行ボタン
    if st.button("比較を実行"):
        st.divider()
        st.subheader("比較レポート")
        
        # 行単位で比較
        diff = difflib.ndiff(text1.splitlines(), text2.splitlines())
        
        # 差異を整理して表示
        diff_data = []
        for line in diff:
            if line.startswith('+ '):
                diff_data.append({"状態": "追加 (最新のみ)", "内容": line[2:]})
            elif line.startswith('- '):
                diff_data.append({"状態": "削除 (原本のみ)", "内容": line[2:]})
        
        if diff_data:
            df_diff = pd.DataFrame(diff_data)
            st.table(df_diff)
        else:
            st.success("両方のPDFに差異は見つかりませんでした。")

else:
    st.info("左側のサイドバーから比較したい2つのPDFを選択してください。")

# --- フッター ---
st.sidebar.markdown("---")
st.sidebar.caption("Project: 零 (ZERO) | Powered by Python & OCR")
