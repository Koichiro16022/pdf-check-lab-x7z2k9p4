import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Hybrid", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 現場実戦仕様・比較")

# --- Gemini API (閃) の設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        # 診断結果に基づき、確実に存在する「gemini-2.5-flash」を指定
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        st.sidebar.success("✅ 閃 (SOU) エンジン接続完了")
    else:
        st.sidebar.error("❌ SecretsにGEMINI_API_KEYを設定してください")
except Exception as e:
    st.sidebar.error(f"❌ 閃 (SOU) 起動失敗: {e}")

# --- 2枚の画像を「間違い探し」する関数 ---
def compare_images_by_sou(img1, img2):
    if model is None:
        return "エラー: APIが正しく設定されていません。"
    
    # 現場の微細な違いを炙り出すための専用プロンプト
    prompt = """
    あなたは超精密な「間違い探し」の専門家です。
    提供された2枚の画像（原本と比較用）を比較し、微細な違いを全てリストアップしてください。

    【重点チェック項目】
    1. 文字の有無：「検査時取付」「山」「本」「'25.03.19」など。
    2. 数字の違い：日付やページ番号（2/2 vs 1/2）。
    3. 記号：[〇] や [V] のチェックの有無。

    【出力形式】
    「原本：〇〇 」「比較用：××」の形式で、見つけた違いを箇条書きで全て報告してください。
    """
    try:
        # 最新の2.5モデルで画像比較を実行
        response = model.generate_content([prompt, img1, img2])
        return response.text
    except Exception as e:
        return f"解析エラーが発生しました。詳細: {str(e)}"

# --- 操作パネル ---
st.sidebar.header("1. PDFアップロード")
file1 = st.sidebar.file_uploader("原本PDF", type=["pdf"], key="f1")
file2 = st.sidebar.file_uploader("比較用PDF", type=["pdf"], key="f2")

if file1 and file2:
    # ページ数確認
    d1_temp = fitz.open(stream=file1.getvalue(), filetype="pdf")
    page_count = len(d1_temp)
    d1_temp.close()

    st.sidebar.divider()
    st.sidebar.header("2. ページ選択")
    current_page = st.sidebar.number_input("比較するページ", min_value=1, max_value=page_count, value=1) - 1

    if st.button("閃 (SOU) で精密比較を実行"):
        with st.spinner("閃 (SOU) Gemini 2.5 が精密スキャン中..."):
            doc1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
            doc2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
            
            p1 = doc1.load_page(current_page)
            p2 = doc2.load_page(current_page)
            
            # 高解像度(5倍)で画像化
            mat = fitz.Matrix(5, 5)
            pix1 = p1.get_pixmap(matrix=mat)
            pix2 = p2.get_pixmap(matrix=mat)
            
            img1 = Image.open(io.BytesIO(pix1.tobytes("png")))
            img2 = Image.open(io.BytesIO(pix2.tobytes("png")))
            
            # 閃による直接比較
            report = compare_images_by_sou(img1, img2)
            
            st.divider()
            st.subheader("🔍 閃 (SOU) による差異レポート")
            st.write(report)
            
            # プレビュー
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.image(img1, caption="原本 (プレビュー)")
            with col2:
                st.image(img2, caption="比較用 (プレビュー)")
            
            doc1.close()
            doc2.close()
else:
    st.info("サイドバーからPDFをアップロードしてください。")

st.sidebar.markdown("---")
st.sidebar.caption("Project: 零 × 閃 Gemini 2.5 Edition")
