import streamlit as st
import fitz
import os
import urllib.request
import io
from datetime import datetime, timedelta, timezone

# ページの設定
st.set_page_config(page_title="検査室用PDF比較ツール", layout="centered")

# --- タイトルとガイド ---
st.title("📝 検査室用PDF比較ツール")
st.info("👇 2つのPDFをドロップして、下の「実行して保存」ボタンを押してください。")

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

# 日本時間（JST）を指定して取得
jst = timezone(timedelta(hours=+9), 'JST')
current_time = datetime.now(jst).strftime("%Y%m%d_%H%M")

output_name = st.text_input("保存するファイル名", value=f"検査比較結果_{current_time}")

def process_pdf(f1, f2):
    doc_orig = fitz.open(stream=f1.read(), filetype="pdf")
    doc_mod = fitz.open(stream=f2.read(), filetype="pdf")
    
    # 判定の許容範囲（100に設定：広範囲のズレに対応）
    TOL = 100 
    
    for p_no in range(max(len(doc_orig), len(doc_mod))):
        if p_no >= len(doc_mod): continue
        page_mod = doc_mod[p_no]
        
        if p_no >= len(doc_orig): continue
            
        p_orig = doc_orig[p_no]
        w_orig = p_orig.get_text("words")
        w_mod = page_mod.get_text("words")
        
        # 追加・変更の判定（赤枠）
        for wm in w_mod:
            txt_m = wm[4].strip()
            if not txt_m: continue
            if not any(txt_m == wo[4].strip() and abs(wm[0]-wo[0])<TOL and abs(wm[1]-wo[1])<TOL for wo in w_orig):
                annot = page_mod.add_rect_annot(fitz.Rect(wm[:4]))
                annot.set_colors(stroke=(1, 0, 0))
                annot.update()
                
        # 削除・変更の判定（青枠）
        for wo in w_orig:
            txt_o = wo[4].strip()
            if not txt_o: continue
            if not any(txt_o == wm[4].strip() and abs(wo[0]-wm[0])<TOL and abs(wo[1]-wm[1])<TOL for wm in w_mod):
                annot = page_mod.add_rect_annot(fitz.Rect(wo[:4]))
                annot.set_colors(stroke=(0, 0, 1))
                annot.update()
                
    out_pdf = io.BytesIO()
    doc_mod.save(out_pdf, garbage=4, deflate=True)
    return out_pdf.getvalue()

if file1 and file2:
    pdf_data = process_pdf(file1, file2)
    st.download_button(
        label="🚀 比較を実行して保存",
        data=pdf_data,
        file_name=f"{output_name}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
else:
    st.warning("⚠️ ファイルをアップロードしてください。")

# --- 設定ヘルプ ---
st.markdown("---")
with st.expander("📁 保存場所を毎回選びたい場合（設定方法）"):
    st.write("Edge/Chromeの設定 > ダウンロード > 「保存場所を確認する」をONにしてください。")

# --- 判定結果の見方 ---
st.caption("【 判定結果の見方 】")
st.markdown("""
- <span style="color:red; font-weight:bold;">■ 赤枠</span>：追加・変更
- <span style="color:blue; font-weight:bold;">■ 青枠</span>：削除（重なっている場合は赤枠が優先されることがあります）
""", unsafe_allow_html=True)

# --- 注意事項（追記版） ---
st.caption("【 注意事項 】")
st.warning("""
- 本ツールは試作品です。出力結果はあくまで「参照」とし、最終確認は必ず目視で行ってください。
- 正確な比較のため、元データと比較データの「総ページ数」を合わせてから実行してください。
- Excel等から直接保存したデジタルPDF同士であれば抽出できますが、スキャンなどの画像データでは正しく処理できません。
- 動作の不具合や改善要望がある場合は、作成担当者（石田）までご連絡ください。
""")
