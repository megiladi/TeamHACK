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
        
        # Print available models for debugging
        try:
            models = genai.list_models()
            print("Available Gemini models:")
            for model in models:
                print(f"- {model.name}")
        except Exception as e:
            print(f"Error listing models: {str(e)}")

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

        # Try different model names in case the API naming has changed
        model_names = ['models/gemini-1.5-pro', 'models/gemini-1.5-flash', 'models/gemini-2.0-pro-exp']
        last_error = None

        for model_name in model_names:
            try:
                print(f"Trying model: {model_name}")
                # Get a reference to the model
                model = genai.GenerativeModel(model_name)
                
                prompt = f"""
                Analyze these two text responses from team members for SIGNIFICANT conflicts in work style, communication preferences, or values:

                PERSON 1: "{text1}"

                PERSON 2: "{text2}"

                Flag two types of issues:
                
                1. MAJOR CONFLICTS: Identify major differences between team members that would likely cause workplace conflicts or serious misalignments when these people collaborate.
                
                2. DISCUSSION POINTS: Flag important individual traits or behaviors mentioned by either person that would benefit from team discussion, even if they don't conflict with the other person (e.g., if someone mentions they're often late, have unusual working hours, or other notable work habits).

                Ignore minor stylistic differences, slight variations in preferences, or differences that are complementary rather than conflicting.

                A conflict should only be flagged if it represents a fundamental incompatibility in working styles that would require explicit discussion to resolve.

                Examples of issues to flag:
                - One person strongly prefers solo work while the other insists on constant collaboration
                - One person values detailed planning while the other believes in complete spontaneity
                - Fundamentally opposed communication styles (e.g., direct vs highly diplomatic)
                - One person mentions they struggle with punctuality or meeting deadlines
                - Someone notes they have atypical working hours or special requirements

                Examples of minor differences to IGNORE:
                - Small variations in preferences that can easily coexist
                - Stylistic differences that don't impact collaboration
                - Complementary traits that could balance each other

                Return a JSON object with exactly these fields:
                1. similarity_score: A number from 0-100 indicating overall alignment (higher means more similar)
                2. potential_conflicts: An array of strings describing potential major conflicts or important discussion points (empty array if none)
                3. conflict_level: One of "none", "low", "medium", or "high"
                4. explanation: A brief explanation of your assessment (50 words max)

                Be conservative in your assessment. When in doubt, rate the conflict level lower.
                However, always flag individual traits that would need team discussion.
                Return ONLY valid JSON with no other text.
                """

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
                result_json['has_conflicts'] = result_json.get('conflict_level') == "high"

                return result_json

            except Exception as e:
                last_error = e
                print(f"Error with model {model_name}: {str(e)}")
                continue  # Try the next model name

        # If we've tried all models and none worked
        print(f"All Gemini model attempts failed. Last error: {str(last_error)}")
        return {
            'similarity_score': 50,
            'potential_conflicts': [f"Analysis error: {str(last_error)}"],
            'conflict_level': "unknown",
            'explanation': "Could not complete analysis due to an error with the LLM service",
            'has_conflicts': False,
            'error': str(last_error)
        }