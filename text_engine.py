import re

replacement_dict = {
    'ä': 'ae',
    'ö': 'oe',
    'ü': 'ue',
    'ß': 'ss',
    '/': ' ',
    '\\': ' ',
    '-': ' ',
}

table = str.maketrans(replacement_dict)

def normalize(text):
    lower_text = text.lower()
    translated_text = lower_text.translate(table)
    no_whitespace_text = re.sub(r'\s+', '_', translated_text).strip(' ')
    no_underscore_text = re.sub(r'_+', '_', no_whitespace_text).strip('_')
    normalized_text = re.sub(r'[^a-z0-9_]', '', no_whitespace_text)

    return normalized_text