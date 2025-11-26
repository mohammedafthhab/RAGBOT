# RAGBOT
🌱 StudyMentor RAG Chatbot (Backend + Frontend)
A Retrieval-Augmented Generation (RAG) powered AI/ML study assistant built with Flask, FAISS, Sentence Transformers, MongoDB, Ollama (LLaMA 3), and React.
The project includes gesture recognition, PDF/URL ingestion, caching, and chat history storage.

🚀 Features

📚 RAG-based context retrieval from PDFs and online sources
🔍 FAISS vector search with caching
🤝 LLaMA 3 integration using Ollama
✋ Gesture-controlled input using MediaPipe
🧠 SentenceTransformer embeddings
🗂 MongoDB Atlas chat history logging
🖥 Full React frontend
⚡ Lightning-fast and ready for deployment
📦 Tech Stack

Backend
Python 3.10
Flask
Sentence Transformers (MiniLM-L6-v2)
FAISS
MongoDB Atlas
Ollama (LLaMA 3)
BeautifulSoup, PDFPlumber, OpenCV, MediaPipe

Frontend
React
npm
Axios

📁 Project Structure
project/
│
├── backend/
│   ├── app.py
│   ├── data/              # PDFs for RAG
│   ├── seed_cache/        # Auto-created FAISS cache
│   └── models/            # Gesture recognition models
│
└── frontend/
    ├── src/
    ├── public/
    └── package.json
    
🛠 Installation Guide
Follow these commands after cloning the repository:
✅ 1. Create and activate Conda environment
conda create -n RAG python=3.10 -y
conda activate RAG
✅ 2. Install backend dependencies
cd backend
pip install -r requirements.txt
✅ 3. Start the backend
python app.py
Backend will start at:
http://localhost:5000
🧠 LLaMA 3 (Ollama) Setup
If you haven’t installed Ollama:
Download: https://ollama.com/download
Then pull the model:
ollama pull llama3

🌐 4. Start the frontend
Open a new terminal:
cd frontend
npm install
npm start
Frontend will start at:
http://localhost:3000

📚 Adding PDFs for RAG
Place your PDFs inside:
backend/data/
The system will automatically:
read them
chunk them
embed them
save them to FAISS cache

✋ Gesture Recognition Setup
for send - 👍
for shutting down the camera - 👎
The backend uses:
models/gesture_model.pkl
models/label_encoder.pkl
Ensure these exist in backend/models/.


📝 Create a MongoDB and paste the URI 
MONGO_URI="your connection string"

🤝 Contributing
Pull requests are welcome!
Feel free to open issues for bugs or feature requests.
⭐ If you like this project, give it a Star!
