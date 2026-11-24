"""Run with: python -m streamlit run app.py"""
import streamlit as st
from chatbot import DatasetError, SupermarketChatbot, WELCOME

st.set_page_config(page_title="Supermarket Shopping Assistant", page_icon="🛒", layout="centered")
st.title("🛒 Supermarket Shopping Assistant")
st.caption("Your local shopping helper · Demonstration data · Prices in INR")
try:
    bot = SupermarketChatbot()
except DatasetError as exc:
    st.error(str(exc))
    st.info("Check products.csv, correct its data, and reload the app.")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELCOME}]
if "context" not in st.session_state:
    st.session_state.context = {}

with st.sidebar:
    st.header("Browse the aisles")
    st.caption("Available categories")
    for category in bot.categories:
        st.write("• " + category)
    st.divider()
    st.caption("Sample inventory for demonstration; stock and offers are not live.")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = [{"role": "assistant", "content": WELCOME}]
        st.session_state.context = {}
        st.rerun()

actions = {
    "Check Availability": "Check availability",
    "Today's Offers": "What are the current offers?",
    "Browse Categories": "What categories are available?",
    "Products Under ₹100": "Show me products under ₹100",
}
chosen = None
columns = st.columns(2)
for index, (label, prompt) in enumerate(actions.items()):
    if columns[index % 2].button(label, use_container_width=True):
        chosen = prompt

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask about a product, offer, category, or budget…")
if chosen or prompt:
    question = chosen or prompt
    response = bot.reply(question, st.session_state.context)
    st.session_state.messages.extend([
        {"role": "user", "content": question},
        {"role": "assistant", "content": response},
    ])
    st.rerun()
