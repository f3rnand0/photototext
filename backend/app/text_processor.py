import re


def clean_line_breaks(text: str) -> str:
    """
    Remove line breaks caused by narrow page width.
    Keep meaningful paragraph breaks.
    
    Rules:
    - Join lines if previous line doesn't end with sentence-ending punctuation
    - Join lines if next line starts with lowercase letter
    - Keep breaks if significant spacing or punctuation + uppercase start
    """
    if not text or not text.strip():
        return text
    
    lines = text.split('\n')
    cleaned_lines = []
    current_paragraph = []
    
    # Sentence ending punctuation
    sentence_enders = '.!?'
    
    for i, line in enumerate(lines):
        line = line.rstrip()
        if not line:
            # Empty line = intentional paragraph break
            if current_paragraph:
                cleaned_lines.append(' '.join(current_paragraph))
                current_paragraph = []
            continue
        
        # Check if line ends with sentence terminator
        ends_with_punct = line[-1] in sentence_enders if line else False
        
        # Check if next line exists and starts with lowercase
        next_starts_lower = False
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and next_line[0].islower():
                next_starts_lower = True
        
        if ends_with_punct and not next_starts_lower:
            # Likely end of sentence/paragraph
            current_paragraph.append(line)
            cleaned_lines.append(' '.join(current_paragraph))
            current_paragraph = []
        else:
            # Likely wrapped line - add to current paragraph
            current_paragraph.append(line)
    
    # Don't forget last paragraph
    if current_paragraph:
        cleaned_lines.append(' '.join(current_paragraph))
    
    # Join paragraphs with double newline
    result = '\n\n'.join(cleaned_lines)
    
    # Clean up multiple spaces
    result = re.sub(r' +', ' ', result)
    
    return result.strip()