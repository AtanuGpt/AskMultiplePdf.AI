import streamlit as st
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_core.messages import AIMessage, HumanMessage
from htmlTemplates import css, bot_template, user_template

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = CharacterTextSplitter(
        separator="\n",
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

def get_vectorstore(text_chunks):
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_texts(texts=text_chunks, embedding=embeddings)
    return vectorstore

def get_conversation_chain(vectorstore):
    llm = ChatOpenAI()

    memory = ConversationBufferMemory(
        memory_key='chat_history', 
        return_messages=True
    )

    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        memory=memory
    )

    return conversation_chain
            
#============================================================================================================
if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            AIMessage(content="Hello, I am a bot. How can I help you?")
        ]

def main():
    load_dotenv()

    st.set_page_config(
        page_title="Chat with multiple PDFs",
        page_icon=":sparkles:"
    )

    st.write(css, unsafe_allow_html=True)
    
    st.header("Chat with single or multiple PDFs :sparkles:")

    for message in st.session_state.chat_history:
        if isinstance(message, AIMessage):
            with st.chat_message("AI"):
                st.write(bot_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
        elif isinstance(message, HumanMessage):
            with st.chat_message("Human"):
                st.write(user_template.replace("{{MSG}}", message.content), unsafe_allow_html=True)
    
    with st.sidebar:
        st.subheader("Your documents")
        pdf_docs = st.file_uploader(
            "Upload your PDFs here and click on 'Process'", 
            accept_multiple_files=True
        )
        if st.button("Process"):
            with st.spinner("Processing"):
                # get pdf text
                raw_text = get_pdf_text(pdf_docs)

                # get the text chunks
                text_chunks = get_text_chunks(raw_text)

                # create vector store
                vectorstore = get_vectorstore(text_chunks)

                # create conversation chain
                st.session_state.conversation = get_conversation_chain(vectorstore)

                # Let the user know its successful
                st.session_state.isPdfProcessed = "done"
                st.success("Done!")

    if "isPdfProcessed" in st.session_state:
        user_question = st.chat_input("Ask a question about your document(s):")

        if user_question is not None and user_question != "":
            st.session_state.chat_history.append(HumanMessage(content=user_question))

            with st.chat_message("Human"):
                st.write(user_template.replace("{{MSG}}", user_question), unsafe_allow_html=True)
            
            with st.chat_message("AI"):
                with st.spinner("Fetching data ..."):
                    response = st.session_state.conversation.invoke({'question': user_question})

                    # Extract answer and relevant links
                    answer = response["answer"]
                    sources = response.get("sources", [])
                    
                    links = "\n".join([f"[{i+1}] {source['url']}" for i, source in enumerate(sources)])

                    if links == "":
                        links = "No relevant links found"

                    full_response = f"{answer}\n\n**Relevant links:**\n{links}"

                    st.write(bot_template.replace("{{MSG}}", full_response), unsafe_allow_html=True)

            st.session_state.chat_history.append(AIMessage(content=response["answer"]))

   
#============================================================================================================
if __name__ == '__main__':
    main()