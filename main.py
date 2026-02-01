import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image, ImageEnhance

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Integrated", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 全能力統合・精密スキャン")

# --- Gemini API 設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        st.sidebar.success("✅ 閃 (SOU) 2.5 接続完了")
except Exception as e:
    st.sidebar.error(f"❌ 接続失敗: {e}")

def get_integrated_scan(img1, img2):
    prompt = """
    あなたは品質保証部門の責任者として、極めて冷静に2枚の書類を比較してください。
    
    【1. 判定欄の絶対ルール】
    - 「合」は左、「否」は右です。手書きの印（〇、レ点）の中心が「合」という文字のエリア内にあれば、迷わず「[合の上に印]」と報告してください。
    - 前回の「[否の上に〇]」という判定は誤りです。今回は「合」へのマークを最優先で正しく認識してください。

    【2. 取消線の検知】
    - 文字の上に「重なっている横線」がある場合のみ、「[取消線あり]」と報告してください。文字を囲んでいる丸印と混同しないでください。

    【3. 文字情報の抽出】
    - 「検査時取付」: No.3の横などに追記されているこの5文字を、執念深く探してください。「出荷時取付」と混同しないこと。
    - ページ番号: 書類上部の「(2/2)」や「(1/2)」を絶対に見落とさないでください。

    【4. 担当者・日付】
    - 欄外や下部の「山」「本」「日付」を正確に抽出してください。
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

        if st.button("閃 (SOU) で統合スキャンを実行"):
            with st.spinner("判定精度を維持しつつ、微細な注釈を探索中..."):
                d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
                d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
                p1 = d1.load_page(current_page)
                p2 = d2.load_page(current_page)
                
                # 解像度7倍で細部を巨大化
                mat = fitz.Matrix(7, 7)
                pix1 = p1.get_pixmap(matrix=mat)
                pix2 = p2.get_pixmap(matrix=mat)
                
                img1 = Image.open(io.BytesIO(pix1.tobytes("png")))
                img2 = Image.open(io.BytesIO(pix2.tobytes("png")))
                
                # 画像補正：シャープネスとコントラストを適度に調整
                img2 = ImageEnhance.Sharpness(img2).enhance(2.0)
                img2 = ImageEnhance.Contrast(img2).enhance(1.5)
                
                report = get_integrated_scan(img1, img2)
                
                st.divider()
                st.subheader("🔍 統合差異レポート（最終調整）")
                st.write(report)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img1, caption="原本")
                with col2:
                    st.image(img2, caption="比較用")
                
                d1.close()
                d2.close()
