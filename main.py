import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import google.generativeai as genai
import io
from PIL import Image
import difflib

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Hybrid", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 究極・差異検出システム")

# --- Gemini API (閃) の設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        st.sidebar.success("✅ 閃 (SOU) エンジン接続完了")
    else:
        st.sidebar.error("❌ Secretsに『GEMINI_API_KEY』を設定してください")
except Exception as e:
    st.sidebar.error(f"❌ 閃 (SOU) 起動失敗: {e}")

# --- 2枚の画像を同時に比較する関数 ---
def compare_images_by_sou(img1, img2):
    prompt = """
    あなたは超精密な「間違い探し」の専門家です。
    左側の画像（原本）と右側の画像（比較用）を比較し、微細な違いを全てリストアップしてください。

    【重点チェック項目】
    1. 文字の有無：「検査時取付」「山」「本」などの、片方にしかない文字やハンコ。
    2. 数字の違い：日付（2025.03.18等）やページ番号（2/2 vs 1/2）の違い。
    3. 記号：[〇] や [V] のチェックがあるかないか。

    【出力形式】
    「原本：〇〇 」「比較用：××」という形式で、箇条書きで出力してください。
    違いがない場合は「完全一致」とだけ書いてください。
    """
    try:
        response = model.generate_content([prompt, img1, img2])
        return response.text
    except Exception as e:
        return f"解析エラー: {e}"

# --- 操作パネル ---
st.sidebar.header("1. PDFアップロード")
file1 = st.sidebar.file_uploader("原本PDF", type=["pdf"], key="f1")
file2 = st.sidebar.file_uploader("比較用PDF", type=["pdf"], key="f2")

if file1 and file2:
    doc1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
    page_count = len(doc1)
    doc1.close()

    st.sidebar.header("2. ページ選択")
    current_page = st.sidebar.number_input("表示ページ", min_value=1, max_value=page_count, value=1) - 1

    if st.button("閃 (SOU) で精密比較を実行"):
        with st.spinner("2枚の画像を並べて「間違い探し」をしています..."):
            # 画像化
            doc1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
            doc2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
            page1 = doc1.load_page(current_page)
            page2 = doc2.load_page(current_page)
            
            pix1 = page1.get_pixmap(matrix=fitz.Matrix(4, 4))
            pix2 = page2.get_pixmap(matrix=fitz.Matrix(4, 4))
            
            img1 = Image.open(io.BytesIO(pix1.tobytes("png")))
            img2 = Image.open(io.BytesIO(pix2.tobytes("png")))
            
            # 閃による直接比較
            result = compare_images_by_sou(img1, img2)
            
            st.divider()
            st.subheader("🔍 閃 (SOU) による差異レポート")
            st.write(result)
            
            # プレビュー表示
            col1, col2 = st.columns(2)
            with col1:
                st.image(img1, caption="原本 (画像)")
            with col2:
                st.image(img2, caption="比較用 (画像)")
            
            doc1.close()
            doc2.close()
else:
    st.info("サイドバーからPDFをアップロードしてください。")
