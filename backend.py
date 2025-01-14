#PARA EJECUTAR: uvicorn backend:app --reload --host 0.0.0.0 --port 8000
from fastapi import FastAPI, UploadFile, HTTPException
from pydantic import BaseModel
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.chains import RetrievalQA
import shutil
import os

# Inicializa la aplicación FastAPI
app = FastAPI()

# Configuración de OpenAI
import openai
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(), override=True)
openai.api_key = os.environ['OPENAI_API_KEY']

# Configuración del almacenamiento para documentos y base de datos
DB_DIRECTORY = "db"
PDF_DIRECTORY = "DocumentosPDF"  # Carpeta con los PDFs iniciales

if not os.path.exists(DB_DIRECTORY):
    os.makedirs(DB_DIRECTORY)

# Variables globales
embedding = OpenAIEmbeddings()
vector_db = None
llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

# Modelo para la solicitud de preguntas
class QueryRequest(BaseModel):
    question: str

# Función para cargar documentos desde PDF
def cargar_documentos_desde_pdfs(pdf_directory):
    all_docs = []
    if not os.path.exists(pdf_directory):
        os.makedirs(pdf_directory)
        print(f"Carpeta creada: {pdf_directory}")
    
    for filename in os.listdir(pdf_directory):
        if filename.endswith(".pdf"):
            print(filename)
            file_path = os.path.join(pdf_directory, filename)
            print(f"Cargando archivo: {file_path}")
            loader = PyPDFLoader(file_path)
            pages = loader.load()

            text_splitter = CharacterTextSplitter(
                separator="\n", chunk_size=650, chunk_overlap=80, length_function=len
            )
            docs = text_splitter.split_documents(pages)
            all_docs.extend(docs)
    return all_docs

# Inicialización de la base de datos al arrancar el servidor
@app.on_event("startup")
async def startup_event():
    global vector_db
    all_docs = cargar_documentos_desde_pdfs(PDF_DIRECTORY)

    if all_docs:
        print(f"Documentos cargados: {len(all_docs)}")
        vector_db = Chroma.from_documents(documents=all_docs, embedding=embedding, persist_directory=DB_DIRECTORY)
        vector_db.persist()
    else:
        print("No se encontraron documentos iniciales para cargar.")


# Endpoint para cargar documentos
@app.post("/upload")
async def upload_files(files: list[UploadFile]):
    global vector_db

    all_docs = []
    for file in files:
        # Guarda temporalmente el archivo
        temp_file = f"temp_{file.filename}"
        with open(temp_file, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Carga el archivo y extrae su contenido
        loader = PyPDFLoader(temp_file)
        pages = loader.load()

        # Divide en chunks
        text_splitter = CharacterTextSplitter(
            separator="\n", chunk_size=650, chunk_overlap=80, length_function=len
        )
        docs = text_splitter.split_documents(pages)
        all_docs.extend(docs)

        # Elimina el archivo temporal
        os.remove(temp_file)

    # Crear o actualizar la base de datos
    if vector_db is None:
        vector_db = Chroma.from_documents(documents=all_docs, embedding=embedding, persist_directory=DB_DIRECTORY)
    else:
        vector_db.add_documents(all_docs)

    vector_db.persist()
    return {"message": f"{len(files)} archivo(s) cargado(s) exitosamente"}

# Endpoint para responder preguntas
@app.post("/query")
async def query_question(request: QueryRequest):
    global vector_db
    if vector_db is None:
        raise HTTPException(status_code=400, detail="No hay documentos cargados")

    question = request.question
    print(f"Pregunta recibida: {question}")

    retriever = vector_db.as_retriever()
    qa_chain = RetrievalQA.from_chain_type(llm, retriever=retriever)
    result = qa_chain({"query": question})

    return {"response": result["result"]}
