import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image, ImageChops, ImageEnhance

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Physical Diff", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 物理差分・絶対検知モード")

# --- Gemini API 設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash')
else:
    st.sidebar.error("SecretsにAPIキーを設定してください")

def get_diff_image(img1, img2):
    # 二つの画像のサイズを完全に一致させる
    img1 = img1.convert("RGB")
    img2 = img2.convert("RGB").resize(img1.size)
    # 物理的な差分（引き算）を実行
    diff = ImageChops.difference(img1, img2)
    # 差分を5倍に強調して、薄いペン跡も浮かび上がらせる
    return ImageEnhance.Contrast(diff).enhance(5.0)

def get_physical_analysis(img1, img2, diff_img):
    prompt = """
    あなたは超精密な検図スキャナーです。
    提供された「差分画像（3枚目）」に映っている「光っている跡」こそが、比較用で追加された全ての情報です。

    【解析の絶対ルール】
    1. 取消線の検知：立会検査欄の「合・否」の場所に、横方向の鋭い光（線）があれば、それは「取消線」です。
    2. 合格の〇：文字を囲むような円形の光があれば、それは「合格の〇」です。
    3. 検査時取付：新しく出現した文字の光を読み取り、それが「検査時取付」であるか確認してください。
    4. ページ番号：ページ端に現れた数字の差分を報告してください。

    差分画像に映っているものは「汚れ」ではなく「全て重要な追記」として扱ってください。
    """
    try:
        response = model.generate_content([prompt, img1, img2, diff_img])
        return response.text
    except Exception as e:
        return f"解析エラー: {e}"

# --- 操作パネル ---
st.sidebar.header("PDFアップロード")
file1 = st.sidebar.file_uploader("原本PDF", type=["pdf"], key="p1")
file2 = st.sidebar.file_uploader("比較用PDF", type=["pdf"], key="p2")

if file1 and file2:
    d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
    page_count = len(d1)
    current_page = st.sidebar.number_input("解析ページ", min_value=1, max_value=page_count, value=1) - 1

    if st.button("閃 (SOU) で物理差分スキャンを実行"):
        with st.spinner("原本との差分（追加されたインク）を抽出中..."):
            p1 = d1.load_page(current_page)
            # 比較用PDFを開く
            d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
            p2 = d2.load_page(current_page)
            
            # 高解像度で画像化
            mat = fitz.Matrix(5, 5)
            img1 = Image.open(io.BytesIO(p1.get_pixmap(matrix=mat).tobytes("png")))
            img2 = Image.open(io.BytesIO(p2.get_pixmap(matrix=mat).tobytes("png")))
            
            # 差分画像を生成
            diff_img = get_diff_image(img1, img2)
            
            # AIに「差分」を主役に解析させる
            report = get_physical_analysis(img1, img2, diff_img)
            
            st.divider()
            st.subheader("🔍 物理差分・解析レポート")
            st.write(report)
            
            # 視覚的な確認
            cols = st.columns(3)
            cols[0].image(img1, caption="原本")
            cols[1].image(img2, caption="比較用")
            cols[2].image(diff_img, caption="差分（追加された箇所）")
            
            d2.close()
    d1.close()
