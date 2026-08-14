import random

import chromadb
import streamlit as st
from groq import Groq
import os
from pypdf import PdfReader
from dotenv import load_dotenv
import time
from datetime import date, timedelta
import calendar

# API_KEY = os.getenv("GROQ_API_KEY")

API_KEY = None

try:
    API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

if not API_KEY:
    load_dotenv()
    API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    st.error("GROQ_API_KEY가 설정되지 않았어요. .env 파일이나 secrets.toml을 확인해주세요.")

MODEL = "llama-3.1-8b-instant"
client = Groq(api_key=API_KEY)

st.set_page_config(page_title="Apps", page_icon="📄")


def pageButtons():
    if st.button("Summarizer", use_container_width=True):
        st.session_state.page = 2
        st.rerun()
    if st.button("AI Chatbot", use_container_width=True):
        st.session_state.page = 3
        st.rerun()
    if st.button("Jackpot", use_container_width=True):
        st.session_state.page = 4
        st.rerun()
    if st.button("Baseball game", use_container_width=True):
        st.session_state.page = 5
        st.rerun()


with st.sidebar:
    if st.button("Go to main screen", use_container_width=True):
        st.session_state.page = 1
        st.rerun()
    pageButtons()


#extract text from file
def extract_text(file):
    if file.name.endswith(".pdf"):
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    else:
        return file.read().decode("utf-8")


#summarize
def summarize_text(text, length_option):
    client = Groq(api_key=API_KEY)

    length_instructions = {
        "Short": "Summarize this in exactly 3 concise bullet points.",
        "Medium": "Summarize this in one clear paragraph (4-6 sentences).",
        "Long": "Provide a detailed summary covering all key points, organized with headers if helpful."
    }

    instruction = length_instructions[length_option]

    prompt = f"""{instruction}

    Text to summarize:
    {text[:12000]}
    """

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


if "page" not in st.session_state:
    st.session_state.page = 2

#main page - select
if st.session_state.page == 1:
    st.title("App")
    pageButtons()

#summarizer
if st.session_state.page == 2:
    st.title("Summarizer")
    st.caption("Upload a file and the AI will summarize it for you.")

    # upload
    uploaded_file = st.file_uploader(
        "Upload a .txt or .pdf file",
        type=["txt", "pdf"]
    )

    typed_text = st.text_area("Type the text you want to summarize here")

    if uploaded_file is not None or typed_text.strip() != "":
        if uploaded_file is not None:
            st.success(f"'{uploaded_file.name}' Uploaded Successfully")

        length_option = st.radio(
            "Choose the summary length",
            ["Short", "Medium", "Long"],
            horizontal=True
        )

        if st.button("Summarize", use_container_width=True):
            with st.spinner("Summarizing..."):
                if uploaded_file is not None:
                    extracted_text = extract_text(uploaded_file)
                else:
                    extracted_text = typed_text

                if len(extracted_text.strip()) == 0:
                    st.warning("Use another file.")
                else:
                    summary = summarize_text(extracted_text, length_option)
                    st.session_state.summary = summary
                    st.session_state.original_length = len(extracted_text)

        # result
        if "summary" in st.session_state:
            st.divider()
            st.subheader("Summary")
            st.write(st.session_state.summary)

            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"Length of Original: {st.session_state.original_length} characters")
            with col2:
                st.caption(f"Length of Summary: {len(st.session_state.summary)} characters")

            st.download_button(
                label="Download (.txt)",
                data=st.session_state.summary,
                file_name = f"summary_{uploaded_file.name}.txt" if uploaded_file else "summary.txt",
                #mime="text/plain",
                #use_container_width=True
            )

        st.write("___________________________________")

        if st.button("Process File to Ask a Question"):
            if uploaded_file is not None:
                text = extract_text(uploaded_file)
                file_label = uploaded_file.name  #파일이면 실제 이름 사용
            else:
                text = typed_text
                file_label = "typed_text"  #타이핑한 텍스트면 그냥 임의의 이름

            chunks = []
            chunk_size = 300
            overlap = 100
            step = chunk_size - overlap
            for i in range(0, len(text), step):
                chunks.append(text[i: i + chunk_size])

            chroma_client = chromadb.Client()
            collection = chroma_client.get_or_create_collection("documents")
            tags = [file_label + str(i) for i in range(len(chunks))]  # file.name → file_label
            collection.add(documents=chunks, ids=tags)

            st.session_state.collection = collection
            st.write("Chunks added to knowledge base!")

        question = st.text_input("Ask a question about the file or text")
        st.session_state.question = question

        if "collection" in st.session_state and question.strip() != "":
            result = st.session_state.collection.query(query_texts=[question], n_results=10)
            st.session_state.context = result["documents"][0]

        if st.button("LLM answer"):
            if "context" not in st.session_state:
                st.warning("Please process a file and ask a question first.")
            else:
                st.write("contacting LLM...")

                context = "\n".join(st.session_state.context)
                question = st.session_state.question

                messages = [
                    {"role": "system",
                     "content": "Answer the user's question using only the provided document context. If the context contains enough information to answer, give the answer."},
                    {"role": "user", "content": f"DOCUMENT CONTEXT:\n{context}\n\nQUESTION:\n{question}"}
                ]

                response = client.chat.completions.create(model=MODEL, messages=messages)
                st.write("LLM Answer:", response.choices[0].message.content)

    else:
        st.info("Upload a file or enter your text first.")


#AI chatbot
if st.session_state.page == 3:
    st.title("AI Chatbot")
    st.caption("Chat with Groq AI!")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "What would you like to do?"}]

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            response = client.chat.completions.create(model=MODEL, messages=st.session_state.messages)

            assistant_response = response.choices[0].message.content
            # Simulate stream of response with milliseconds delay
            for chunk in assistant_response.split():
                full_response += chunk + " "
                time.sleep(0.05)
                # Add a blinking cursor to simulate typing
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})

if st.session_state.page == 4:
    st.title("Jackpot")
    st.caption("Push the button to roll!")

    minDice = 1
    maxDice = 9

    if "earned_badges" not in st.session_state:
        st.session_state.earned_badges = set()

    if st.button("Roll"):

        roll1 = random.randint(minDice, maxDice)
        roll2 = random.randint(minDice, maxDice)
        roll3 = random.randint(minDice, maxDice)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<h1 style='text-align: center; font-size: 80px;'>{roll1}</h1>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<h1 style='text-align: center; font-size: 80px;'>{roll2}</h1>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<h1 style='text-align: center; font-size: 80px;'>{roll3}</h1>", unsafe_allow_html=True)

        new_badge = None
        badge_color = None

        if (roll1 == roll2 == roll3 == 7):
            new_badge = "Jackpot"
            badge_color = "red"
            st.snow()
        elif [roll1, roll2, roll3].count(7) == 2:
            new_badge = "Double Seven"
            badge_color = "orange"
            st.balloons()
        elif (roll1 == 7 or roll2 == 7 or roll3 == 7):
            new_badge = "7"
            badge_color = "yellow"
            st.balloons()
        if (roll1 + 1 == roll2 and roll2 + 1 == roll3):
            new_badge = str(roll1 * 100 + roll2 * 10 + roll3)
            badge_color = "green"
            st.balloons()
        if (roll1 == roll2 == roll3):
            new_badge = str(roll1 * 100 + roll2 * 10 + roll3)
            badge_color = "violet"
            st.balloons()
        # elif (roll1 == roll2 or roll2 == roll3 or roll1 == roll3):
        #     new_badge = str(roll1 * 100 + roll2 * 10 + roll3)
        #     badge_color = "yellow"

        elif (roll1 == 3 and roll2 == 6 and roll3 == 9):
            new_badge = "369"
            badge_color = "green"
            st.balloons()


        if new_badge is not None:
            if new_badge not in st.session_state.earned_badges:
                st.session_state.earned_badges.add(new_badge)
                st.success(f"New badge earned: {new_badge}!")
                st.balloons()
            else:
                st.info(f"Badge already earned: {new_badge}!")

    st.divider()
    st.subheader("Your Badges")
    st.caption("Roll a special number to earn a badge!")
    if len(st.session_state.earned_badges) == 0:
        st.write("No badges yet")
    else:
        for badge in st.session_state.earned_badges:
            st.badge(badge, color="violet")

#baseball game
if st.session_state.page == 5:
    st.title("Baseball Game")

    if st.button("Rules"):
        st.session_state.page = 6
        st.rerun()

    st.caption("Match the random 3 number combination! (0~9)")

    def new_game():
        digits = random.sample(range(1, 10), 3)  # 서로 다른 숫자 3개 뽑기
        st.session_state.answer = digits
        st.session_state.history = []  # [(guess, strike, ball), ...]
        st.session_state.game_over = False
        st.session_state.tries = 0

    def check_guess(guess_digits, answer_digits):
        strike = 0
        ball = 0
        for i in range(3):
            if guess_digits[i] == answer_digits[i]:
                strike += 1
            elif guess_digits[i] in answer_digits:
                ball += 1
        return strike, ball

    if "answer" not in st.session_state:
        new_game()

    if st.button("New Game", use_container_width=True):
        new_game()
        st.rerun()
    st.caption(f"Number of Tries: {st.session_state.tries}")

    if not st.session_state.game_over:
        if "current_guess" not in st.session_state:
            st.session_state.current_guess = ""

        st.write("Enter a 3-number combination (e.g.: 123)")

        display = st.session_state.current_guess.ljust(3, "_")
        st.markdown(f"<h2 style='text-align:center; letter-spacing: 10px;'>{display}</h2>", unsafe_allow_html=True)

        st.write("")
        cols = st.columns(3)
        numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9]

        for i, num in enumerate(numbers):
            with cols[i % 3]:
                if st.button(str(num), key=f"num_{num}", use_container_width=True):
                    if len(st.session_state.current_guess) < 3 and str(num) not in st.session_state.current_guess:
                        st.session_state.current_guess += str(num)
                        st.rerun()

        col_clear, col_submit = st.columns(2)
        with col_clear:
            if st.button("Clear", use_container_width=True):
                st.session_state.current_guess = ""
                st.rerun()

        with col_submit:
            if st.button("Guess", use_container_width=True):
                guess_input = st.session_state.current_guess
                if len(guess_input) != 3:
                    st.warning("Enter 3 numbers")
                else:
                    guess_digits = [int(d) for d in guess_input]
                    strike, ball = check_guess(guess_digits, st.session_state.answer)
                    st.session_state.tries += 1
                    st.session_state.history.append((guess_input, strike, ball))

                    if strike == 3:
                        st.session_state.game_over = True
                        st.session_state.won = True

                    st.session_state.current_guess = ""
                    st.rerun()

    # result
    if st.session_state.game_over:
        answer_str = "".join(str(d) for d in st.session_state.answer)
        st.success(f"Correct! The answer was '{answer_str}' You have guess it in {st.session_state.tries} tries!")
        st.balloons()

        if st.button("Try Again", use_container_width=True):
            new_game()
            st.rerun()

    #tries
    st.divider()
    st.subheader("Tries")

    if len(st.session_state.history) == 0:
        st.write("No tries yet")
    else:
        for i, (guess, strike, ball) in enumerate(reversed(st.session_state.history), 1):
            attempt_num = len(st.session_state.history) - i + 1
            out = 3 - strike - ball
            c1, c2, c3, c4 = st.columns([1, 2, 2, 2])
            with c1:
                st.write(f"**{guess}**")
            with c2:
                st.write(f"{strike} Strike")
            with c3:
                st.write(f"{ball} Ball")
            with c4:
                st.write(f"{out} Out")

if st.session_state.page == 6:
    st.title("Rules")
    st.write("- Match the random 3 number combination! (0~9)")
    st.write("- **Strike**: The number and location was both correct")
    st.write("- **Ball**: The number was correct but the location was wrong")
    st.write("- **Out**: The number does not exist in the combination")
    st.divider()

    if st.button("Go Back", use_container_width=True):
        st.session_state.page = 5
        st.rerun()
