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
st.title("零 (ZERO) × 閃 (SOU) - 現場実戦仕様・比較システム")

# --- Gemini API (閃) の設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 高精度な解析が可能な1.5-flashモデルを指定
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        st.sidebar.success("✅ 閃 (SOU) エンジン接続完了")
    else:
        st.sidebar.error("❌ Secretsに『GEMINI_API_KEY』を設定してください")
except Exception as e:
    st.sidebar.error(f"❌ 閃 (SOU) 起動失敗: {e}")

# --- 閃 (SOU) による精密解析関数（キーワード強化プロンプト） ---
def get_text_by_sou(img):
    if model is None:
        return "エラー: APIが正しく設定されていません。"
    
    # 石田様が重視する「検査時取付」や「ハンコ」を絶対に逃さないための指示
    prompt = """
    あなたは精密機器の品質管理検査員です。この検査成績書の画像を「一文字も漏らさず」スキャンしてください。
    
    【重点抽出キーワード】
    - 「検査時取付」「判定」「合格」「良」「番号」「備考」「型式」
    - 日付、ハンコ文字（山、本、'25.03.19等）、ページ番号（2/2, 1/2等）
    
    【抽出ルール】
    1. 意味の要約禁止：文書の意味を理解しようとせず、視覚的なインクの跡をすべて言語化してください。
    2. どんな小さな注釈も書き出す：表の隅にある「検査時取付」などの小さな文字を絶対に無視しないでください。
    3. 記号の可視化：丸印、チェック、手書きの追記がある場合は、[〇合] や [V良]、[山] のように [ ] で囲んで記述してください。
    4. 1項目1行：比較しやすくするため、単語や項目ごとに改行して出力してください。
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
    
    # 現場の細かい文字を拾うため、解像度を5倍(5.0)に引き上げ
    mat = fitz.Matrix(5, 5)
    
    if mode == "閃 (AI精密解析)":
        with st.spinner("閃 (SOU) が微細な文字を探索中..."):
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = get_text_by_sou(img)
    elif mode == "画像OCR (無料)":
        with st.spinner("零 (ZERO) が画像解析中..."):
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, lang='jpn+eng')
    else:
        # 通常のデジタルテキスト抽出
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
        ["通常 (高速・無料)", "画像OCR (無料)", "閃 (AI精密解析)"]
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
        st.divider()
        # 差異の検出と表示
        diff = difflib.ndiff(text1.splitlines(), text2.splitlines())
        diff_data = []
        for l in diff:
            if l.startswith('+ '):
                diff_data.append({"状態": "追加（比較用のみ）", "内容": l[2:]})
            elif l.startswith('- '):
                diff_data.append({"状態": "削除（原本のみ）", "内容": l[2:]})
        
        if diff_data:
            st.write("### 検出された差異リスト")
            st.table(pd.DataFrame(diff_data))
        else:
            st.error("テキストレベルでの差異は見つかりませんでした。")
            st.info("左右のテキストエリアを目視し、AIが重要な単語を読み飛ばしていないか確認してください。")
else:
    st.info("サイドバーからPDFをアップロードしてください。")

st.sidebar.markdown("---")
st.sidebar.caption("Project: 零 × 閃 Field-Ready Edition")
