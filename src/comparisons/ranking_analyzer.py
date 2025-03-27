def compare_rankings(rank1, rank2, max_rank):
    """
    Compare two ranking values with dynamic threshold based on range.

    Args:
        rank1: First user's ranking
        rank2: Second user's ranking
        max_rank: The maximum possible ranking (how many options total)

    Returns:
        dict: Comparison result with conflict flag
    """
    try:
        r1 = int(rank1)
        r2 = int(rank2)

        difference = abs(r1 - r2)

        # Dynamic threshold: flag if difference is more than 1/3 (rounded down) of the range
        threshold = max(1, max_rank // 3)
        is_conflict = difference >= threshold

        # For highest priority items (rank 1 or 2), be more sensitive
        is_high_priority_conflict = (r1 <= 2 or r2 <= 2) and difference >= threshold - 1

        return {
            'rank1': r1,
            'rank2': r2,
            'difference': difference,
            'is_conflict': is_conflict,
            'is_high_priority_conflict': is_high_priority_conflict
        }
    except (ValueError, TypeError):
        return {
            'rank1': rank1,
            'rank2': rank2,
            'error': 'Invalid ranking values'
        }