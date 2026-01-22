import streamlit as st
import fitz
import os
import urllib.request
import io
from datetime import datetime

# ページの設定
st.set_page_config(page_title="検査室用PDF比較ツール", layout="centered")

# --- タイトルとガイド ---
st.title("📝 検査室用PDF比較ツール")
st.info("👇 設定により「保存先」を選べます。詳細は下の【保存先の設定方法】を確認してください。")

# フォントの準備
font_path = "NotoSansCJKjp-Regular.otf"
@st.cache_resource
def load_font():
    if not os.path.exists(font_path):
        font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"
        urllib.request.urlretrieve(font_url, font_path)
    return font_path

f_path = load_font()

# --- 1. 読み込みエリア ---
st.subheader("1. 検査データの読み込み")
file1 = st.file_uploader("【元データ（旧）】をここにドロップ", type="pdf")
file2 = st.file_uploader("【修正後（新）】をここにドロップ", type="pdf")

st.markdown("---")

# --- 2. 実行エリア ---
st.subheader("2. 実行と保存")

# 日時を自動取得してデフォルトのファイル名に含める（例：検査比較結果_20240122_1530）
current_time = datetime.now().strftime("%Y%m%d_%H%M")
output_name = st.text_input("保存するファイル名", value=f"検査比較結果_{current_time}")

def process_pdf(f1, f2):
    doc_orig = fitz.open(stream=f1.read(), filetype="pdf")
    doc_mod = fitz.open(stream=f2.read(), filetype="pdf")
    X_TOL, Y_TOL = 15, 15
    for p_no in range(max(len(doc_orig), len(doc_mod))):
        if p_no >= len(doc_mod): continue
        page_mod = doc_mod[p_no]
        rect = page_mod.rect
        if p_no >= len(doc_orig):
            warning_msg = "【 未確認 】\n\nページ不一致：\n元データに該当するページがありません。"
            center_rect = fitz.Rect(rect.width * 0.1, rect.height * 0.3, rect.width * 0.9, rect.height * 0.7)
            page_mod.insert_textbox(center_rect, warning_msg, fontsize=30, fontfile=f_path, fontname="jp-g", color=(1, 0, 0), align=fitz.TEXT_ALIGN_CENTER)
            inset_rect = fitz.Rect(5, 5, rect.width - 5, rect.height - 5)
            page_mod.add_rect_annot(inset_rect).set_colors(stroke=(1, 0, 0)).set_border(width=8).update()
            continue
        p_orig = doc_orig[p_no]
        w_orig = p_orig.get_text("words")
        w_mod = page_mod.get_text("words")
        for wm in w_mod:
            txt_m = wm[4].strip()
            if not txt_m: continue
            if not any(txt_m == wo[4].strip() and abs(wm[0]-wo[0])<X_TOL and abs(wm[1]-wo[1])<Y_TOL for wo in w_orig):
                page_mod.add_rect_annot(fitz.Rect(wm[:4])).set_colors(stroke=(1, 0, 0)).update()
        for wo in w_orig:
            txt_o = wo[4].strip()
            if not txt_o: continue
            if not any(abs(wo[0]-wm[0])<X_TOL and abs(wo[1]-wm[1])<Y_TOL for wm in w_mod):
                page_mod.add_rect_annot(fitz.Rect(wo[:4])).set_colors(stroke=(0, 0, 1)).update()
    out_pdf = io.BytesIO()
    doc_mod.save(out_pdf, garbage=4, deflate=True)
    return out_pdf.getvalue()

if file1 and file2:
    st.download_button(
        label="🚀 比較を実行して保存先を選択",
        data=process_pdf(file1, file2),
        file_name=f"{output_name}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
else:
    st.warning("⚠️ ファイルをアップロードしてください。")

# --- 案内と注意書き ---
st.markdown("---")
with st.expander("📁 保存場所を毎回選びたい場合（設定方法）"):
    st.write("""
    ブラウザの設定を変更することで、保存先フォルダを毎回選択できるようになります。
    - **Edgeの場合**: 設定 > ダウンロード > 「ダウンロード時の動作を毎回確認する」をON
    - **Chromeの場合**: 設定 > ダウンロード > 「ダウンロード前に各ファイルの保存場所を確認する」をON
    """)

st.caption("【 判定結果の見方 】")
st.markdown("""
- <span style="color:red; font-weight:bold;">■ 赤枠</span>：修正後（新）で **追加・変更** された項目
- <span style="color:blue; font-weight:bold;">■ 青枠</span>：元データ（旧）から **削除** された項目
""", unsafe_allow_html=True)

st.caption("【 注意事項 】")
st.warning("本ツールは試作品です。出力結果は参照とし、不具合は石田まで連絡してください。")
