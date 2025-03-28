def compare_rankings(rank1, rank2, max_rank):
    """
    Compare two ranking values with dynamic threshold based on range.
    Less sensitive for small differences, especially in larger ranking ranges.

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

        # For values ranked close to #1 (top priority), even small differences matter more
        top_priority_threshold = max(1, max_rank // 4)  # More lenient threshold

        # For general rankings, be more lenient
        general_threshold = max(2, max_rank // 3)  # At least a difference of 2 for conflict

        # Calculate percentage difference relative to max_rank
        percentage_difference = (difference / max_rank) * 100

        # Determine if this is a conflict based on multiple factors
        is_conflict = False
        is_high_priority_conflict = False

        # More sophisticated conflict detection
        if max_rank <= 3:
            # For small ranking ranges (1-3)
            is_conflict = difference >= 2  # Only flag if difference is 2 or more in a small range
            is_high_priority_conflict = (r1 == 1 or r2 == 1) and difference >= 2
        elif max_rank <= 6:
            # For medium ranking ranges (4-6)
            # Only flag as conflict if difference is significant or involves top priorities
            is_conflict = difference >= 3 or ((r1 <= 2 or r2 <= 2) and difference >= 2)
            is_high_priority_conflict = (r1 == 1 or r2 == 1) and difference >= 2
        else:
            # For large ranking ranges
            is_conflict = difference >= general_threshold
            is_high_priority_conflict = (r1 <= 2 or r2 <= 2) and difference >= top_priority_threshold

        # Additional check: if difference is small (1) and neither is top priority (1-2),
        # then it's not a conflict regardless of range
        if difference == 1 and r1 > 2 and r2 > 2:
            is_conflict = False
            is_high_priority_conflict = False

        # Special case for top priority (1) vs very low priority (near max)
        if (r1 == 1 and r2 >= max_rank - 1) or (r2 == 1 and r1 >= max_rank - 1):
            is_conflict = True
            is_high_priority_conflict = True

        conflict_level = "none"
        if is_high_priority_conflict:
            conflict_level = "high"
        elif is_conflict:
            conflict_level = "medium" if percentage_difference > 30 else "low"

        return {
            'rank1': r1,
            'rank2': r2,
            'difference': difference,
            'percentage_difference': round(percentage_difference, 1),
            'is_conflict': is_conflict,
            'is_high_priority_conflict': is_high_priority_conflict,
            'conflict_level': conflict_level
        }
    except (ValueError, TypeError):
        return {
            'rank1': rank1,
            'rank2': rank2,
            'error': 'Invalid ranking values',
            'conflict_level': "none"
        }