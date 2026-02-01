import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image, ImageEnhance

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Precision Line", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 精密線条・取消線検知")

# --- Gemini API 設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        st.sidebar.success("✅ 閃 (SOU) 2.5 接続完了")
except Exception as e:
    st.sidebar.error(f"❌ 接続失敗: {e}")

def get_line_scan(img1, img2):
    prompt = """
    あなたは超精密な図面検図員です。文字を「読む」だけでなく、画像上の「線」を「視覚的」に解析してください。

    【重点スキャン項目】
    1. 取消線の検知：立会検査欄などの「合・否」の文字の上に、横線（ー）や斜線が引かれていないか凝視してください。文字が線で消されている場合は「[取消線あり]」と報告してください。
    2. 端っこの文字：書類の端にある「(2/2)」や「(1/2)」といったページ情報を、ゴミだと思わずに必ず抽出してください。
    3. 検査時取付：この5文字は完璧に捕捉してください。

    【判定ルール：物理位置】
    4. 記号の位置：〇やレ点が「合」の上にあるか「否」の上にあるか、ピクセル単位の報告を継続してください。

    【出力形式】
    ・項目名：[判定結果] [取消線の有無]
    ・追記/ページ：見つかった全ての文字情報を出力
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

        if st.button("閃 (SOU) で線条検知を実行"):
            with st.spinner("文字を消している『線』を探索中..."):
                d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
                d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
                p1 = d1.load_page(current_page)
                p2 = d2.load_page(current_page)
                
                # 解像度7倍
                mat = fitz.Matrix(7, 7)
                pix1 = p1.get_pixmap(matrix=mat)
                pix2 = p2.get_pixmap(matrix=mat)
                
                img1 = Image.open(io.BytesIO(pix1.tobytes("png")))
                img2 = Image.open(io.BytesIO(pix2.tobytes("png")))
                
                # 線を際立たせるため、シャープネスを強めにかけます
                from PIL import ImageEnhance
                img2 = ImageEnhance.Sharpness(img2).enhance(3.0)
                
                report = get_line_scan(img1, img2)
                
                st.divider()
                st.subheader("🔍 精密線条レポート（取消線・ページ番号対応）")
                st.write(report)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img1, caption="原本")
                with col2:
                    st.image(img2, caption="比較用（シャープネス処理済）")
                
                d1.close()
                d2.close()
else:
    st.info("左側のサイドバーでAPIキーを確認してください。")
