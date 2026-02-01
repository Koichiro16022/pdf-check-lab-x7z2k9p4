import streamlit as st
import google.generativeai as genai

st.title("閃 (SOU) - 利用可能モデル診断")

if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        # 利用可能なモデルをリストアップ
        st.write("### 🔍 あなたのAPIキーで利用可能なモデル一覧:")
        models = genai.list_models()
        
        model_info = []
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                model_info.append({
                    "モデル名": m.name,
                    "表示名": m.display_name,
                    "説明": m.description
                })
        
        if model_info:
            st.table(model_info)
            st.success("モデルの一覧取得に成功しました。上のリストにある名前をコードに指定すれば動くはずです。")
        else:
            st.warning("生成可能なモデルが見つかりませんでした。")
            
    except Exception as e:
        st.error(f"診断中にエラーが発生しました: {e}")
        st.info("APIキーが正しくないか、支払い設定（Billing）が反映されていない可能性があります。")
else:
    st.error("SecretsにGEMINI_API_KEYが設定されていません。")
