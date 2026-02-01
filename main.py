import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image, ImageEnhance, ImageDraw

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Precision v3", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 境界線ガイド・物理判定")

# --- Gemini API 設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        st.sidebar.success("✅ 閃 (SOU) 2.5 接続完了")
except Exception as e:
    st.sidebar.error(f"❌ 接続失敗: {e}")

def get_guided_scan(img1, img2):
    prompt = """
    あなたは超精密な幾何学検査員です。
    画像内の「合」と「否」という文字に対し、手書きの「〇」がどの座標に位置しているかを0.1ミリ単位で判定してください。

    【絶対判定基準】
    1. 左右の判定：「合」の文字の真上、あるいは「合」の文字を囲むように印があれば、それは100%「合」です。
    2. 誤読への警告：あなたは先ほど「否」と誤読しました。今回はそのミスを猛省し、「否」という文字の輪郭に印が直接重なっていない限り、「否」と判定してはいけません。
    3. 〇の中心点：印の「中心」がどこにあるかを見てください。右側の「否」に寄っていない限り、それは「合」への意思表示です。
    4. 検査時取付：この文字列を画像から探し出し、有無を報告してください。

    【出力形式】
    ・項目名：[原本の状態] ➔ [比較用の状態] (理由: 記号が「合」の真上にあるため、等)
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

        if st.button("閃 (SOU) で境界線判定を実行"):
            with st.spinner("ピクセル単位での位置関係を再計算中..."):
                d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
                d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
                p1 = d1.load_page(current_page)
                p2 = d2.load_page(current_page)
                
                # 解像度を7倍(最高クラス)に引き上げ
                mat = fitz.Matrix(7, 7)
                pix1 = p1.get_pixmap(matrix=mat)
                pix2 = p2.get_pixmap(matrix=mat)
                
                img1 = Image.open(io.BytesIO(pix1.tobytes("png")))
                img2 = Image.open(io.BytesIO(pix2.tobytes("png")))
                
                # 画像のコントラストを極限まで上げ、ノイズを飛ばす
                img2 = ImageEnhance.Contrast(img2).enhance(3.0)
                img2 = ImageEnhance.Sharpness(img2).enhance(2.0)
                
                report = get_guided_scan(img1, img2)
                
                st.divider()
                st.subheader("🔍 厳格・物理差異レポート")
                st.write(report)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img1, caption="原本")
                with col2:
                    st.image(img2, caption="比較用（超解像・強調処理）")
                
                d1.close()
                d2.close()
