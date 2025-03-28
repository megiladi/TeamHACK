def compare_likert_scales(value1, value2):
    """
    Compare two Likert scale values (1-3) and determine if they indicate potential conflict.
    Uses simplified three-state classification: aligned, discuss, high_priority.

    Args:
        value1: First user's response (1-3)
        value2: Second user's response (1-3)

    Returns:
        dict: Comparison result with assessment
    """
    try:
        v1 = int(value1)
        v2 = int(value2)

        difference = abs(v1 - v2)

        # Simple logic: only max difference (2 on a 3-point scale) gets flagged as "discuss"
        if difference >= 2:
            assessment = "discuss"
        else:
            assessment = "aligned"

        return {
            'value1': v1,
            'value2': v2,
            'difference': difference,
            'assessment': assessment
        }
    except (ValueError, TypeError):
        # Handle invalid inputs
        return {
            'value1': value1,
            'value2': value2,
            'error': 'Invalid Likert scale values',
            'assessment': "aligned"  # Default to aligned for error cases
        }