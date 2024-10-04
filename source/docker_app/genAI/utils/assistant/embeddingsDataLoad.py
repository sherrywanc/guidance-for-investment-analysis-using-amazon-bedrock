import json
import boto3
from langchain_community.embeddings import BedrockEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema.document import Document
import PyPDF2
from io import BytesIO 
from config_file import Config
import psycopg2

def activate_vector_extension(db_connection):
    try:
        
        """Activate PGVector extension."""
        print("Inside PGVector extension setup")
        print(type(db_connection))
        
        db_connection.autocommit = True
        cursor = db_connection.cursor()
        # install pgvector
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        db_connection.close()
        print("PGVector extension setup")
    except Exception as e:
        print("Error during Vector extension setup:", e)
        return ""

def get_db_connection():
    try:
        print("inside db connection")
        """Retrieve database credentials from AWS Secrets Manager and construct the connection string."""
        secret_name = Config.DB_SECRET_NAME
        region_name = Config.BEDROCK_REGION
    
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=region_name
        )
    
        # Retrieve the secret
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
        secret = get_secret_value_response['SecretString']
        database_secrets = json.loads(secret)
    
        # Extract database credentials
        host = database_secrets['host']
        dbname = database_secrets['dbname']
        username = database_secrets['username']
        password = database_secrets['password']
        port = database_secrets['port']
    
        db_connection = psycopg2.connect(
            host=host,
            port=port,
            database=dbname,
            user=username,
            password=password,
        )
        
        return db_connection  # Make sure to return the connection
    except Exception as e:
        print("Error creating connection to database:", e)
        return None
        
def get_db_connection_string():

    """Retrieve database credentials from AWS Secrets Manager and construct the connection string."""
    secret_name = Config.DB_SECRET_NAME
    region_name = Config.BEDROCK_REGION

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    # Retrieve the secret
    get_secret_value_response = client.get_secret_value(
        SecretId=secret_name
    )
    secret = get_secret_value_response['SecretString']
    database_secrets = json.loads(secret)

    # Extract database credentials
    host = database_secrets['host']
    dbname = database_secrets['dbname']
    username = database_secrets['username']
    password = database_secrets['password']
    port = database_secrets['port']

    # Construct the connection string to the PostgreSQL database using psycopg3
    connection_string = f"postgresql+psycopg://{username}:{password}@{host}:{port}/{dbname}"
    return connection_string

def extract_text_from_pdf(file_content):
    """Extract text from PDF content using PyPDF2."""
    file_like_object = BytesIO(file_content)
    pdf_reader = PyPDF2.PdfReader(file_like_object)
    full_text = []
    for page in pdf_reader.pages:
        text = page.extract_text()
        if text:
            full_text.append(text)
    return "\n".join(full_text)

def vectorize_and_store(file_content, file_name, collection_name="InvestmentAnalyst"):
    """Vectorize the document content and store it in the PostgreSQL vector store."""
    try:
        
        print("Inside vectorize_and_store function ")
        # Initialize the text embedding model
        embeddings = BedrockEmbeddings()

        # Initialize a text splitter for dividing text into chunks
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)

        # Extract text from the PDF content
        combined_text = extract_text_from_pdf(file_content)

        # Split the combined text into chunks
        text_chunks = text_splitter.split_text(combined_text)

        # Create Document instances from the chunks
        documents = [Document(page_content=chunk) for chunk in text_chunks]

        # Debug: Print the first document's content and metadata
        if documents:
            print(f"First document chunk: {documents[0].page_content}")
        
        dbconn = get_db_connection()
        
        print(dbconn)
        
        if dbconn is None:
            raise ValueError("Database connection failed")
        
        activate_vector_extension(dbconn)
        
        # Construct the connection string to the PostgreSQL database
        connection_string = get_db_connection_string()
        print(connection_string)
       
        # Create a vector database store instance and populate it with document data and embeddings
        db = PGVector(
            embeddings=embeddings,
            collection_name=collection_name,
            connection=connection_string,
            pre_delete_collection=True,  # For demo purposes, we are cleaning up vector data
        )
        
        db.add_documents(documents)

        print("Vector database store instance created and populated with embeddings.")
        return True

    except Exception as e:
        print("Error during PGVector setup:", e)
        return False

