from flask import Flask, request, jsonify
from flask_cors import CORS

import os
from pathlib import Path

from scraping import scrape_professor_by_name_college
from rag import path_to_uploaded_db, rag_chat

app = Flask(__name__)
CORS(app)

papers_dir = Path('./papers')

def pathname_to_name(pathname):
    return pathname.replace('_', ' ').title()

def name_to_pathname(name):
    return name.replace(' ', '_').lower()

@app.route('/echo', methods=['GET'])
def echo():
    message = request.args.get('message')
    print(message)
    return jsonify({'message': message})

@app.route('/professors', methods=['GET'])
def get_professors():
    professor_folders = os.listdir(papers_dir)
    professor_names = list(map(pathname_to_name, professor_folders))
    return jsonify({'professors': professor_names})

@app.route('/scrape_professor', methods=['POST'])
def scrape_professor():
    professor = request.args.get('professor')
    college = request.args.get('college')
    if college:
        scrape_professor_by_name_college(professor, college)
    else:
        scrape_professor_by_name_college(professor)
    professor_papers_dir = papers_dir / name_to_pathname(professor)
    return jsonify({'articles': len(os.listdir(professor_papers_dir) - 2)})

@app.route('/upload_professor_to_db', methods=['POST'])
def upload_professor_to_pinecone():
    professor = request.args.get('professor')
    if name_to_pathname(professor) not in os.listdir(papers_dir):
        return jsonify(f'{professor} not found in database'), 404
    else:
        path_to_uploaded_db(papers_dir / name_to_pathname(professor))
        return jsonify({'message': 'Success!'})

@app.route('/chat_with_professor', methods=['GET'])
def chat_with_professor():
    professor = request.args.get('professor')
    history = request.args.get('history')
    history = [{'role': 'user', 'content': 'Tell me about something that this professor published'}] # TODO: remove this line
    return jsonify(rag_chat(professor, history)), 200
    

if __name__ == '__main__':
    app.run(debug=True)