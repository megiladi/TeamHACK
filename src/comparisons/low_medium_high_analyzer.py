def compare_low_medium_high_traits(trait1, trait2):
    """
    Compare general low/medium/high trait values.

    Args:
        trait1: First user's trait value (low/medium/high)
        trait2: Second user's trait value (low/medium/high)

    Returns:
        dict: Comparison result with conflict flag
    """
    # Map string values to numeric for comparison
    value_map = {"low": 1, "medium": 2, "high": 3}

    try:
        v1 = value_map.get(trait1.lower(), 0)
        v2 = value_map.get(trait2.lower(), 0)

        difference = abs(v1 - v2)

        # Only flag maximum differences (low vs high)
        is_conflict = difference >= 2

        return {
            'trait1': trait1,
            'trait2': trait2,
            'difference': difference,
            'is_conflict': is_conflict
        }
    except (AttributeError, TypeError):
        return {
            'trait1': trait1,
            'trait2': trait2,
            'error': 'Invalid trait values'
        }