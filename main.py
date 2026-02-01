import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image, ImageEnhance

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 PM Session", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 午後：取消線確定フェーズ")

# --- Gemini API 設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash')
else:
    st.error("SecretsにAPIキーを設定してください")

# データの保持
if 'text1' not in st.session_state: st.session_state.text1 = ""
if 'text2' not in st.session_state: st.session_state.text2 = ""

def get_total_text(img):
    prompt = """
    あなたは超精密な文字読み取りスキャナーです。
    【最優先：立会検査の取消線】
    立会検査欄の「合・否」の文字の上に、一筆で引かれた横線（取消線）がないか凝視してください。
    もし文字に横線が重なっていれば、必ず「[取消線あり]」と報告してください。

    【重要：全要素の抽出】
    ページ番号 (2/2)、ハンコ（山・本）、日付（2025.03.18等）、備考欄の「検査時取付」をすべて抽出してください。
    """
    try:
        # 画像の明瞭化
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.8) # 線をくっきりさせる
        response = model.generate_content([prompt, img])
        return response.text
    except Exception as e:
        return f"解析エラー: {e}"

# --- 操作パネル ---
st.sidebar.header("PDFアップロード")
file1 = st.sidebar.file_uploader("原本PDF", type=["pdf"], key="p1")
file2 = st.sidebar.file_uploader("比較用PDF", type=["pdf"], key="p2")

if file1 and file2:
    current_page = st.sidebar.number_input("解析ページ", min_value=1, value=1) - 1

    if st.button("1. 閃 (SOU) で物理スキャン実行"):
        with st.spinner("取消線のミリ単位の解析を開始..."):
            d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
            d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
            p1 = d1.load_page(current_page)
            p2 = d2.load_page(current_page)
            
            # 最高精度の7倍
            mat = fitz.Matrix(7, 7)
            img1 = Image.open(io.BytesIO(p1.get_pixmap(matrix=mat).tobytes("png")))
            img2 = Image.open(io.BytesIO(p2.get_pixmap(matrix=mat).tobytes("png")))
            
            st.session_state.text1 = get_total_text(img1)
            st.session_state.text2 = get_total_text(img2)
            d1.close()
            d2.close()

    if st.session_state.text1 and st.session_state.text2:
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.text_area("原本", st.session_state.text1, height=300)
        with col_t2:
            st.text_area("比較用", st.session_state.text2, height=300)
        
        if st.button("2. 最終差異レポート作成（取消線を確定）"):
            diff_prompt = f"""
            以下の2つのデータを比較し、検品差異をまとめてください。
            
            【特に注意】
            立会検査欄の「合・否」に「取消線」がある場合、それは「立会検査を実施していない」ことを示す重要事項です。必ず明記してください。
            その他、ページ番号の違い(2/2)、ハンコ(山・本)、日付、追記文字(検査時取付)の違いを報告してください。

            原本: {st.session_state.text1}
            比較用: {st.session_state.text2}
            """
            diff_report = model.generate_content(diff_prompt)
            st.subheader("🔍 午後の精密差異レポート")
            st.write(diff_report.text)

---

### 🛡️ 石田様、ここをチェックしてください

1.  **「立会検査に取消線あり」**という文言が、レポートに含まれているか。
2.  **ページ番号(2/2)**や**ハンコ(山・本)**が引き続き正しく拾えているか。

これが確認できれば、次は石田様が200枚を自動で倒すための**「全ページ比較ループ」**へコードを書き換えます。

14:40、ここから午後のスプリント、一気に加速しましょう！
まずはこの「取消線」の最終回答、いかがでしょうか？
