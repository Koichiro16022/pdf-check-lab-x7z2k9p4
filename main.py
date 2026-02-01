import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Hybrid", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 究極・画像直接比較")

# --- Gemini API (閃) の設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # モデル名を最も標準的な形式に変更してエラーを回避
        model = genai.GenerativeModel('gemini-1.5-flash')
        st.sidebar.success("✅ 閃 (SOU) エンジン接続完了")
    else:
        st.sidebar.error("❌ Secretsにキーを設定してください")
except Exception as e:
    st.sidebar.error(f"❌ 閃 (SOU) 起動失敗: {e}")

# --- 2枚の画像を「間違い探し」する関数 ---
def compare_images_by_sou(img1, img2):
    if model is None:
        return "エラー: APIが正しく設定されていません。"
    
    # 意味の要約を禁止し、物理的な「間違い探し」に特化させた指示
    prompt = """
    あなたは超精密な「間違い探し」の専門家です。
    提供された2枚の画像（1枚目が原本、2枚目が比較用）を比較し、微細な違いを全てリストアップしてください。

    【重点チェック項目】
    1. 文字の有無：「検査時取付」「山」「本」「'25.03.19」など、片方にしかない文字。
    2. 数字の違い：日付（2025.03.18等）やページ番号（2/2 vs 1/2）の違い。
    3. 記号：[〇] や [V] のチェックがあるかないか。

    【出力形式】
    ・原本：〇〇 
    ・比較用：××
    という形式で、見つけた違いを箇条書きで全て報告してください。
    """
    try:
        # 2枚の画像をリスト形式で渡して直接比較させます
        response = model.generate_content([prompt, img1, img2])
        return response.text
    except Exception as e:
        return f"解析エラーが発生しました: {str(e)}"

# --- サイドバー：操作パネル ---
st.sidebar.header("1. PDFアップロード")
file1 = st.sidebar.file_uploader("原本PDF", type=["pdf"], key="f1")
file2 = st.sidebar.file_uploader("比較用PDF", type=["pdf"], key="f2")

if file1 and file2:
    doc1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
    page_count = len(doc1)
    doc1.close()

    st.sidebar.divider()
    st.sidebar.header("2. ページ選択")
    current_page = st.sidebar.number_input("比較するページ", min_value=1, max_value=page_count, value=1) - 1

    if st.button("閃 (SOU) で精密比較を実行"):
        with st.spinner("閃 (SOU) が2枚の画像を並べて「間違い探し」をしています..."):
            # ページを画像化
            d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
            d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
            p1 = d1.load_page(current_page)
            p2 = d2.load_page(current_page)
            
            # 高解像度(4倍)で画像化
            mat = fitz.Matrix(4, 4)
            pix1 = p1.get_pixmap(matrix=mat)
            pix2 = p2.get_pixmap(matrix=mat)
            
            img1 = Image.open(io.BytesIO(pix1.tobytes("png")))
            img2 = Image.open(io.BytesIO(pix2.tobytes("png")))
            
            # 閃による直接比較
            report = compare_images_by_sou(img1, img2)
            
            st.divider()
            st.subheader("🔍 閃 (SOU) による差異レポート")
            st.info("AIが画像を直接見て、人間のように違いを書き出した結果です。")
            st.write(report)
            
            # プレビュー
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.image(img1, caption="原本 (プレビュー)")
            with col2:
                st.image(img2, caption="比較用 (プレビュー)")
            
            d1.close()
            d2.close()
else:
    st.info("サイドバーからPDFをアップロードしてください。")

st.sidebar.markdown("---")
st.sidebar.caption("Project: 零 × 閃 Visual Compare")
