import streamlit as st
import fitz
import os
import urllib.request
import io
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="検査室用PDF比較ツール", layout="centered")

st.title("📝 検査室用PDF比較ツール")
st.info("👇 2つのPDFをドロップして、下の「実行して保存」ボタンを押してください。")

font_path = "NotoSansCJKjp-Regular.otf"
@st.cache_resource
def load_font():
    if not os.path.exists(font_path):
        font_url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf"
        urllib.request.urlretrieve(font_url, font_path)
    return font_path
f_path = load_font()

st.subheader("1. 検査データの読み込み")
file1 = st.file_uploader("【元データ（旧）】をここにドロップ", type="pdf")
file2 = st.file_uploader("【修正後（新）】をここにドロップ", type="pdf")

st.markdown("---")
st.subheader("2. 実行と保存")

jst = timezone(timedelta(hours=+9), 'JST')
current_time = datetime.now(jst).strftime("%Y%m%d_%H%M")
output_name = st.text_input("保存するファイル名", value=f"検査比較結果_{current_time}")

def get_text_blocks(page):
    """
    ページからテキスト情報を取得する関数。
    空白のみのブロックを除外してリスト化します。
    """
    blocks = []
    for b in page.get_text("words"):
        txt = b[4].strip()
        if txt and len(txt) > 0:
            blocks.append(b)
    return blocks

def process_pdf(f1, f2):
    doc_orig = fitz.open(stream=f1.read(), filetype="pdf")
    doc_mod = fitz.open(stream=f2.read(), filetype="pdf")
    
    # 判定の許容範囲（非常に広い80に設定してみます）
    X_TOL, Y_TOL = 80, 80 
    
    for p_no in range(max(len(doc_orig), len(doc_mod))):
        if p_no >= len(doc_mod): continue
        page_mod = doc_mod[p_no]
        
        if p_no >= len(doc_orig):
            # ページ不足警告（省略）
            continue
            
        p_orig = doc_orig[p_no]
        w_orig = get_text_blocks(p_orig)
        w_mod = get_text_blocks(page_mod)
        
        # 【追加の判定（赤枠）】
        for wm in w_mod:
            txt_m = wm[4].strip()
            # 修正後の文字が元のPDFの同じ場所に「文字として存在するか」を厳密にチェック
            found = False
            for wo in w_orig:
                if txt_m == wo[4].strip() and abs(wm[0]-wo[0])<X_TOL and abs(wm[1]-wo[1])<Y_TOL:
                    found = True
                    break
            if not found:
                annot = page_mod.add_rect_annot(fitz.Rect(wm[:4]))
                annot.set_colors(stroke=(1, 0, 0))
                annot.update()
                
        # 【削除の判定（青枠）】改良版
        for wo in w_orig:
            txt_o = wo[4].strip()
            # 元の文字が修正後のPDFの同じ場所に「何らかの可視文字」として存在するかチェック
            found_anything = False
            for wm in w_mod:
                # 座標が近くにあり、かつ何らかの文字データがあるか
                if abs(wo[0]-wm[0])<X_TOL and abs(wo[1]-wm[1])<Y_TOL:
                    found_anything = True
                    break
            if not found_anything:
                # 何も見つからない場合のみ青枠
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

st.markdown("---")
st.caption("【 判定結果の見方 】")
st.markdown("- <span style='color:red; font-weight:bold;'>■ 赤枠</span>：追加・変更 / <span style='color:blue; font-weight:bold;'>■ 青枠</span>：削除", unsafe_allow_html=True)
st.caption("【 注意事項 】")
st.warning("""
- 本ツールは試作品です。出力結果はあくまで「参照」とし、最終確認は必ず目視で行ってください。
- 正確な比較のため、元データと比較データの「総ページ数」を合わせてから実行してください。
- 動作の不具合や改善要望がある場合は、作成担当者（石田）までご連絡ください。
""")
