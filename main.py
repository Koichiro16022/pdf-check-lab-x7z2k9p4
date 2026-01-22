import streamlit as st
import fitz
import os
import urllib.request
import io

# ページの設定
st.set_page_config(page_title="検査室用PDF比較ツール", layout="centered")

# --- タイトルとガイド ---
st.title("📝 検査室用PDF比較ツール")
st.info("👇 比較したい2つのPDFファイルを、下の枠内にドラッグ＆ドロップしてください。")

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

# --- 2. 比較実行エリア ---
st.subheader("2. 比較実行")
output_name = st.text_input("保存するファイル名", value="検査比較結果")

if st.button("🚀 比較を実行する"):
    if file1 and file2:
        with st.spinner("解析中です。検査データを照合しています..."):
            doc_orig = fitz.open(stream=file1.read(), filetype="pdf")
            doc_mod = fitz.open(stream=file2.read(), filetype="pdf")
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
                    annot = page_mod.add_rect_annot(inset_rect)
                    annot.set_colors(stroke=(1, 0, 0))
                    annot.set_border(width=8)
                    annot.update()
                    continue

                p_orig = doc_orig[p_no]
                w_orig = p_orig.get_text("words")
                w_mod = page_mod.get_text("words")

                # 追加・変更箇所（赤枠）
                for wm in w_mod:
                    txt_m = wm[4].strip()
                    if not txt_m: continue
                    if not any(txt_m == wo[4].strip() and abs(wm[0]-wo[0])<X_TOL and abs(wm[1]-wo[1])<Y_TOL for wo in w_orig):
                        annot = page_mod.add_rect_annot(fitz.Rect(wm[:4]))
                        annot.set_colors(stroke=(1, 0, 0))
                        annot.update()

                # 削除箇所（青枠）
                for wo in w_orig:
                    txt_o = wo[4].strip()
                    if not txt_o: continue
                    if not any(abs(wo[0]-wm[0])<X_TOL and abs(wo[1]-wm[1])<Y_TOL for wm in w_mod):
                        annot = page_mod.add_rect_annot(fitz.Rect(wo[:4]))
                        annot.set_colors(stroke=(0, 0, 1))
                        annot.update()
            
            out_pdf = io.BytesIO()
            doc_mod.save(out_pdf, garbage=4, deflate=True)
            st.success("照合が完了しました！")
            st.download_button(label="📥 比較結果をダウンロード", data=out_pdf.getvalue(), file_name=f"{output_name}.pdf", mime="application/pdf")
    else:
        st.warning("⚠️ 比較を始めるには、2つのファイルを両方アップロードしてください。")

# --- 注意書き（凡例を追記） ---
st.markdown("---")
st.caption("【 判定結果の見方 】")
st.markdown("""
- <span style="color:red; font-weight:bold;">■ 赤枠</span>：修正後（新）で **追加・変更** された項目
- <span style="color:blue; font-weight:bold;">■ 青枠</span>：元データ（旧）から **削除** された項目
""", unsafe_allow_html=True)

st.caption("【 注意事項 】")
st.warning("""
- 本ツールは試作品です。出力結果はあくまで「参照」とし、最終確認は必ず目視で行ってください。
- 正確な比較のため、元データと比較データの「総ページ数」を合わせてから実行してください。
- 動作の不具合や改善要望がある場合は、作成担当者（石田）までご連絡ください。
""")
