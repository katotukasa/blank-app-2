import streamlit as st
import google.generativeai as genai
import os

# --- アプリケーションの基本設定 ---
st.set_page_config(
    page_title="統計分析支援チャットボット",
    page_icon="🤖",
    layout="wide",
)

st.title("📊 統計分析支援チャットボット")
st.write(
    "ようこそ！このチャットボットは、あなたがアップロードした文書（統計分析の計画など）に基づいて、統計手法の提案や質問への回答、学習のためのクイズ出題などを行います。"
)
st.write(
    "まずは、お持ちのGemini APIキーを入力し、分析計画が書かれたファイルをアップロードしてください。"
)

# --- サイドバーでのAPIキー入力 ---
with st.sidebar:
    gemini_api_key = st.text_input("Gemini API Key", type="password", key="gemini_api_key")
    "[Gemini APIキーを取得する](https://aistudio.google.com/app/apikey)"

# --- メインコンテンツ ---
if not gemini_api_key:
    st.info("サイドバーからGemini APIキーを入力してください。")
    st.stop()

# APIキーの認証
try:
    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel("gemini-pro")
except Exception as e:
    st.error(f"APIキーの認証に失敗しました。正しいキーを入力してください。: {e}")
    st.stop()

# --- プロンプト設定 ---
SYSTEM_PROMPT = """
あなたは、統計分析の専門家であり、教育者です。
ユーザーから提供された文書（研究計画や分析したいことのメモ）を深く理解し、以下の役割を担ってください。

1.  **統計手法の提案**: 文書の内容に基づき、最も適切だと思われる統計手法を複数提案し、それぞれのメリット・デメリットを分かりやすく説明します。
2.  **質問応答**: 統計学の概念、特定の手法、ツールの使い方（例：Pythonのライブラリ）など、ユーザーからのあらゆる質問に、初心者にも理解できるように丁寧に答えます。
3.  **クイズ出題**: ユーザーの学習を促進するため、会話の流れに応じて統計に関するクイズを出題します。
4.  **対話の記憶**: 過去の会話を記憶し、文脈に沿った対話を続けます。

あなたの目的は、ユーザーが自身の研究や学習において、統計分析を正しく、かつ自信を持って活用できるようになることを支援することです。
"""

# ファイルアップローダー
uploaded_file = st.file_uploader(
    "分析計画のファイル（.mdまたは.txt）をアップロードしてください",
    type=["md", "txt"]
)

if uploaded_file is not None:
    # アップロードされたファイルはセッション状態で管理
    # ファイルが変わった場合、メッセージ履歴と要約をリセット
    if "last_uploaded_filename" not in st.session_state or st.session_state.last_uploaded_filename != uploaded_file.name:
        st.session_state.last_uploaded_filename = uploaded_file.name
        st.session_state.document_content = uploaded_file.read().decode("utf-8")
        st.session_state.messages = []
        st.session_state.summary = None # ファイルが変わったら要約もリセット
        st.success(f"「{uploaded_file.name}」をアップロードしました。")

    # --- 要約機能 ---
    if st.session_state.document_content and not st.session_state.summary:
        with st.spinner("AIがドキュメントの要約を作成しています..."):
            try:
                summary_prompt = f"{SYSTEM_PROMPT}\n\n---\n\n以下のドキュメントを3〜5行で簡潔に要約してください。\n\n{st.session_state.document_content}"
                response = model.generate_content(summary_prompt)
                st.session_state.summary = response.text
            except Exception as e:
                st.error(f"要約の生成中にエラーが発生しました: {e}")

    if st.session_state.summary:
        with st.expander("アップロードされたドキュメントの要約", expanded=True):
            st.markdown(st.session_state.summary)

    # --- チャット機能 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 過去のメッセージを表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # ユーザーからの新しいメッセージ
    if prompt := st.chat_input("ファイル内容について質問してください"):
        # ユーザーのメッセージを保存して表示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AIからの応答を生成・表示
        try:
            with st.chat_message("assistant"):
                with st.spinner("AIが応答を生成中です..."):
                    # プロンプトにシステム設定、ドキュメント、会話履歴をすべて含める
                    full_prompt = (
                        f"{SYSTEM_PROMPT}\n\n"
                        f"--- 以下はアップロードされたドキュメントです ---\n"
                        f"{st.session_state.document_content}\n\n"
                        f"--- 以下はこれまでの会話履歴です ---\n"
                    )
                    for msg in st.session_state.messages:
                        full_prompt += f"{msg['role']}: {msg['content']}\n"

                    # ストリーミングで応答を生成
                    response_stream = model.generate_content(full_prompt, stream=True)
                    
                    # レスポンスを結合するための変数
                    full_response = ""
                    response_placeholder = st.empty()
                    for chunk in response_stream:
                        if chunk.text:
                            full_response += chunk.text
                            response_placeholder.markdown(full_response + " ▌")
                    response_placeholder.markdown(full_response)

            # AIの応答をセッション状態に保存
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"応答の生成中にエラーが発生しました: {e}")

else:
    st.info("ファイルをアップロードすると、チャットが開始できます。")

