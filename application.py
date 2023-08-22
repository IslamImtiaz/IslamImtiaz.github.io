from flask import Flask, render_template, request, send_file
from moviepy.editor import VideoFileClip
from deepgram import Deepgram
import json
from moviepy.editor import TextClip, CompositeVideoClip
import os


application = Flask(__name__)

def extract_audio_from_video(video_path, output_audio_path):
    video_clip = VideoFileClip(video_path)
    audio_clip = video_clip.audio

    audio_clip.write_audiofile(output_audio_path)

    video_clip.close()
    audio_clip.close()

def generate_json_file(audio_path):
    DEEPGRAM_API_KEY = 'd0921111401b01d588acbc2afaa580d5146e4c8d'

    dg_client = Deepgram(DEEPGRAM_API_KEY)

    with open(audio_path, 'rb') as audio:
        source = {'buffer': audio, 'mimetype': 'audio/wav'}
        options = {"smart_format": True, "model": "general", "tier": "nova", "language": "en-US"}

        response = dg_client.transcription.sync_prerecorded(source, options)

    with open('static/output.json', 'w') as output_file:
        json.dump(response, output_file, indent=4)

def extract_sentences_from_json(json_path):
    with open(json_path, "r") as json_file:
        data = json.load(json_file)

    sentences_info = []
    channels = data.get("results", {}).get("channels", [])
    for channel in channels:
        for alternative in channel.get("alternatives", []):
            sentence_text = ""
            sentence_start = None
            sentence_end = None
            for sentence in alternative.get("words", []):
                word_text = sentence.get("punctuated_word", "")
                word_start = sentence.get("start", 0.0)
                word_end = sentence.get("end", 0.0)

                if len(sentence_text) + len(word_text) > 100:
                    sentence_info = {
                        "text": sentence_text,
                        "start": sentence_start,
                        "end": sentence_end
                    }
                    sentences_info.append(sentence_info)
                    sentence_text = word_text
                    sentence_start = word_start
                    sentence_end = word_end
                else:
                    if sentence_text:
                        sentence_text += " "
                    if sentence_start is None:
                        sentence_start = word_start
                    sentence_text += word_text
                    sentence_end = word_end

                if word_text.endswith((".", "!", "?")):
                    sentence_info = {
                        "text": sentence_text,
                        "start": sentence_start,
                        "end": sentence_end
                    }
                    sentences_info.append(sentence_info)
                    sentence_text = ""
                    sentence_start = None
                    sentence_end = None

    output_file = "static/sentences_info.json"
    with open(output_file, "w") as output_json_file:
        json.dump(sentences_info, output_json_file, indent=4)

def add_captions_to_video(video_path, captions_path):
    with open(captions_path, 'r') as captions_file:
        captions_data = json.load(captions_file)

    captions = captions_data

    video = VideoFileClip(video_path)

    caption_clips = []

    for caption in captions:
        start_time = caption['start']
        end_time = caption['end']
        text = caption['text']

        caption_clip = TextClip(text, fontsize=24, color='white')
        caption_clip = caption_clip.set_position(('center', 'bottom'))
        caption_clip = caption_clip.set_start(start_time).set_end(end_time)

        caption_clips.append(caption_clip)

    video_with_captions = CompositeVideoClip([video] + caption_clips)
    video_with_captions = video_with_captions.set_audio(video.audio)

    output_video_path = 'static/output_video.mp4'
    video_with_captions.write_videofile(output_video_path, codec='libx264')

    print("Captions added to the video successfully!")
    print(f"Output video saved to {output_video_path}")
    os.remove(video_path)
    return output_video_path

@application.route('/')
def home():
    return render_template('index.html')

@application.route('/main')
def main():
    return render_template('index.html')

@application.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        video_path = file.filename
        output_audio_path = "static/Caption.wav"
        audio_path = "static/Caption.wav"
        json_path = "static/output.json"
        captions_path = "static/sentences_info.json"

        file.save(video_path)

        extract_audio_from_video(video_path, output_audio_path)
        generate_json_file(audio_path)
        extract_sentences_from_json(json_path)
        output_video_path = add_captions_to_video(video_path, captions_path)

        return render_template('download.html', video_path=output_video_path)

    return render_template('upload.html')

@application.route('/download')
def download():
    output_video_path = 'static/output_video.mp4'
    return send_file(output_video_path, as_attachment=True)


if __name__ == '__main__':
    application.run(debug=True)

