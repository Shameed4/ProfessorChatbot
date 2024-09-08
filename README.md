# Professor Chatbot

Are you interested in learning more about a professor's research but find it overwhelming to read through all their papers or understand complex language? This project provides a solution. Professor Chatbot is a web app that allows users to ask questions about a professor's research and get concise, easy-to-understand answers. The app automatically scrapes and indexes papers from the professor's Google Scholar page, making the research more accessible.

## How to set up the program
1. Make sure that you have NodeJS and Python installed.
2. Clone this repository.
3. Create a `.env.local` file in the `api` directory. Add the following two lines with your API keys:
   ```bash
   OPENAI_API_KEY=your-openai-api-key
   PINECONE_API_KEY=your-pinecone-api-key
   ```
4. In the terminal, navigate to the `api` directory (`cd api`) and run the following command to install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   You can now safely close this terminal once the installations are complete.
5. Follow the instructions for **How to run the program** below.

## How to run the program
1. Open a terminal and navigate to the `api` directory:
   ```bash
   cd api
   python backend.py
   ```
   This will run the back-end. Keep this terminal open until you're ready to stop the program.
2. In another terminal, navigate to the root `ProfessorChatbot` directory:
   ```bash
   cd ProfessorChatbot
   npm start
   ```
   The app will now be running locally at `http://localhost:3000`. You can open this URL in your browser to use the app!

## Technologies Used
- Node.js
- Python
- React
- Flask
- OpenAI API
- Pinecone

## Future Improvements
- Improve scraping abilities to gather more articles.
- Enhance the chatbot's ability to answer more specific or complex research questions.
- Implement user authentication for custom saved profiles of professors and favorite papers.
