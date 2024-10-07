
import boto3
from langchain_aws import ChatBedrock
import os
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from config_file import Config
from genAI.utils.assistant.embeddingsDataLoad import get_db_connection_string
from langchain_community.embeddings import BedrockEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain.chains import RetrievalQA
import sys

bedrock_region = Config.BEDROCK_REGION
bedrock_runtime = boto3.client("bedrock-runtime", region_name=bedrock_region)

bedrock_modelId = Config.LLM_MODEL_ID
claude_chat_llm = ChatBedrock(
    model_id=bedrock_modelId,
    client=bedrock_runtime,
    model_kwargs={"temperature": 0.0, "top_p": 0.99},
)

def get_qa_answer(user_question, verbose=True):
    try:
        print("inside get qa answer")
        
        embedding_model = BedrockEmbeddings(
            model_id=Config.EMBEDDINGS_MODEL_ID, client=bedrock_runtime
        )
    
        db = PGVector.from_existing_index(
            embedding=embedding_model,
            collection_name='InvestmentAnalyst',
            connection=get_db_connection_string(),
        )
    
        # Retrieve and generate using the relevant snippets of the blog.
        retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 6})
        
        question_answer_chain = create_stuff_documents_chain(claude_chat_llm, prompt)
        
        print("invoking rag chain")
        
        rag_chain = create_retrieval_chain(retriever, question_answer_chain)

        response = rag_chain.invoke({"input": user_question})
        print("Query Response:", response)  # Properly print the response
        print(response["answer"])
        
        for document in response["context"]:
            print(document)
            print()
        
        return response
        
    except Exception as e:
        print(f"Failed to get answer: {str(e)}")
        return str(e), None


def get_rag_chain(question):
    """Prepare a RAG question answering chain.

      Note: Must use the same embedding model used for creating the semantic search index
      to be used for real-time semantic search.
    """
    
    try:
        embedding_model = BedrockEmbeddings(
            model_id=Config.EMBEDDINGS_MODEL_ID, client=bedrock_runtime
        )
    
        vector_store = PGVector.from_existing_index(
            embedding=embedding_model,
            collection_name='InvestmentAnalyst',
            connection=get_db_connection_string(),
        )
    
        return RetrievalQA.from_chain_type(
            llm=claude_chat_llm,
            chain_type="stuff",
            retriever=vector_store.as_retriever(k=5, fetch_k=50),
            return_source_documents=True,
            input_key=question,
            verbose=True,
        )
    except Exception as e:
        print("Error during RAG Retrieval:", e)
        return str(e), None


system_prompt = (
    "You are an assistant for question-answering tasks. "
    "Use the following pieces of retrieved context to answer "
    "the question. Provide as much as details as possible.If you don't know the answer, say that you "
    "don't know."
    "\n\n"
    "{context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

# Example usage
if __name__ == "__main__":
    
    get_qa_answer("What are Amazon's revenue streams?")
    
