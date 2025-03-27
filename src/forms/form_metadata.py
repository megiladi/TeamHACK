"""
Dynamic form metadata class that extracts form structure from HTML.
"""
import os
from bs4 import BeautifulSoup

# Form field types
FIELD_TYPE_LIKERT = "likert"
FIELD_TYPE_RANKING = "ranking"
FIELD_TYPE_TRAIT = "trait"
FIELD_TYPE_TEXT = "text"
FIELD_TYPE_OTHER = "other"

class FormMetadata:
    """Form metadata class that can extract form structure from HTML."""

    def __init__(self, form_html_path=None):
        """
        Initialize form metadata by parsing the form HTML.

        Args:
            form_html_path: Path to the HTML form file
        """
        # Maps of known ranking groups and their max values
        self._known_ranking_groups = {}

        # Field types determined from form
        self._field_types = {}

        # Field name patterns that strongly suggest a field type
        self._field_patterns = {
            'rank_': FIELD_TYPE_RANKING,
            'ocean_': FIELD_TYPE_TRAIT
        }

        # Parse form HTML if provided
        if form_html_path and os.path.exists(form_html_path):
            self._parse_form_html(form_html_path)

    def _parse_form_html(self, html_path):
        """
        Parse the form HTML to extract field metadata.

        Args:
            html_path: Path to the HTML form file
        """
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            soup = BeautifulSoup(html_content, 'html.parser')

            # Find all form inputs, selects, and textareas
            form_elements = soup.find_all(['input', 'select', 'textarea'])

            for element in form_elements:
                # Skip elements without names
                if not element.get('name'):
                    continue

                field_name = element.get('name')

                # Identify Likert scale fields (radio buttons in groups)
                if element.name == 'input' and element.get('type') == 'radio':
                    self._field_types[field_name] = FIELD_TYPE_LIKERT

                # Identify ranking fields (selects with ranking in data attribute or name)
                elif element.name == 'select' and ('rank' in field_name or element.get('data-ranking-group')):
                    self._field_types[field_name] = FIELD_TYPE_RANKING

                    # Extract ranking group information
                    ranking_group = element.get('data-ranking-group')
                    if ranking_group:
                        # Find all selects in this group to determine max rank
                        group_selects = soup.find_all('select', attrs={'data-ranking-group': ranking_group})
                        self._known_ranking_groups[ranking_group] = len(group_selects)

                # Identify trait fields (selects for low/medium/high)
                elif element.name == 'select':
                    # Check if this select has low/medium/high options
                    options = element.find_all('option')
                    option_values = [opt.get('value', '').lower() for opt in options if opt.get('value')]

                    # If it has low/medium/high options, it's likely a trait field
                    if all(val in ['low', 'medium', 'high'] for val in option_values if val):
                        self._field_types[field_name] = FIELD_TYPE_TRAIT
                    # Otherwise, check if it's a ranking field by name pattern
                    elif 'rank' in field_name:
                        self._field_types[field_name] = FIELD_TYPE_RANKING

                # Identify text fields (textareas)
                elif element.name == 'textarea':
                    self._field_types[field_name] = FIELD_TYPE_TEXT

            print(f"Parsed {len(self._field_types)} fields from form HTML")

        except Exception as e:
            print(f"Error parsing form HTML: {str(e)}")

    def get_field_type(self, field_name, field_value=''):
        """
        Determine field type based on field name and value.
        Uses stored metadata or pattern detection.

        Args:
            field_name: The name of the form field
            field_value: The value to analyze

        Returns:
            str: Field type constant
        """
        # Check if we already know this field's type
        if field_name in self._field_types:
            return self._field_types[field_name]

        # Check for pattern matches in field name
        for pattern, field_type in self._field_patterns.items():
            if field_name.startswith(pattern):
                return field_type

        # Try to determine type from value
        if isinstance(field_value, str):
            # Check for Likert scale values (1-3)
            if field_value in ['1', '2', '3']:
                return FIELD_TYPE_LIKERT

            # Check for trait values (low/medium/high)
            if field_value.lower() in ['low', 'medium', 'high']:
                return FIELD_TYPE_TRAIT

            # Longer text is probably free text
            if len(field_value) > 20:
                return FIELD_TYPE_TEXT

        # Default to other
        return FIELD_TYPE_OTHER

    def get_ranking_group_max(self, group_name):
        """
        Get the maximum rank for a ranking group.

        Args:
            group_name: The ranking group name

        Returns:
            int: The maximum rank value
        """
        return self._known_ranking_groups.get(group_name, 4)  # Default to 4

    def get_ranking_info(self, field_name):
        """
        Try to determine ranking group and max rank from field name.

        Args:
            field_name: The field name to analyze

        Returns:
            tuple: (group_name, max_rank) or (None, None) if not found
        """
        if not field_name.startswith('rank_'):
            return None, None

        # Extract group from data attributes if available
        for group_name, max_rank in self._known_ranking_groups.items():
            # Simple pattern matching for now
            if group_name in field_name:
                return group_name, max_rank

        # If we can't determine the group but it's a ranking field,
        # use a reasonable default
        return 'unknown_group', 4

    def is_likert_field(self, field_name, field_value=''):
        """Check if a field is a Likert scale field."""
        return self.get_field_type(field_name, field_value) == FIELD_TYPE_LIKERT

    def is_ranking_field(self, field_name, field_value=''):
        """Check if a field is a ranking field."""
        return self.get_field_type(field_name, field_value) == FIELD_TYPE_RANKING

    def is_trait_field(self, field_name, field_value=''):
        """Check if a field is a trait field."""
        return self.get_field_type(field_name, field_value) == FIELD_TYPE_TRAIT

    def is_text_field(self, field_name, field_value=''):
        """Check if a field is a text field."""
        return self.get_field_type(field_name, field_value) == FIELD_TYPE_TEXT