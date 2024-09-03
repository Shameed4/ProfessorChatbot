import json
import time
from dotenv import load_dotenv

# os stuff
import os
from pathlib import Path

load_dotenv('./.env.local')
professor_name = 'Ritwik Banerjee'
papers_path = Path('./papers')

# openAI stuff
from openai import OpenAI
import tiktoken
embeddings_model = 'text-embedding-3-small'
language_model = 'gpt-4o-mini'
tokenizer = tiktoken.encoding_for_model(embeddings_model)
client = OpenAI()
cost_per_token = 0.000020 / 1000

from helpers import name_to_index_name, name_to_pathname

# pinecone and langchain stuff
from pinecone import Pinecone, ServerlessSpec
from langchain.text_splitter import RecursiveCharacterTextSplitter

pc = Pinecone()
cloud = os.environ.get('PINECONE_CLOUD') or 'aws'
region = os.environ.get('PINECONE_REGION') or 'us-east-1'
spec = ServerlessSpec(cloud=cloud, region=region)

# returns how many tokens a text is
def tiktoken_len(text):
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    return len(tokens)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=20,
    length_function=tiktoken_len,
    separators=["\n\n", "\n", " ", ""]
)

index_name="professors"
if index_name not in pc.list_indexes().names():
    pc.create_index(
        index_name,
        dimension=1536, # TODO: replace with len(embed.data[0].embedding)
        metric='cosine',
        spec=spec
    )
index = pc.Index(index_name)


uploaded_professors_path = papers_path / 'uploaded_professors.json' 
if os.path.exists(uploaded_professors_path):
    with open(uploaded_professors_path, 'r') as file:
        professors = json.load(file)
else:
    professors = []

# gets the chunks given that there are .txt files in that directory
def get_chunks(dir_path : Path):
    chunks = []
    with open(dir_path / 'successful_articles.json', 'r') as file:
        success_data = json.load(file) # success_data contains titles as keys and [file_name,
    print(success_data)
    for file_name in success_data:
        with open(Path.joinpath(dir_path, file_name), "r") as file:
            article_title = success_data[file_name][0]
            article_url = success_data[file_name][1]
            article_text = file.read()
        file_text_chunks = text_splitter.split_text(article_text)
        file_chunks = [{'id': article_title + f' [CHUNK {id}]', 'url': article_url, 'text': file_text_chunk} for id, file_text_chunk in enumerate(file_text_chunks)]
        chunks.extend(file_chunks)
    return chunks

def estimate_embedding_cost(chunks, batch_size=10):
    total_tokens = 0
    for i in range(0, len(chunks), batch_size):
        i_end = min(len(chunks), i+batch_size)
        meta_batch = chunks[i:i_end]
        texts = [chunk['text'] for chunk in meta_batch]
        batch_encoding = tokenizer.encode_batch(texts)
        total_tokens += sum(len(encoding) for encoding in batch_encoding)
    return total_tokens * cost_per_token

def chunks2embedding(texts, attempts=2, delay=2):
    for i in range(attempts):  # attempt creating the embeddings twice
        try:
            res = client.embeddings.create(input=texts, model=embeddings_model)
            done = True
            break
        except:
            time.sleep(delay)
    return [record.embedding for record in res.data]


def upload_to_pinecone(professor_name, chunks, batch_size=50, estimate_costs=False):
    # check if professor already exists
    query_result = index.query(
        vector=[0]*1536, 
        top_k=1,
        filter={"professor": professor_name},
        include_metadata=True
    )
    if query_result["matches"]:
        print("Vector with professor: 'Xi Chen' already exists.")
        return
    
    total_tokens = 0 # TODO: Count tokens for estimating costs
    print(f"Embedding {len(chunks)}")
    for i in range(0, len(chunks), batch_size):
        i_end = min(len(chunks), i+batch_size)
        print(f"Embedding chunks {i} to {i_end}")
        meta_batch = chunks[i:i_end] # this format will be easier for the next 3 lines, but meta_batch will change later

        meta_texts = [chunk['text'] for chunk in meta_batch]
        meta_ids = [chunk['id'] for chunk in meta_batch]
        meta_urls = [chunk['url'] for chunk in meta_batch]

        embeds = chunks2embedding(meta_texts)
        meta_batch = [{
            'text': x['text'],
            'id': x['id'],
            'url': x['url'],
            'professor': professor_name
        } for x in meta_batch]
        to_upsert = list(zip(meta_ids, embeds, meta_batch))
    
    index.upsert(vectors=to_upsert)

    # save loaded professors locally   
    professors.append(professor_name)
    with open(uploaded_professors_path, 'w') as file:
        json.dump(professors, file, indent=4)


def name_to_uploaded_db(name : str):
    path = papers_path / name_to_pathname(name)
    chunks = get_chunks(path)
    upload_to_pinecone(name, chunks)


def prompt_index_deletion_and_quit():
    inp = input('Exiting program. Delete index? y/n: ')
    if inp == 'y':
        pc.delete_index(index_name)
        print('Deleted index')
    else:
        print('Index saved')
    exit(0)

def rag_query(professor_name, user_message) -> str:
    with open(papers_path / name_to_pathname(professor_name) / "successful_articles.json", 'r') as file:
        article_info = json.load(file)
        titles = [item[0] for item in article_info.values()]
        print(titles)

   
    primer = (
    f"Your task is to generate a search query for a vector database. This query should be designed to retrieve relevant information "
    f"from research papers authored by Professor {professor_name}. The user's message may contain a question or a topic of interest "
    f"related to the professor's work. Use the following article titles as a reference to understand the scope of their research: {titles}. "
    "The query should be concise and focused on retrieving the most relevant information based on the user's input."
    )

    messages = [{"role": "system", "content": primer}, {"role": "user", "content": user_message}]
    response = client.chat.completions.create(
        model=language_model,
        messages=messages
    )
    answer = response.choices[0].message.content
    return answer


def rag_chat(professor_name, messages : list, k = 5):
    """
    Parameters:
        messages - The chat history (excluding the system prompt). Context retrieved by RAG will not be included in any of these messages.
                    The first and last element should both be user messages.
        k - The number of chunks that are received by the vector database.
    Returns a generator of chunks.
    """
    primer = f"You are a Q&A bot that answers questions specifically about {professor_name}'s research. If the user doesn't specify a professor, you know they are referring to {professor_name}. Avoid naming other professors unless it is relevant to the user's questions. You will be given {k} excerpts from {professor_name}'s research papers, but the user is not providing them and cannot see them. If you don't know anything based on the results, truthfully say \"I don't know\"."
    chat_history = [{"role": "system", "content": primer}] + messages
    user_response = chat_history[-1]["content"]
    chatbot_response = rag_query(professor_name, user_response)
    query = client.embeddings.create(input=[chatbot_response], model=embeddings_model).data[0].embedding
    top_results = index.query(vector=query, top_k=k, include_metadata=True, filter={'professor': professor_name})['matches']

    metadata = [result['metadata'] for result in top_results]
    info = ['\n\n'.join([f"{key}:{data[key]}" for key in data]) for data in metadata]
    augmented = '\n\n-----\n\n'.join(info)
    augmented_prompt = f"{augmented}\n\n\n-----\n\n\n{user_response}"
    chat_history[-1]["content"] = augmented_prompt
    completion = client.chat.completions.create(
        model=language_model,
        messages=chat_history,
        stream=True
    )
    
    for chunk in completion:
        content = chunk.choices[0].delta.content
        if content:
            yield content

if __name__ == "__main__":
    top_results = index.query(vector=[0]*1536, top_k=5, include_metadata=True, filter={'professor': "Ritwik Banerjee"})['matches']
    print(top_results)


