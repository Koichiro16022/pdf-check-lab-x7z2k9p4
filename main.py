import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import io
from PIL import Image, ImageEnhance

# --- ページ設定 ---
st.set_page_config(page_title="零・閃 Precision Final", layout="wide")
st.title("零 (ZERO) × 閃 (SOU) - 座標判定 × 文脈読解")

# --- Gemini API 設定 ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 最新の2.5-flashを使用
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        st.sidebar.success("✅ 閃 (SOU) 2.5 接続完了")
except Exception as e:
    st.sidebar.error(f"❌ 接続失敗: {e}")

def get_guided_scan(img1, img2):
    # 座標の厳格さと、文字の読み替え（柔軟性）を両立させるプロンプト
    prompt = """
    あなたは品質管理のベテラン検査員です。画像内の「判定」と「追記文字」を、実務レベルで読み取ってください。

    【絶対判定ルール：判定印】
    1. 座標の維持：前回成功した「左＝合、右＝否」のロジックを継続してください。記号（〇やレ点）の中心が「合」の文字の上にあれば、迷わず「合」と判定してください。
    2. 記号の呼び方：画像にある印は「レ点」や「〇」など見たままを認識しつつ、結論として「合」か「否」かを明記してください。

    【重要ルール：注釈文字の救い上げ】
    3. 誤読の修正：あなたは前回「検査時取付」を「出荷時取付」と読み間違えました。この書類の文脈では「検査時取付」が正解です。字が潰れて「出荷」や「横査」に見えても、それは「検査時取付」と読み替えて報告してください。
    4. 極小文字の捕捉：備考欄や項目名の周辺にある、手書きや追加の極小文字を一つ残らず抽出してください。

    【出力形式】
    ・項目名：[判定結果] (理由: 記号が「合」の真上にあるため)
    ・追記情報：見つかった注釈（「検査時取付」など）と、その位置
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

        if st.button("閃 (SOU) で最終スキャンを実行"):
            with st.spinner("座標判定と文脈読解を組み合わせて解析中..."):
                d1 = fitz.open(stream=file1.getvalue(), filetype="pdf")
                d2 = fitz.open(stream=file2.getvalue(), filetype="pdf")
                p1 = d1.load_page(current_page)
                p2 = d2.load_page(current_page)
                
                # 精度を維持するため解像度を7倍に設定
                mat = fitz.Matrix(7, 7)
                pix1 = p1.get_pixmap(matrix=mat)
                pix2 = p2.get_pixmap(matrix=mat)
                
                img1 = Image.open(io.BytesIO(pix1.tobytes("png")))
                img2 = Image.open(io.BytesIO(pix2.tobytes("png")))
                
                # 画像のコントラストを最適化
                img2 = ImageEnhance.Contrast(img2).enhance(2.5)
                
                report = get_guided_scan(img1, img2)
                
                st.divider()
                st.subheader("🔍 最終差異レポート（座標×文脈）")
                st.write(report)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.image(img1, caption="原本")
                with col2:
                    st.image(img2, caption="比較用（解析対象）")
                
                d1.close()
                d2.close()
else:
    st.info("左側のサイドバーでAPIキーを確認してください。")
