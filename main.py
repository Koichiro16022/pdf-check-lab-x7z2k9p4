import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image, ImageEnhance

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Precision", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - バイアス排除・物理判定")

# --- Gemini API (閃) の設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        st.sidebar.success("✅ 閃 (SOU) 2.5 接続完了")
except Exception as e:
    st.sidebar.error(f"❌ 接続失敗: {e}")

# --- AIへの「物理判定」徹底指示関数 ---
def get_physical_scan(img1, img2):
    prompt = """
    あなたは先入観を一切持たない精密検査員です。「合」が一般的であるという思い込みを捨て、画像にある事実のみを報告してください。
    
    【判定の物理ロジック】
    1. 判定位置の厳密化：「合」と「否」の中間地点を境界線とし、記号（〇）の中心が1ピクセルでも右にあれば「否」へのマーク、左にあれば「合」へのマークと客観的に判断してください。
    2. 記号の報告：手書きの印は、形にかかわらず「〇」として扱います。「◎」や「否に追加」といった主観的な解釈をせず、「どの文字の上に重なっているか」だけを報告してください。
    3. キーワードの執念：小さな「検査時取付」という文字を絶対に見落とさないでください。
    4. 差異の抽出：原本に存在せず、比較用にのみ存在する「日付」「ハンコ」「手書きの記号」を一つ残らずリストアップしてください。

    【出力形式】
    ・項目名：原本の状態 ➔ 比較用の状態
    """
    try:
        response = model.generate_content([prompt, img1, img2])
        return response.text
    except Exception as e:
        return f"解析エラー: {e}"

# --- 操作パネル ---
if "GEMINI_API_KEY" in st.secrets:
    st.sidebar.header("PDFアップロード")
    file1 = st.sidebar.file_uploader("原本PDF", type=["pdf"], key="p1")
    file2 = st.sidebar.file_uploader("比較用PDF", type=["pdf"], key="p2")

    if file1 and file2:
        current_page = st.sidebar.number_input("比較するページ", min_value=1, value=1) - 1

        if st.button("閃 (SOU) で物理判定を実行"):
            with st.spinner("AIの先入観をリセットし、ピクセル単位でスキャン中..."):
                d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
                d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
                p1 = d1.load_page(current_page)
                p2 = d2.load_page(current_page)
                
                # 解像度を6倍に維持（小さな差異を捉えるため）
                mat = fitz.Matrix(6, 6)
                pix1 = p1.get_pixmap(matrix=mat)
                pix2 = p2.get_pixmap(matrix=mat)
                
                img1 = Image.open(io.BytesIO(pix1.tobytes("png")))
                img2 = Image.open(io.BytesIO(pix2.tobytes("png")))
                
                # コントラスト補正で手書き文字を強調
                img2 = ImageEnhance.Contrast(img2).enhance(2.0)
                
                report = get_physical_scan(img1, img2)
                
                st.divider()
                st.subheader("🔍 物理差異レポート（先入観なし）")
                st.write(report)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img1, caption="原本")
                with col2:
                    st.image(img2, caption="比較用（強調処理済）")
                
                d1.close()
                d2.close()
else:
    st.info("左側のサイドバーから設定を行ってください。")
