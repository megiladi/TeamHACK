import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TextAnalyzer:
    """Text analyzer that exclusively uses Google's Gemini API."""

    def __init__(self):
        # Get API key from environment variable
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")

        if not self.gemini_api_key:
            raise ValueError("Gemini API key is required. Please set GEMINI_API_KEY in your .env file.")

        # Configure Gemini API
        genai.configure(api_key=self.gemini_api_key)

    def analyze_text_similarity(self, text1, text2):
        """
        Analyze similarity between two text responses using Gemini.

        Args:
            text1: First user's text response
            text2: Second user's text response

        Returns:
            dict: Analysis result with potential conflicts
        """
        # Handle empty inputs
        if not text1 and not text2:
            return {
                'similarity_score': 100,
                'potential_conflicts': [],
                'conflict_level': "none",
                'explanation': "Both responses are empty",
                'has_conflicts': False
            }
        elif not text1 or not text2:
            return {
                'similarity_score': 0,
                'potential_conflicts': ["One response is empty"],
                'conflict_level': "high",
                'explanation': "One person provided input while the other didn't",
                'has_conflicts': True
            }

        # Get a reference to the model
        model = genai.GenerativeModel('gemini-pro')

        prompt = f"""
        Analyze these two text responses from team members for potential conflicts in work style, communication preferences, or values:

        PERSON 1: "{text1}"

        PERSON 2: "{text2}"

        Focus on identifying differences that might cause workplace conflicts or misalignments when these people collaborate.

        Return a JSON object with exactly these fields:
        1. similarity_score: A number from 0-100 indicating overall alignment (higher means more similar)
        2. potential_conflicts: An array of strings describing specific potential conflict areas
        3. conflict_level: One of "none", "low", "medium", or "high"
        4. explanation: A brief explanation of your assessment (50 words max)

        Return ONLY valid JSON with no other text.
        """

        try:
            response = model.generate_content(prompt)

            # Extract the text response
            result_text = response.text

            # Clean up the response to ensure valid JSON
            # Remove any markdown formatting, leading/trailing backticks, etc.
            cleaned_text = result_text.strip('`\n ')
            if cleaned_text.startswith('json'):
                cleaned_text = cleaned_text[4:].strip()

            # Parse JSON
            result_json = json.loads(cleaned_text)

            # Add has_conflicts flag based on conflict_level
            result_json['has_conflicts'] = result_json.get('conflict_level') in ("medium", "high")

            return result_json

        except Exception as e:
            # Instead of falling back to word-based comparison, return an error
            # This ensures we're always using the LLM or nothing
            print(f"Error in Gemini API analysis: {str(e)}")
            return {
                'similarity_score': 50,
                'potential_conflicts': [f"Analysis error: {str(e)}"],
                'conflict_level': "unknown",
                'explanation': "Could not complete analysis due to an error with the LLM service",
                'has_conflicts': False,
                'error': str(e)
            }