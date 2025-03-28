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
        Analyze similarity between two text responses to identify discussion points.
        Identifies potential discussion points even when answers appear aligned.

        Args:
            text1: First user's text response
            text2: Second user's text response

        Returns:
            dict: Analysis result with potential conflicts and specific discussion recommendations
        """
        # Handle empty inputs
        if not text1 and not text2:
            return {
                'similarity_score': 100,
                'potential_conflicts': [],
                'conflict_level': "none",
                'explanation': "Both responses are empty",
                'has_conflicts': False,
                'discussion_recommendations': []
            }
        elif not text1 or not text2:
            return {
                'similarity_score': 0,
                'potential_conflicts': ["One response is empty while the other has content"],
                'conflict_level': "medium",
                'explanation': "One person provided input while the other didn't, which may indicate different engagement levels",
                'has_conflicts': True,
                'discussion_recommendations': [
                    "Discuss: Expectations around participation and sharing perspectives"
                ]
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
                Analyze these two text responses from team members to identify discussion points for a team working together:

                PERSON 1: "{text1}"

                PERSON 2: "{text2}"

                IMPORTANT: Even when responses APPEAR aligned, there may be helpful things to discuss. The goal is to identify potential areas for discussion, not just conflicts.

                You must identify the following:

                1. CONFLICTS: Actual differences that would cause workplace tension (e.g., different work-style preferences).
                   - CONFLICT SEVERITY LEVELS:
                     - NONE: Responses are truly aligned with no meaningful tension points
                     - LOW: Minor differences that are easily reconciled
                     - MEDIUM: Differences that need attention but aren't deal-breakers
                     - HIGH: Significant differences that could cause real friction

                2. DISCUSSION POINTS: Topics worth discussing even when no conflict exists. These don't change the conflict level but should be noted.

                For EVERY pair of answers, identify any helpful discussion points, but DO NOT artificially inflate the conflict level. Many topics may be worth discussing even with a "none" conflict level.

                Return a JSON object with exactly these fields:
                1. similarity_score: A number from 0-100 indicating alignment (higher means more similar)
                2. potential_conflicts: An array of strings describing all important issues to discuss
                3. conflict_level: One of "none", "low", "medium", or "high" (use "none" if truly aligned)
                4. explanation: A brief explanation of your assessment (50 words max)
                5. discussion_recommendations: An array of specific things to discuss, each starting with "Discuss: "
                6. has_blindspots: Boolean indicating if there are areas one person mentioned that the other didn't

                IMPORTANT EXAMPLES:
                - If both people love intense work and have similar workaholic tendencies: conflict_level = "none", but still include discussion recommendations about boundaries
                - If one person focuses more on work-life balance than the other: conflict_level = "low" or higher
                - If work styles fundamentally differ: conflict_level = "medium" or "high"

                Only use "low", "medium", or "high" conflict levels when there is an actual difference that could create tension. Don't inflate the conflict level just because there are things to discuss.

                Return ONLY valid JSON with no other text.
                """

                response = model.generate_content(prompt)

                # Extract the text response
                result_text = response.text

                # Clean up the response to ensure valid JSON
                cleaned_text = result_text.strip('`\n ')
                if cleaned_text.startswith('json'):
                    cleaned_text = cleaned_text[4:].strip()

                # Parse JSON
                result_json = json.loads(cleaned_text)

                # Add has_conflicts flag based on conflict_level
                result_json['has_conflicts'] = result_json.get('conflict_level') in ["low", "medium", "high"]

                # Add recommendations to potential_conflicts to ensure they're seen by the comparison engine
                for rec in result_json.get('discussion_recommendations', []):
                    if rec not in result_json.get('potential_conflicts', []):
                        result_json['potential_conflicts'].append(rec)

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
            'conflict_level': "none",  # Default to none for error case
            'explanation': "Could not complete analysis due to an error with the LLM service",
            'has_conflicts': False,
            'discussion_recommendations': ["Discuss: Team members' work styles and expectations"],
            'error': str(last_error)
        }