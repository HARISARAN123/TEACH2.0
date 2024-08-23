import logging
import wikipedia
from flask import Flask, request, render_template, jsonify
import google.generativeai as genai
import os
import random

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini API
API_KEY = os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("No API key found. Set the GOOGLE_API_KEY environment variable.")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def query_gemini_doubt(doubt):
    """Query Gemini API to resolve doubt."""
    try:
        response = model.generate_content(doubt)
        return response.text
    except Exception as e:
        logger.error(f"Error querying Gemini: {e}")
        return "Error querying Gemini. Please try again later."

def generate_quiz_question(subject, syllabus, grade, difficulty):
    """Generate a quiz question based on provided inputs."""
    try:
        search_query = f"{subject} {syllabus} {grade}"
        search_results = wikipedia.search(search_query)

        if not search_results:
            return "No content available for this query. Please try a different topic.", {}, None

        page = wikipedia.page(search_results[0])
        content = wikipedia.summary(page.title, sentences=5)

        question_prompt = f"Generate a question about the following text: {content}"
        response = model.generate_content(question_prompt)
        question_text = response.text

        key_sentences = content.split('.')
        key_sentences = [sentence.strip() for sentence in key_sentences if sentence.strip()]

        if len(key_sentences) < 2:
            return "Not enough content to generate options.", {}, None

        correct_sentence = random.choice(key_sentences)
        options = { "A": correct_sentence }

        incorrect_options = [s for s in key_sentences if s != correct_sentence]
        while len(options) < 4 and incorrect_options:
            option = random.choice(incorrect_options)
            options[chr(65 + len(options))] = option
            incorrect_options.remove(option)

        while len(options) < 4:
            options[chr(65 + len(options))] = "Not enough relevant options available."

        correct_option = [k for k, v in options.items() if v == correct_sentence][0]

        return question_text, options, correct_option

    except wikipedia.exceptions.DisambiguationError as e:
        logger.error(f"Disambiguation error: {e}")
        return "Disambiguation error. Please be more specific in your query.", {}, None
    except wikipedia.exceptions.PageError as e:
        logger.error(f"Page not found: {e}")
        return "Page not found. Please try a different topic.", {}, None
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return "Error fetching question. Please try again later.", {}, None

@app.route('/')
def home():
    """Render the home page."""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        return jsonify({'error': 'An error occurred while rendering the page.'}), 500

@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    """Handle quiz generation and answer verification."""
    if request.method == 'POST':
        subject = request.form.get('subject')
        syllabus = request.form.get('syllabus')
        grade = request.form.get('grade')
        difficulty = request.form.get('difficulty')
        user_answer = request.form.get('user_answer')
        correct_answer = request.form.get('correct_answer')
        question = request.form.get('question')

        if user_answer:
            if user_answer.strip().upper() == correct_answer.upper():
                feedback = "Correct answer!"
            else:
                feedback = f"Incorrect. The correct answer was: {correct_answer}"
            return render_template('quiz.html', feedback=feedback, question=question, options=None)

        question, options, correct_answer = generate_quiz_question(subject, syllabus, grade, difficulty)
        return render_template('quiz.html', question=question, options=options, correct_answer=correct_answer)

    return render_template('quiz.html')

@app.route('/doubt', methods=['GET', 'POST'])
def doubt():
    """Handle doubt resolution."""
    if request.method == 'POST':
        doubt = request.form.get('doubt')
        answer = query_gemini_doubt(doubt)
        if not answer:
            try:
                search_results = wikipedia.search(doubt)
                if search_results:
                    page = wikipedia.page(search_results[0])
                    answer = wikipedia.summary(page.title, sentences=2)
                else:
                    answer = "No content found in Wikipedia for this doubt."
            except Exception as e:
                logger.error(f"Error querying Wikipedia: {e}")
                answer = "Error resolving doubt. Please try again later."

        return render_template('doubt.html', answer=answer)
    return render_template('doubt.html')

@app.route('/reset_quiz', methods=['POST'])
def reset_quiz():
    """Reset the quiz form."""
    return render_template('quiz.html')

if __name__ == '__main__':
    app.run(debug=True)
