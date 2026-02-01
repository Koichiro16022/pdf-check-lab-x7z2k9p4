import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Total Scan", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 全情報網羅スキャン")

# --- Gemini API 設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        st.sidebar.success("✅ 閃 (SOU) 2.5 接続完了")
except Exception as e:
    st.sidebar.error(f"❌ 接続失敗: {e}")

def get_total_text(img):
    # 特定のものを探させず、全てのインクを文字化させるプロンプト
    prompt = """
    あなたは超高性能な文字読み取りスキャナーです。画像内の全てのインク跡（印刷文字、手書き文字、記号、線）を漏らさず抽出してください。

    【抽出ルール】
    1. 隅々まで：ページ番号 (2/2)、日付、ハンコの「山」「本」、備考欄の「検査時取付」、全て書き出してください。
    2. 記号の可視化：文字の上に〇があれば [〇合]、横線があれば [取消線-合] のように、文字と記号の重なりを正確に表現してください。
    3. 表の構造：1行に1つの項目が来るように、上から順に箇条書きで出力してください。
    4. 忖度禁止：読めない文字を勝手に補完せず、見えた通りに出力してください。
    """
    try:
        response = model.generate_content([prompt, img])
        return response.text
    except Exception as e:
        return f"解析エラー: {e}"

# --- 操作パネル ---
if "GEMINI_API_KEY" in st.secrets:
    st.sidebar.header("PDFアップロード")
    file1 = st.sidebar.file_uploader("原本PDF", type=["pdf"], key="p1")
    file2 = st.sidebar.file_uploader("比較用PDF", type=["pdf"], key="p2")

    if file1 and file2:
        current_page = st.sidebar.number_input("解析ページ", min_value=1, value=1) - 1

        if st.button("閃 (SOU) で全情報をスキャン"):
            with st.spinner("AIが全インク跡を解析中..."):
                d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
                d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
                p1 = d1.load_page(current_page)
                p2 = d2.load_page(current_page)
                
                # 解像度7倍
                mat = fitz.Matrix(7, 7)
                img1 = Image.open(io.BytesIO(p1.get_pixmap(matrix=mat).tobytes("png")))
                img2 = Image.open(io.BytesIO(p2.get_pixmap(matrix=mat).tobytes("png")))
                
                # 左右個別に解析
                text1 = get_total_text(img1)
                text2 = get_total_text(img2)
                
                st.divider()
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    st.subheader("原本の全抽出データ")
                    st.text_area("原本", text1, height=500)
                with col_t2:
                    st.subheader("比較用の全抽出データ")
                    st.text_area("比較用", text2, height=500)
                
                # 最後にAIに「この2つのテキストの違い」をまとめさせる
                if st.button("この2つの抽出結果から差異を抽出"):
                    diff_prompt = f"以下の2つのテキストを比較し、違い（追加・削除・変更）を箇条書きで教えてください。\n\n原本:\n{text1}\n\n比較用:\n{text2}"
                    diff_report = model.generate_content(diff_prompt)
                    st.subheader("🔍 最終差異レポート")
                    st.write(diff_report.text)

                d1.close()
                d2.close()
