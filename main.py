import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image, ImageEnhance

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Robots Eye", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 非・忖度 物理スキャン")

# --- Gemini API 設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        st.sidebar.success("✅ 閃 (SOU) 2.5 接続完了")
except Exception as e:
    st.sidebar.error(f"❌ 接続失敗: {e}")

def get_robotic_scan(img1, img2):
    prompt = """
    あなたは感情や先入観を持たない、冷徹な物理スキャナーです。
    画像内のインクの跡（文字・記号）を、1ピクセルも違わず「見たまま」報告してください。

    【鉄の掟：文字の読み取り】
    1. 勝手な変換禁止：「ダム」を「ゴム」と読んだり、「検査」を「出荷」と読んだりするような「意味の解釈」を一切禁じます。一画一画を凝視し、書かれている通りの漢字を出力してください。
    2. 存在しない記号の禁止：丸印やレ点があると言うなら、その線の形が明確に見える場合のみ報告してください。少しでも「汚れ」や「印刷のカスレ」に見えるものは無視してください。
    3. 検査時取付：この5文字を画像内から執念深く探してください。似た言葉に逃げず、この5文字そのものを抽出してください。

    【絶対判定基準：判定印】
    4. 座標判定：印の中心が「合」という漢字の境界線より内側にあるか、外側にあるかだけで判断してください。

    【出力形式】
    ・項目名：[判定結果] (根拠: 印の形状と位置を簡潔に)
    ・注釈：画像内の追記文字を「見たまま」抽出
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

        if st.button("閃 (SOU) で物理スキャンを実行"):
            with st.spinner("AIの「脳」を止め、「眼」だけで解析中..."):
                d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
                d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
                p1 = d1.load_page(current_page)
                p2 = d2.load_page(current_page)
                
                # 解像度は7倍を維持
                mat = fitz.Matrix(7, 7)
                pix1 = p1.get_pixmap(matrix=mat)
                pix2 = p2.get_pixmap(matrix=mat)
                
                img1 = Image.open(io.BytesIO(pix1.tobytes("png")))
                img2 = Image.open(io.BytesIO(pix2.tobytes("png")))
                
                # 過度な補正は幻覚を呼ぶため、コントラストを1.5倍に抑えます
                img2 = ImageEnhance.Contrast(img2).enhance(1.5)
                
                report = get_robotic_scan(img1, img2)
                
                st.divider()
                st.subheader("🔍 物理スキャンレポート（非・忖度）")
                st.write(report)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img1, caption="原本")
                with col2:
                    st.image(img2, caption="比較用（物理スキャン対象）")
                
                d1.close()
                d2.close()
