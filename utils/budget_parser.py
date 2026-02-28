import re

def parse_budget(budget_string):
    """
    Parse budget string and return tier classification.
    
    Args:
        budget_string: Budget in format like "₹50,000", "$100", "EUR 200"
    
    Returns:
        str: "budget", "mid-range", or "luxury"
    """
    if not budget_string:
        return "mid-range"
    
    # Extract numeric amount
    amount_match = re.search(r'[\d,]+', budget_string.replace(',', ''))
    if not amount_match:
        return "mid-range"
    
    try:
        amount = int(amount_match.group())
    except:
        return "mid-range"
    
    # Determine tier based on currency
    if "₹" in budget_string or "INR" in budget_string:
        # Indian Rupees
        if amount < 4000:
            return "budget"
        elif amount < 12000:
            return "mid-range"
        else:
            return "luxury"
    elif "$" in budget_string or "USD" in budget_string:
        # US Dollars
        if amount < 50:
            return "budget"
        elif amount < 150:
            return "mid-range"
        else:
            return "luxury"
    elif "€" in budget_string or "EUR" in budget_string:
        # Euros
        if amount < 45:
            return "budget"
        elif amount < 140:
            return "mid-range"
        else:
            return "luxury"
    elif "£" in budget_string or "GBP" in budget_string:
        # British Pounds
        if amount < 40:
            return "budget"
        elif amount < 120:
            return "mid-range"
        else:
            return "luxury"
    else:
        # Default to USD thresholds
        if amount < 50:
            return "budget"
        elif amount < 150:
            return "mid-range"
        else:
            return "luxury"
