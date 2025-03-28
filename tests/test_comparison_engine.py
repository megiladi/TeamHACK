import os
import unittest
import json
from src.comparisons.comparison_engine import ComparisonEngine
from src.comparisons.likert_analyzer import compare_likert_scales
from src.comparisons.ranking_analyzer import compare_rankings
from src.comparisons.low_medium_high_analyzer import compare_low_medium_high_traits
from src.forms.form_metadata import FormMetadata, FIELD_TYPE_LIKERT, FIELD_TYPE_RANKING, FIELD_TYPE_TRAIT, \
    FIELD_TYPE_TEXT

# Set testing environment
os.environ['TESTING'] = 'True'


class TestComparisonEngine(unittest.TestCase):
    """Test cases for the comparison engine and its components."""

    def setUp(self):
        """Set up for each test."""
        self.comparison_engine = ComparisonEngine()

    def test_likert_analyzer(self):
        """Test Likert scale comparison."""
        # Test aligned values
        result = compare_likert_scales('2', '2')
        self.assertEqual(result['assessment'], 'aligned')
        self.assertEqual(result['difference'], 0)

        # Test minor difference (not enough to flag)
        result = compare_likert_scales('1', '2')
        self.assertEqual(result['assessment'], 'aligned')
        self.assertEqual(result['difference'], 1)

        # Test significant difference (should be flagged as "discuss")
        result = compare_likert_scales('1', '3')
        self.assertEqual(result['assessment'], 'discuss')
        self.assertEqual(result['difference'], 2)

        # Test invalid input handling
        result = compare_likert_scales('invalid', '3')
        self.assertTrue('error' in result)
        self.assertEqual(result['assessment'], 'aligned')  # Default for errors

    def test_ranking_analyzer(self):
        """Test ranking comparison."""
        # Test identical rankings
        result = compare_rankings('1', '1', 6)
        self.assertEqual(result['assessment'], 'aligned')
        self.assertEqual(result['difference'], 0)

        # Test small difference in low priority items (3,4)
        result = compare_rankings('3', '4', 6)
        self.assertEqual(result['assessment'], 'aligned')

        # Test critical difference: Rank 1 vs. Rank 6 (top vs. bottom)
        result = compare_rankings('1', '6', 6)
        self.assertEqual(result['assessment'], 'high_priority')
        self.assertEqual(result['difference'], 5)

        # Test smaller range with significant difference
        result = compare_rankings('1', '3', 3)
        self.assertEqual(result['assessment'], 'high_priority')

        # Test invalid input handling
        result = compare_rankings('invalid', '3', 6)
        self.assertTrue('error' in result)

    def test_trait_analyzer(self):
        """Test trait (low/medium/high) comparison."""
        # Test identical traits
        result = compare_low_medium_high_traits('medium', 'medium')
        self.assertEqual(result['assessment'], 'aligned')
        self.assertEqual(result['difference'], 0)

        # Test adjacent traits (not enough to flag)
        result = compare_low_medium_high_traits('low', 'medium')
        self.assertEqual(result['assessment'], 'aligned')
        self.assertEqual(result['difference'], 1)

        # Test opposite traits (should be flagged)
        result = compare_low_medium_high_traits('low', 'high')
        self.assertEqual(result['assessment'], 'discuss')
        self.assertEqual(result['difference'], 2)

        # Test case insensitivity
        result = compare_low_medium_high_traits('HIGH', 'high')
        self.assertEqual(result['assessment'], 'aligned')
        self.assertEqual(result['difference'], 0)

        # Test invalid input handling
        result = compare_low_medium_high_traits('invalid', 'low')
        self.assertTrue('error' in result)

    def test_form_metadata(self):
        """Test form metadata field type detection."""
        form_metadata = FormMetadata()

        # Test Likert field detection
        self.assertEqual(form_metadata.get_field_type('timing_preference', '2'), FIELD_TYPE_LIKERT)

        # Test ranking field detection
        self.assertEqual(form_metadata.get_field_type('rank_opposing', '1'), FIELD_TYPE_RANKING)

        # Test trait field detection
        self.assertEqual(form_metadata.get_field_type('ocean_openness', 'high'), FIELD_TYPE_TRAIT)

        # Test text field detection
        self.assertEqual(
            form_metadata.get_field_type('professional_goals', 'A long text response that exceeds twenty characters'),
            FIELD_TYPE_TEXT)

    def test_compare_forms_basic(self):
        """Test basic form comparison functionality."""
        # Simple form data with some matching and some different values
        form1 = {
            'timing_preference': '1',  # Early bird
            'working_hours': '2',  # Balanced
            'ocean_openness': 'high',
            'rank_opposing': '1',
            'professional_goals': 'I want to become a team lead'
        }

        form2 = {
            'timing_preference': '3',  # Night owl
            'working_hours': '2',  # Balanced
            'ocean_openness': 'medium',
            'rank_opposing': '3',
            'professional_goals': 'I want to develop technical expertise'
        }

        # Convert to JSON strings for the engine
        form1_json = json.dumps(form1)
        form2_json = json.dumps(form2)

        # Run comparison
        result = self.comparison_engine.compare_forms(form1_json, form2_json)

        # Check basic structure
        self.assertTrue('likert_scales' in result)
        self.assertTrue('traits' in result)
        self.assertTrue('rankings' in result)
        self.assertTrue('free_text' in result)
        self.assertTrue('conflict_summary' in result)

        # Check conflicts identified
        self.assertTrue(result['conflict_summary']['total_conflicts'] > 0)

        # Check timing_preference was flagged (1 vs 3 should be a conflict)
        timing_conflicts = [conflict for conflict in result['conflict_summary']['conflict_areas']
                            if conflict['field'] == 'timing_preference']
        self.assertTrue(len(timing_conflicts) > 0)

        # Check working_hours was NOT flagged (both are 2)
        working_hours_conflicts = [conflict for conflict in result['conflict_summary']['conflict_areas']
                                   if conflict['field'] == 'working_hours']
        self.assertEqual(len(working_hours_conflicts), 0)

    def test_compare_forms_empty(self):
        """Test comparison with empty forms."""
        empty_form = {}
        empty_form_json = json.dumps(empty_form)

        result = self.comparison_engine.compare_forms(empty_form_json, empty_form_json)

        # Check that it doesn't crash and returns expected structure
        self.assertEqual(result['conflict_summary']['total_conflicts'], 0)
        self.assertEqual(len(result['conflict_summary']['conflict_areas']), 0)

    def test_compare_forms_partial_overlap(self):
        """Test comparison with partial field overlap."""
        form1 = {
            'timing_preference': '2',
            'working_hours': '1'
        }

        form2 = {
            'working_hours': '3',
            'relax_preference': '2'
        }

        form1_json = json.dumps(form1)
        form2_json = json.dumps(form2)

        result = self.comparison_engine.compare_forms(form1_json, form2_json)

        # Check that it only compares common fields
        working_hours_conflicts = [conflict for conflict in result['conflict_summary']['conflict_areas']
                                   if conflict['field'] == 'working_hours']
        self.assertTrue(len(working_hours_conflicts) > 0)

        # Fields unique to each form should not appear in conflicts
        timing_conflicts = [conflict for conflict in result['conflict_summary']['conflict_areas']
                            if conflict['field'] == 'timing_preference']
        relax_conflicts = [conflict for conflict in result['conflict_summary']['conflict_areas']
                           if conflict['field'] == 'relax_preference']

        self.assertEqual(len(timing_conflicts), 0)
        self.assertEqual(len(relax_conflicts), 0)


if __name__ == '__main__':
    unittest.main()