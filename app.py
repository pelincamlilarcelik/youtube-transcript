from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import openai
import subprocess
import os
from fpdf import FPDF
from datetime import datetime
from yt_dlp import YoutubeDL

openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)
CORS(app)

os.makedirs("downloads", exist_ok=True)
os.makedirs("transcripts", exist_ok=True)

def download_audio(youtube_url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/audio.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

def transcribe_audio(file_path):
    with open(file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript["text"]

def save_transcript(text):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_path = f"transcripts/transcript_{timestamp}.txt"
    pdf_path = f"transcripts/transcript_{timestamp}.pdf"

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, text)
    pdf.output(pdf_path)

    return txt_path, pdf_path

@app.route('/transcribe', methods=['POST'])
def transcribe():
    data = request.get_json()
    url = data.get("youtubeUrl")
    if not url:
        return jsonify({"error": "youtubeUrl is required"}), 400

    try:
        audio_path = download_audio(url)
        transcript_text = transcribe_audio(audio_path)
        txt_path, pdf_path = save_transcript(transcript_text)

        return jsonify({
            "transcript": transcript_text,
            "txtFile": os.path.basename(txt_path),
            "pdfFile": os.path.basename(pdf_path)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download/<file_type>/<filename>')
def download_file(file_type, filename):
    folder = "transcripts"
    if file_type not in ["txt", "pdf"]:
        return "Invalid file type", 400
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
