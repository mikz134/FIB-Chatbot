import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from get_vector_db import get_vector_db

SOURCE_FOLDER = os.getenv('SOURCE_FOLDER', './document_source')

# Function to check if the uploaded file is allowed (only PDF files)
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf'}


def save_file(file):
    file_path = os.path.join(SOURCE_FOLDER, file.filename)
    file.save(file_path)
    return file_path

def load_and_split_data(file_path):
    loader = PyPDFLoader(file_path=file_path)
    data = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(data)
    return chunks


def embed_url(url):
    loader = WebBaseLoader(url)
    docs = loader.load()
    for doc in docs:
        print(doc)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = text_splitter.split_documents(docs)
    db = get_vector_db()
    db.add_documents(chunks)
    return True


def embed(file):
    if file.filename != '' and file and allowed_file(file.filename):
        file_path = save_file(file)
        chunks = load_and_split_data(file_path)
        db = get_vector_db()
        db.add_documents(chunks)
        return True

    return False