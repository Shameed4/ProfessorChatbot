import json
import time
from dotenv import load_dotenv


# os stuff
import os
from pathlib import Path

load_dotenv('./.env.local')
professor_name = 'Ritwik Banerjee'
dir_path = Path('./papers') / professor_name.lower().replace(' ', '_')

# openAI stuff
from openai import OpenAI
import tiktoken
embeddings_model = 'text-embedding-3-small'
language_model = 'gpt-4o-mini'
tokenizer = tiktoken.encoding_for_model(embeddings_model)
client = OpenAI()
cost_per_token = 0.000020 / 1000

# pinecone and langchain stuff
from pinecone import Pinecone, ServerlessSpec
from langchain.text_splitter import RecursiveCharacterTextSplitter
pc = Pinecone()
cloud = os.environ.get('PINECONE_CLOUD') or 'aws'
region = os.environ.get('PINECONE_REGION') or 'us-east-1'
spec = ServerlessSpec(cloud=cloud, region=region)
index_name=professor_name.lower().replace(' ', '-')
if index_name not in pc.list_indexes().names():
    pc.create_index(
        index_name,
        dimension=1536, # TODO: replace with len(embed.data[0].embedding)
        metric='cosine',
        spec=spec
    )
    while not pc.describe_index(index_name).status['ready']:
        time.sleep(1)
index = pc.Index(index_name)


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

def get_chunks(dir_path):
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
    total_tokens = 0
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
            'url': x['url']
        } for x in meta_batch]
        to_upsert = list(zip(meta_ids, embeds, meta_batch))
        index.upsert(vectors=to_upsert)

def prompt_index_deletion_and_quit():
    inp = input('Exiting program. Delete index? y/n: ')
    if inp == 'y':
        pc.delete_index(index_name)
        print('Deleted index')
    else:
        print('Index saved')
    exit(0)

def chat():
    primer = f"""You are a Q&A bot that answers questions about {professor_name}'s research based on information 
    provided by the user above each question. If you don't know anything based on the results, truthfully say 
    \"I don't know\"."""

    print("""Welcome to the chat bot! You can ask a question, or do one of the following
        FORGET if you want to reset the conversation (saving me money if you are starting a new topic)
        QUIT if you want to exit the conversation""")

    messages = [{"role": "system", "content": primer}]
    user_response = input(f"Ask a question about {professor_name}: ")
    while user_response != "QUIT":
        if user_response == "FORGET":
            messages = [{"role": "system", "content": primer}]
            print("Reset memory")
        else:
            query = client.embeddings.create(input=[user_response], model=embeddings_model).data[0].embedding
            top_results = index.query(vector=query, top_k=5, include_metadata=True)['matches']
            metadata = [result['metadata'] for result in top_results]
            info = ['\n'.join([f"{key}:\n{data[key]}" for key in data]) for data in metadata]
            augmented = '\n\n-----\n\n'.join(info)
            augmented_prompt = f"{augmented}\n\n\n-----\n\n\n{user_response}"

            messages.append({"role": "user", "content": augmented_prompt})
            completion = client.chat.completions.create(
                model=language_model,
                messages=messages
            )
            assistant_response = completion.choices[0].message.content
            print('\n', assistant_response)
            messages.append({"role": "assistant", "content": assistant_response})
            print('\n\n', messages[2])


        user_response = input(f"Ask a question about {professor_name}.")
    prompt_index_deletion_and_quit()


    completion = client.chat.completions.create(
        model=language_model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ]
    )

if index.describe_index_stats()['total_vector_count'] == 0:
    print('Index not yet created. Creating index.')
    chunks = get_chunks(dir_path)
    inp = input(f"Estimated cost: {estimate_embedding_cost(chunks)}. Would you like to continue? y/n: ")
    if inp == 'n':
        prompt_index_deletion_and_quit()
    upload_to_pinecone(professor_name, chunks)
else:
    print('Index already exists!')

chat()

prompt_index_deletion_and_quit()


