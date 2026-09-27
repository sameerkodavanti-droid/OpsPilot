import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Local embeddings — no API key required
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Path to the runbooks directory
RUNBOOKS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "runbooks")
CHROMA_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")

def init_vector_store():
    """Initialize the Chroma vector store and load runbooks if empty."""
    
    # Try to load existing Chroma DB
    if os.path.exists(CHROMA_DB_DIR) and os.listdir(CHROMA_DB_DIR):
        vector_store = Chroma(
            persist_directory=CHROMA_DB_DIR, 
            embedding_function=embeddings,
            collection_name="runbooks"
        )
    else:
        # Load runbooks from markdown files
        loader = DirectoryLoader(RUNBOOKS_DIR, glob="*.md", loader_cls=TextLoader)
        docs = loader.load()
        
        # Split markdown by headers
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        
        splits = []
        for doc in docs:
            md_splits = markdown_splitter.split_text(doc.page_content)
            # Add metadata about source
            for split in md_splits:
                split.metadata["source"] = doc.metadata["source"]
            splits.extend(md_splits)

        # Further split if sections are too large
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        final_splits = text_splitter.split_documents(splits)

        # Create the vector store
        vector_store = Chroma.from_documents(
            documents=final_splits,
            embedding=embeddings,
            persist_directory=CHROMA_DB_DIR,
            collection_name="runbooks"
        )
        
    return vector_store

# Initialize a global retriever
vector_store = init_vector_store()
retriever = vector_store.as_retriever(search_kwargs={"k": 2})

def retrieve_runbook(query: str) -> str:
    """Retrieve runbook context for a given diagnosis or query."""
    docs = retriever.invoke(query)
    if not docs:
        return "No relevant runbook found."
    
    context = "\n\n".join([
        f"Runbook: {os.path.basename(doc.metadata.get('source', 'unknown'))}\n{doc.page_content}"
        for doc in docs
    ])
    return context
