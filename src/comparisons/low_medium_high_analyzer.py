def compare_low_medium_high_traits(trait1, trait2):
    """
    Compare general low/medium/high trait values.
    Uses simplified three-state classification: aligned, discuss, high_priority.

    Args:
        trait1: First user's trait value (low/medium/high)
        trait2: Second user's trait value (low/medium/high)

    Returns:
        dict: Comparison result with assessment
    """
    # Map string values to numeric for comparison
    value_map = {"low": 1, "medium": 2, "high": 3}

    try:
        v1 = value_map.get(str(trait1).lower(), 0)
        v2 = value_map.get(str(trait2).lower(), 0)

        difference = abs(v1 - v2)

        # Only flag maximum differences (low vs high) as discuss
        # These are rarely high priority as people can adapt
        if difference >= 2:
            assessment = "discuss"
        else:
            assessment = "aligned"

        return {
            'trait1': trait1,
            'trait2': trait2,
            'difference': difference,
            'assessment': assessment
        }
    except (AttributeError, TypeError):
        return {
            'trait1': trait1,
            'trait2': trait2,
            'error': 'Invalid trait values',
            'assessment': "aligned"  # Default to aligned for error cases
        }