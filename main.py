import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image, ImageChops, ImageEnhance

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Durability Test", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 耐久テスト：2枚目の実証")

# --- Gemini API 設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash')
else:
    st.sidebar.error("SecretsにAPIキーを設定してください")

def get_diff_image(img1, img2):
    img1 = img1.convert("RGB")
    # ズレによる偽陽性を防ぐため、サイズを厳密に合わせる
    img2 = img2.convert("RGB").resize(img1.size)
    diff = ImageChops.difference(img1, img2)
    # 差分をさらに際立たせ、ノイズを飛ばす
    return ImageEnhance.Contrast(diff).enhance(5.0)

def get_physical_analysis(img1, img2, diff_img):
    prompt = """
    あなたは超精密な検図スキャナーです。
    提供された「原本」「比較用」および「差分画像（3枚目）」を元に、追加された情報を特定してください。

    【重点項目】
    1. 取消線：合・否の文字を打ち消す「横線」の光があるか。
    2. 合格の〇：文字を囲う「円形」の光があるか。
    3. 特記事項：「検査時取付」などの手書きの文字の光を特定せよ。
    4. 日付・ハンコ：新しく押された日付印や氏名印。

    事実のみを簡潔に、項目別に報告してください。
    """
    try:
        response = model.generate_content([prompt, img1, img2, diff_img])
        return response.text
    except Exception as e:
        return f"解析エラー: {e}"

# --- UI ---
st.sidebar.header("PDFアップロード")
file1 = st.sidebar.file_uploader("原本PDF", type=["pdf"], key="p1")
file2 = st.sidebar.file_uploader("比較用PDF", type=["pdf"], key="p2")

if file1 and file2:
    d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
    page_count = len(d1)
    
    # ここで次のページ（2枚目以降）を指定
    st.sidebar.divider()
    current_page = st.sidebar.number_input("検証するページ番号", min_value=1, max_value=page_count, value=1) - 1

    if st.button(f"ページ {current_page + 1} の物理差分スキャンを実行"):
        with st.spinner(f"ページ {current_page + 1} の実証試験中..."):
            d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
            p1 = d1.load_page(current_page)
            p2 = d2.load_page(current_page)
            
            # 高解像度（5倍）で詳細を保持
            mat = fitz.Matrix(5, 5)
            img1 = Image.open(io.BytesIO(p1.get_pixmap(matrix=mat).tobytes("png")))
            img2 = Image.open(io.BytesIO(p2.get_pixmap(matrix=mat).tobytes("png")))
            
            diff_img = get_diff_image(img1, img2)
            report = get_physical_analysis(img1, img2, diff_img)
            
            st.divider()
            st.subheader(f"🔍 物理差分レポート（ページ {current_page + 1}）")
            st.write(report)
            
            cols = st.columns(3)
            cols[0].image(img1, caption="原本")
            cols[1].image(img2, caption="比較用")
            cols[2].image(diff_img, caption="差分画像（光る箇所が変更点）")
            
            d2.close()
    d1.close()
