import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Stable Scan", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 安定比較スキャン")

# --- Gemini API 設定 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.5-flash')
else:
    st.error("SecretsにAPIキーを設定してください")

# --- データ保持用の初期化 ---
if 'text1' not in st.session_state: st.session_state.text1 = ""
if 'text2' not in st.session_state: st.session_state.text2 = ""

def get_total_text(img):
    prompt = """
    あなたは超高性能な文字読み取りスキャナーです。画像内の全てのインク跡（印刷文字、手書き文字、記号、線）を漏らさず抽出してください。
    【重要】ページ番号(2/2)、日付、ハンコの「山」「本」、備考欄の「検査時取付」、全て書き出してください。
    文字の上に〇があれば [〇合]、横線があれば [取消線-合] と表現してください。
    """
    try:
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

    if st.button("1. 閃 (SOU) で全情報を個別にスキャン"):
        with st.spinner("AIが全インク跡を解析中..."):
            d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
            d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
            p1 = d1.load_page(current_page)
            p2 = d2.load_page(current_page)
            
            mat = fitz.Matrix(7, 7)
            img1 = Image.open(io.BytesIO(p1.get_pixmap(matrix=mat).tobytes("png")))
            img2 = Image.open(io.BytesIO(p2.get_pixmap(matrix=mat).tobytes("png")))
            
            # 結果をセッションに保存（これで消えなくなります）
            st.session_state.text1 = get_total_text(img1)
            st.session_state.text2 = get_total_text(img2)
            d1.close()
            d2.close()

    # 読み取り結果の表示
    if st.session_state.text1 and st.session_state.text2:
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.subheader("原本の全抽出データ")
            st.text_area("原本", st.session_state.text1, height=400)
        with col_t2:
            st.subheader("比較用の全抽出データ")
            st.text_area("比較用", st.session_state.text2, height=400)
        
        st.divider()
        
        # 差異抽出ボタン（データが保持されているので今度は消えません）
        if st.button("2. この抽出結果から最終的な差異をまとめる"):
            with st.spinner("二つのデータを突き合わせ中..."):
                diff_prompt = f"""
                以下の2つのテキストを比較し、石田様が検品で重視する「追加された日付、ハンコ(山・本)、検査時取付の有無、ページ番号の違い、取消線の有無」を重点的にまとめてください。
                
                原本データ:
                {st.session_state.text1}
                
                比較用データ:
                {st.session_state.text2}
                """
                diff_report = model.generate_content(diff_prompt)
                st.subheader("🔍 最終差異レポート")
                st.success("差異の抽出が完了しました")
                st.write(diff_report.text)
else:
    st.info("左側のサイドバーからPDFをアップロードしてください。")
