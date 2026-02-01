import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
from pdf2image import convert_from_bytes
import pytesseract
import difflib
import google.generativeai as genai
import io
from PIL import Image

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Hybrid", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - ハイブリッド比較システム")

# --- Gemini API (閃) の設定 ---
# 接続状態を管理する変数
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # モデル名をフルパスで指定することでNotFoundエラーを回避します
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        st.sidebar.success("✅ 閃 (SOU) エンジン接続完了")
    else:
        st.sidebar.error("❌ Secretsに『GEMINI_API_KEY』を設定してください")
except Exception as e:
    st.sidebar.error(f"❌ 閃 (SOU) 起動失敗: {e}")

# --- 閃 (SOU) による精密解析関数 ---
def get_text_by_sou(img):
    if model is None:
        return "エラー: APIが正しく設定されていません。"
    
    prompt = """
    この画像は機械の検査記録（成績書）です。
    【指示】
    1. 記載されている全ての文字を正確に抽出してください。
    2. 表形式のデータは、可能な限り構造を維持してテキスト化してください。
    3. 「判定」欄にある『〇』などの印を読み取り、「合格」や「〇」として文字で表現してください。
    4. 潰れている文字や専門用語（「番号」「備考」「検査時取付」など）は文脈から推測して正しく補完してください。
    """
    try:
        response = model.generate_content([prompt, img])
        return response.text
    except Exception as e:
        return f"【閃】解析エラー: {str(e)}"

# --- テキスト抽出メイン関数 ---
def get_pdf_text_optimized(file_bytes, page_num, mode):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page = doc.load_page(page_num)
    
    # 読み取り精度向上のため、3倍の解像度で画像化
    mat = fitz.Matrix(3, 3)
    
    if mode == "閃 (AI精密解析)":
        with st.spinner("閃 (SOU) が思考中... 文脈から文字を再構築しています"):
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = get_text_by_sou(img)
    elif mode == "画像OCR (無料)":
        with st.spinner("零 (ZERO) が画像解析中..."):
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, lang='jpn+eng')
    else:
        text = page.get_text()
    
    doc.close()
    return text

# --- メイン操作パネル ---
st.sidebar.header("1. PDFアップロード")
file1 = st.sidebar.file_uploader("原本PDF", type=["pdf"], key="f1")
file2 = st.sidebar.file_uploader("比較用PDF", type=["pdf"], key="f2")

if file1 and file2:
    doc1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
    page_count = len(doc1)
    doc1.close()

    st.sidebar.divider()
    st.sidebar.header("2. 解析モード選択")
    current_page = st.sidebar.number_input("表示ページ", min_value=1, max_value=page_count, value=1) - 1
    
    analysis_mode = st.sidebar.radio(
        "解析エンジンを選択",
        ["通常 (高速・無料)", "画像OCR (無料)", "閃 (AI精密解析)"],
        help="デジタル文字が読み取れない、または誤読が多い場合は『閃』をお試しください。"
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"原本 ({current_page + 1}ページ目)")
        text1 = get_pdf_text_optimized(file1.getvalue(), current_page, analysis_mode)
        st.text_area("原本のテキスト", text1, height=400, key=f"t1_{current_page}")

    with col2:
        st.subheader(f"比較用 ({current_page + 1}ページ目)")
        text2 = get_pdf_text_optimized(file2.getvalue(), current_page, analysis_mode)
        st.text_area("比較用のテキスト", text2, height=400, key=f"t2_{current_page}")

    if st.button("このページの差異を比較"):
        diff = difflib.ndiff(text1.splitlines(), text2.splitlines())
        diff_data = [{"状態": "追加" if l.startswith('+ ') else "削除", "内容": l[2:]} 
                     for l in diff if l.startswith('+ ') or l.startswith('- ')]
        if diff_data:
            st.table(pd.DataFrame(diff_data))
        else:
            st.success("差異は見つかりませんでした。")
else:
    st.info("サイドバーからPDFをアップロードしてください。")

st.sidebar.markdown("---")
st.sidebar.caption("Project: 零 × 閃 Hybrid System")
