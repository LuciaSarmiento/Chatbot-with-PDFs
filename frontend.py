import streamlit as st
import requests

# Configuración de la API
API_URL = "http://localhost:8000"

# Interfaz del chatbot
st.title("Chatbot sobre Moody's CreditLens")

# Sección para subir documentos
st.header("1. Subir documentos")
uploaded_files = st.file_uploader("Sube tus PDFs", type=["pdf"], accept_multiple_files=True)

if st.button("Subir documentos"):
    if uploaded_files:
        files = [("files", (file.name, file, "application/pdf")) for file in uploaded_files]
        response = requests.post(f"{API_URL}/upload", files=files)
        if response.status_code == 200:
            st.success(response.json()["message"])
        else:
            st.error("Hubo un error al subir los archivos.")
    else:
        st.warning("Por favor, sube al menos un archivo.")

# Sección para realizar preguntas
st.header("2. Consultar al chatbot")
question = st.text_input("Escribe tu pregunta:")
if st.button("Enviar pregunta"):
    if question.strip():
        print("Enviando pregunta:", question)
        response = requests.post(f"{API_URL}/query", json={"question": question})
        print(response)
        if response.status_code == 200:
            st.write("**Respuesta:**", response.json()["response"])
        else:
            st.error("Hubo un error al obtener la respuesta.")
    else:
        st.warning("Por favor, escribe una pregunta.")
