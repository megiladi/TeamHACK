import json
from .likert_analyzer import compare_likert_scales
from .ranking_analyzer import compare_rankings
from .low_medium_high_analyzer import compare_low_medium_high_traits
from .text_analyzer import TextAnalyzer
from src.forms.form_metadata import FormMetadata, FIELD_TYPE_LIKERT, FIELD_TYPE_RANKING, FIELD_TYPE_TRAIT, FIELD_TYPE_TEXT, FIELD_TYPE_OTHER

class ComparisonEngine:
    """
    Dynamic comparison engine that adapts to form changes.
    Uses pattern detection for field types without hardcoded field lists.
    """

    def __init__(self, form_html_path=None):
        """
        Initialize the comparison engine components.

        Args:
            form_html_path: Optional path to HTML form file for metadata extraction
        """
        self.form_metadata = FormMetadata(form_html_path)
        self.text_analyzer = TextAnalyzer()

    def compare_forms(self, form1_content, form2_content):
        """
        Compare two completed forms to identify potential conflicts.
        Dynamically detects field types without relying on hardcoded lists.

        Args:
            form1_content: JSON string or dict of first user's form
            form2_content: JSON string or dict of second user's form

        Returns:
            dict: Structured comparison results with conflict areas
        """
        # Convert JSON strings to dicts if needed
        form1 = json.loads(form1_content) if isinstance(form1_content, str) else form1_content
        form2 = json.loads(form2_content) if isinstance(form2_content, str) else form2_content

        # Initialize results structure
        results = {
            'likert_scales': {},
            'rankings': {},
            'traits': {},
            'free_text': {},
            'conflict_summary': {
                'total_conflicts': 0,
                'high_priority_conflicts': 0,
                'conflict_areas': []
            }
        }

        # Process each common field in both forms
        common_fields = set(form1.keys()).intersection(set(form2.keys()))
        for field_name in common_fields:
            value1 = form1.get(field_name)
            value2 = form2.get(field_name)

            # Skip empty values
            if not value1 or not value2:
                continue

            # Determine field type and analyze accordingly
            field_type = self.form_metadata.get_field_type(field_name, value1)

            if field_type == FIELD_TYPE_LIKERT:
                self._analyze_likert_field(field_name, value1, value2, results)

            elif field_type == FIELD_TYPE_RANKING:
                self._analyze_ranking_field(field_name, value1, value2, results)

            elif field_type == FIELD_TYPE_TRAIT:
                self._analyze_trait_field(field_name, value1, value2, results)

            elif field_type == FIELD_TYPE_TEXT:
                self._analyze_text_field(field_name, value1, value2, results)

        # Generate overall assessment
        self._generate_overall_assessment(results)

        return results

    def _analyze_likert_field(self, field_name, value1, value2, results):
        """Analyze a Likert scale field."""
        results['likert_scales'][field_name] = compare_likert_scales(value1, value2)

        # Track conflicts
        if results['likert_scales'][field_name].get('is_conflict'):
            self._add_conflict(results, 'likert', field_name,
                               results['likert_scales'][field_name]['difference'])

    def _analyze_ranking_field(self, field_name, value1, value2, results):
        """Analyze a ranking field."""
        # Get ranking group and max rank
        group, max_rank = self.form_metadata.get_ranking_info(field_name)

        # Create group if it doesn't exist
        if group not in results['rankings']:
            results['rankings'][group] = {}

        # Compare the rankings
        results['rankings'][group][field_name] = compare_rankings(value1, value2, max_rank)

        # Track conflicts
        if results['rankings'][group][field_name].get('is_conflict'):
            self._add_conflict(
                results, 'ranking', field_name,
                results['rankings'][group][field_name]['difference'],
                group=group,
                is_high_priority=results['rankings'][group][field_name].get('is_high_priority_conflict', False)
            )

            if results['rankings'][group][field_name].get('is_high_priority_conflict'):
                results['conflict_summary']['high_priority_conflicts'] += 1

    def _analyze_trait_field(self, field_name, value1, value2, results):
        """Analyze a trait field (low/medium/high)."""
        results['traits'][field_name] = compare_low_medium_high_traits(value1, value2)

        # Track conflicts
        if results['traits'][field_name].get('is_conflict'):
            self._add_conflict(results, 'trait', field_name,
                               results['traits'][field_name]['difference'])

    def _analyze_text_field(self, field_name, value1, value2, results):
        """Analyze a free text field using the LLM."""
        results['free_text'][field_name] = self.text_analyzer.analyze_text_similarity(value1, value2)

        # Track conflicts
        if results['free_text'][field_name].get('has_conflicts'):
            self._add_conflict(
                results, 'free_text', field_name,
                conflict_level=results['free_text'][field_name].get('conflict_level', 'unknown')
            )

    def _add_conflict(self, results, type_name, field_name, difference=None, group=None,
                      is_high_priority=False, conflict_level=None):
        """Add a conflict to the summary."""
        results['conflict_summary']['total_conflicts'] += 1

        conflict = {
            'type': type_name,
            'field': field_name
        }

        if difference is not None:
            conflict['difference'] = difference

        if group:
            conflict['group'] = group

        if is_high_priority:
            conflict['is_high_priority'] = True

        if conflict_level:
            conflict['conflict_level'] = conflict_level

        results['conflict_summary']['conflict_areas'].append(conflict)

    def _generate_overall_assessment(self, results):
        """Generate overall assessment based on conflicts found."""
        if results['conflict_summary']['high_priority_conflicts'] > 0:
            results['conflict_summary']['overall_assessment'] = "High potential for conflict in key areas"
        elif results['conflict_summary']['total_conflicts'] > 5:
            results['conflict_summary']['overall_assessment'] = "Moderate potential for conflict"
        elif results['conflict_summary']['total_conflicts'] > 0:
            results['conflict_summary']['overall_assessment'] = "Some areas of potential difference"
        else:
            results['conflict_summary']['overall_assessment'] = "Highly compatible"