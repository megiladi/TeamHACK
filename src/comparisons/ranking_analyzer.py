def compare_rankings(rank1, rank2, max_rank):
    """
    Compare two ranking values with dynamic threshold based on range.
    Uses simplified three-state classification: aligned, discuss, high_priority.

    Args:
        rank1: First user's ranking
        rank2: Second user's ranking
        max_rank: The maximum possible ranking (how many options total)

    Returns:
        dict: Comparison result with assessment
    """
    try:
        r1 = int(rank1)
        r2 = int(rank2)

        difference = abs(r1 - r2)

        # Calculate percentage difference relative to max_rank
        percentage_difference = (difference / max_rank) * 100

        # Determine assessment based on multiple factors
        assessment = "aligned"  # Default

        # For small ranking ranges (1-3)
        if max_rank <= 3:
            # Only flag if difference is 2 in a small range (max difference)
            if difference >= 2:
                assessment = "discuss"
                # If one person's #1 is another's #3 in a 3-point scale, it's significant
                if (r1 == 1 and r2 == max_rank) or (r2 == 1 and r1 == max_rank):
                    assessment = "high_priority"

        # For medium ranking ranges (4-6)
        elif max_rank <= 6:
            # Major differences for important items
            if difference >= 3 or ((r1 <= 2 or r2 <= 2) and difference >= 2):
                assessment = "discuss"
                # If one's top priority is another's bottom priority
                if (r1 == 1 and r2 >= max_rank - 1) or (r2 == 1 and r1 >= max_rank - 1):
                    assessment = "high_priority"

        # For large ranking ranges (7+)
        else:
            # Only flag significant differences
            if difference >= max_rank // 3:
                assessment = "discuss"
                # If one's top priority is another's bottom half
                if (r1 == 1 and r2 >= max_rank // 2) or (r2 == 1 and r1 >= max_rank // 2):
                    assessment = "high_priority"

        # Additional check: if difference is small (1) and neither is top priority (1-2),
        # then it's aligned regardless of range
        if difference == 1 and r1 > 2 and r2 > 2:
            assessment = "aligned"

        return {
            'rank1': r1,
            'rank2': r2,
            'difference': difference,
            'percentage_difference': round(percentage_difference, 1),
            'assessment': assessment
        }
    except (ValueError, TypeError):
        return {
            'rank1': rank1,
            'rank2': rank2,
            'error': 'Invalid ranking values',
            'assessment': "aligned"  # Default to aligned for error cases
        }