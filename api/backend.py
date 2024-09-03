from helpers import name_to_pathname, pathname_to_name

from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS

import os
from pathlib import Path

from scraping import scrape_professor_by_name_college
from rag import name_to_uploaded_db, rag_chat, professors

app = Flask(__name__)
CORS(app)

papers_dir = Path('./papers')

@app.route('/professors', methods=['GET'])
def get_professors():
    return jsonify({'professors': professors})

@app.route('/scrape_professor', methods=['POST'])
def scrape_professor():
    data = request.get_json()
    professor = data.get('professor')
    college = data.get('college')
    if college:
        scrape_professor_by_name_college(professor, college)
    else:
        scrape_professor_by_name_college(professor)
    professor_papers_dir = papers_dir / name_to_pathname(professor)
    return jsonify({'articles': len(os.listdir(professor_papers_dir)) - 2})

@app.route('/upload_professor_to_db', methods=['POST'])
def upload_professor_to_db():
    data = request.get_json()
    professor = data.get('professor')
    if name_to_pathname(professor) not in os.listdir(papers_dir):
        return jsonify(f'{professor} not found in database'), 404
    else:
        name_to_uploaded_db(professor)
        return jsonify({'message': 'Success!'})

@app.route('/scrape_and_upload_professor', methods=['POST'])
def scrape_and_upload_professor():
    # Call the existing scrape_professor route
    professor = request.args.get('professor')
    college = request.args.get('college')
    print('info 2 --', professor, college)
    scrape_response = scrape_professor()
    scrape_data = scrape_response.get_json()

    # If scraping was successful, proceed to upload
    if 'articles' in scrape_data:
        upload_response = upload_professor_to_db()
        upload_data = upload_response.get_json()

        if upload_response.status_code == 200:
            # Combine the responses and return
            return jsonify({
                'message': upload_data['message'],
                'articles': scrape_data['articles']
            })
        else:
            return upload_response  # Return the error response from the upload route
    else:
        return scrape_response  # Return the error response from the scrape route


@app.route('/chat_with_professor', methods=['POST'])
def chat_with_professor():
    data = request.get_json()
    professor = data.get('professor')
    history = data.get('history')
    
    @stream_with_context
    def generate():
        for chunk in rag_chat(professor, history):
            yield chunk  # Yield each chunk to the client as it's generated
    
    return Response(generate(), content_type='text/event-stream')
    

if __name__ == '__main__':
    app.run(debug=True)