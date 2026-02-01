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
st.title("零 (ZERO) × 閃 (SOU) - 超・厳密比較システム")

# --- Gemini API (閃) の設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        st.sidebar.success("✅ 閃 (SOU) エンジン接続完了")
    else:
        st.sidebar.error("❌ Secretsに『GEMINI_API_KEY』を設定してください")
except Exception as e:
    st.sidebar.error(f"❌ 閃 (SOU) 起動失敗: {e}")

# --- 閃 (SOU) による精密解析関数（「意味」を排除する超厳密プロンプト） ---
def get_text_by_sou(img):
    if model is None:
        return "エラー: APIが正しく設定されていません。"
    
    # AIに「賢く振る舞うな」と強く命じ、物理的な文字羅列のみを出力させる
    prompt = """
    あなたは超精密な文字読み取り専用機です。文章の意味を理解しようとせず、画像内の視覚的な「事実」のみを報告してください。
    
    【厳守ルール】
    1. 1文字の漏れも許さない：ページ番号（1/2, 2/2）、日付（2025.03.18）、スタンプ内の小さな文字（山、本）、手書きの数字、これらを全て「見たまま」書き出してください。
    2. 記号の徹底可視化：丸印、チェック、斜線、塗りつぶしがある場所は、必ず [〇] [V] [/] のように記号化して記述してください。
    3. 構造を無視：表を綺麗に整える必要はありません。左上から右下へ、スキャンした順に、1単語ごとに「改行」して出力してください。
    4. 補完禁止：かすれている文字を、前後の文脈から「こうだろう」と判断して書き換えることは絶対に禁止します。
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
    
    # 精度最大化のため、解像度をさらに上げる(4倍)
    mat = fitz.Matrix(4, 4)
    
    if mode == "閃 (AI精密解析)":
        with st.spinner("閃 (SOU) が「事実」のみをスキャン中..."):
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

# --- 操作パネル ---
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
        # 差異検出（空白や改行の差を無視しない厳密比較）
        d = difflib.HtmlDiff()
        diff_html = d.make_table(text1.splitlines(), text2.splitlines(), context=True, numlines=2)
        
        # 簡易表示版も併記
        diff = difflib.ndiff(text1.splitlines(), text2.splitlines())
        diff_data = [{"状態": "追加" if l.startswith('+ ') else "削除", "内容": l[2:]} 
                     for l in diff if l.startswith('+ ') or l.startswith('- ')]
        
        if diff_data:
            st.write("### 検出された差異リスト")
            st.table(pd.DataFrame(diff_data))
        else:
            st.error("【警告】テキスト上では差異が検出されませんでした。AIが内容を同一とみなした可能性があります。")
            st.info("左右のテキストエリアの文字を目視で比較し、AIの読み飛ばしがないか確認してください。")

else:
    st.info("サイドバーからPDFをアップロードしてください。")

st.sidebar.markdown("---")
st.sidebar.caption("Project: 零 × 閃 Ultra Strict")
