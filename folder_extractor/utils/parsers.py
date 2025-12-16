"""
Parsing utilities for command line arguments and user input.

Extracts parsing logic from the main module for better
testability and reusability.
"""
from typing import List, Optional


def parse_file_types(type_string: Optional[str]) -> Optional[List[str]]:
    """
    Parse file type filter string.
    
    Args:
        type_string: Comma-separated file types (e.g., "pdf,jpg,png")
    
    Returns:
        List of file extensions with dots (e.g., [".pdf", ".jpg", ".png"])
        or None if input is empty
    
    Examples:
        >>> parse_file_types("pdf,jpg")
        ['.pdf', '.jpg']
        >>> parse_file_types(".pdf,.jpg")
        ['.pdf', '.jpg']
        >>> parse_file_types("*.pdf,*.jpg")
        ['.pdf', '.jpg']
        >>> parse_file_types("")
        None
    """
    if not type_string or type_string.strip() == "":
        return None
    
    types = []
    for t in type_string.split(','):
        t = t.strip().lower()
        if t:
            # Remove common prefixes
            if t.startswith('*.'):
                t = t[2:]
            elif t.startswith('*'):
                t = t[1:]
            
            # Ensure dot prefix
            if not t.startswith('.'):
                t = '.' + t
            
            types.append(t)
    
    return types if types else None


def parse_domains(domain_string: Optional[str]) -> Optional[List[str]]:
    """
    Parse domain filter string.
    
    Args:
        domain_string: Comma-separated domains (e.g., "youtube.com,github.com")
    
    Returns:
        List of domains without www prefix (e.g., ["youtube.com", "github.com"])
        or None if input is empty
    
    Examples:
        >>> parse_domains("youtube.com,github.com")
        ['youtube.com', 'github.com']
        >>> parse_domains("www.youtube.com")
        ['youtube.com']
        >>> parse_domains("")
        None
    """
    if not domain_string or domain_string.strip() == "":
        return None
    
    domains = []
    for d in domain_string.split(','):
        d = d.strip().lower()
        if d:
            # Remove www prefix
            if d.startswith('www.'):
                d = d[4:]
            domains.append(d)
    
    return domains if domains else None


def parse_depth(depth_string: str) -> int:
    """
    Parse depth argument.
    
    Args:
        depth_string: Depth value as string
    
    Returns:
        Integer depth value (0 means unlimited)
    
    Raises:
        ValueError: If depth is not a valid non-negative integer
    """
    try:
        depth = int(depth_string)
        if depth < 0:
            raise ValueError("Tiefe muss eine positive Zahl sein")
        return depth
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(f"Ungültige Tiefe: '{depth_string}' ist keine Zahl")
        raise