import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image, ImageChops, ImageEnhance

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Interference Test", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 実証：文字重なり・複雑ページ検証")

# --- Gemini API 設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash')
else:
    st.sidebar.error("SecretsにAPIキーを設定してください")

def get_diff_image(img1, img2):
    img1 = img1.convert("RGB")
    img2 = img2.convert("RGB").resize(img1.size)
    # 差分抽出
    diff = ImageChops.difference(img1, img2)
    # 差分を5倍に強調
    return ImageEnhance.Contrast(diff).enhance(5.0)

def get_interference_analysis(img1, img2, diff_img):
    prompt = """
    あなたは超精密な検図スキャナーです。
    今回の検証テーマは「重なりの分離」です。

    【解析の優先順位】
    1. 文字と印の重なり：文字（合・否）の上に〇や取消線が重なっている場合、差分画像では「重なった部分だけが欠けている」あるいは「重なった部分だけが強く光っている」可能性があります。それを見逃さず、印の形（円形か、直線か）を推論して報告してください。
    2. 複雑な背景：罫線や既存の文字が少しでもズレていると、差分画像にノイズとして現れます。それらを無視し、明らかに「後から追加されたインク跡」のみを抽出してください。
    3. ページ間の不整合：ページ番号やヘッダーの微細な違い。

    「この光っている跡は、何という文字や記号を構成しているか」という視点で報告してください。
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
    current_page = st.sidebar.number_input("検証ページ", min_value=1, max_value=page_count, value=1) - 1

    if st.button(f"ページ {current_page + 1} の干渉解析を実行"):
        with st.spinner("重なりとレイアウトの歪みを解析中..."):
            d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
            p1 = d1.load_page(current_page)
            p2 = d2.load_page(current_page)
            
            # 最高精度の7倍でレンダリング（重なりを見抜くため）
            mat = fitz.Matrix(7, 7)
            img1 = Image.open(io.BytesIO(p1.get_pixmap(matrix=mat).tobytes("png")))
            img2 = Image.open(io.BytesIO(p2.get_pixmap(matrix=mat).tobytes("png")))
            
            diff_img = get_diff_image(img1, img2)
            report = get_interference_analysis(img1, img2, diff_img)
            
            st.divider()
            st.subheader(f"🔍 干渉解析レポート（ページ {current_page + 1}）")
            st.write(report)
            
            cols = st.columns(3)
            cols[0].image(img1, caption="原本")
            cols[1].image(img2, caption="比較用")
            cols[2].image(diff_img, caption="差分（干渉チェック用）")
            
            d2.close()
    d1.close()
