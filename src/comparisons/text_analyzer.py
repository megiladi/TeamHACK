import os
import json
import re
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
        Uses a simplified three-state classification system: aligned, discuss, high_priority.

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
                'potential_discussion_points': [],
                'assessment': "aligned",
                'explanation': "Both responses are empty",
                'has_conflicts': False,
                'recommendations': []
            }
        elif not text1 or not text2:
            return {
                'similarity_score': 0,
                'potential_discussion_points': ["One response is empty while the other has content"],
                'assessment': "discuss",
                'explanation': "One person provided input while the other didn't",
                'has_conflicts': True,
                'recommendations': [
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
                Analyze these two work style responses for potential collaboration friction:

                PERSON 1: "{text1}"

                PERSON 2: "{text2}"

                CRITICAL GUIDELINES:
                1. There are ONLY THREE possible assessment levels:
                   - ALIGNED: Approaches are compatible or complementary
                   - DISCUSS: Worth a conversation but not fundamentally problematic
                   - HIGH PRIORITY: Critical difference that must be addressed

                2. BE CONSERVATIVE with flagging conflicts:
                   - Different but complementary approaches should be ALIGNED
                   - Time preferences with ANY overlap should be ALIGNED
                   - Only flag HIGH PRIORITY when a true blocker to collaboration exists

                Examples:
                - Different problem-solving styles that complement each other = ALIGNED
                - Overlapping productive times (10AM-2PM vs 11AM-6PM) = ALIGNED  
                - One preferring structured meetings vs one preferring action-oriented meetings = DISCUSS
                - Someone who needs silence to work vs someone who talks constantly = HIGH PRIORITY

                Return a JSON object with exactly these fields:
                1. assessment: ONLY "aligned", "discuss", or "high_priority"
                2. potential_discussion_points: Array of specific items worth discussing
                3. explanation: Brief explanation of your assessment (30 words max)
                4. recommendations: 1-2 specific conversation topics if needed
                5. similarity_score: A number from 0-100 indicating alignment (higher means more similar)

                IMPORTANT: Default to ALIGNED unless there's clear evidence of friction.
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

                # Apply additional validation to prevent over-flagging
                result_json = self.validate_assessment(result_json, text1, text2)

                # Add has_conflicts flag based on assessment
                result_json['has_conflicts'] = result_json.get('assessment') in ["discuss", "high_priority"]

                return result_json

            except Exception as e:
                last_error = e
                print(f"Error with model {model_name}: {str(e)}")
                continue  # Try the next model name

        # If we've tried all models and none worked
        print(f"All Gemini model attempts failed. Last error: {str(last_error)}")
        return {
            'similarity_score': 50,
            'potential_discussion_points': [f"Analysis error: {str(last_error)}"],
            'assessment': "aligned",  # Default to aligned for error case
            'explanation': "Could not complete analysis due to an error with the LLM service",
            'has_conflicts': False,
            'recommendations': ["Discuss: Team members' work styles and expectations"],
            'error': str(last_error)
        }

    def validate_assessment(self, result, text1, text2):
        """Additional validation to prevent over-flagging conflicts"""

        # Time preference check - look for overlaps
        time_patterns = [r'\d+\s*(am|pm)', r'\d+:\d+', r'morning', r'afternoon', r'evening']

        times1 = []
        times2 = []

        for pattern in time_patterns:
            times1.extend(re.findall(pattern, text1.lower()))
            times2.extend(re.findall(pattern, text2.lower()))

        # If both mention times and there's likely overlap, consider aligning
        if times1 and times2 and result.get('assessment') == "discuss":
            result['assessment'] = "aligned"
            result['explanation'] = "Time preferences show potential compatibility."

        # Check for complementary approaches in problem-solving
        complementary_terms = [
            ["brood", "truth seeking", "data driven", "structure"],
            ["team", "collaborate", "coworking"],
            ["sprint", "execute", "action", "implement"]
        ]

        # If terms from the same complementary group appear across both texts
        for group in complementary_terms:
            terms1 = [term for term in group if term in text1.lower()]
            terms2 = [term for term in group if term in text2.lower()]

            if terms1 and terms2 and result.get('assessment') == "discuss":
                result['assessment'] = "aligned"
                result['explanation'] = "Approaches appear complementary rather than conflicting."

        return result