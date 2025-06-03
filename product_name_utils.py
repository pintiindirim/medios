# # product_name_utils.py
# import urllib.parse
# import re
# HTML_SUFFIX_PATTERN = re.compile(r'\.html$')
# GB_PATTERN = re.compile(r'(\d+)\s*[Gg][Bb]')
# AKILLI_TELEFON_PATTERN = re.compile(r'\bAkıllı Telefon\b', flags=re.IGNORECASE)
# EXTRA_SPACES_PATTERN = re.compile(r'\s+')
# def extract_product_name_from_url(url):
#     parsed = urllib.parse.urlparse(url)
#     parts = parsed.path.split('/')
#     if len(parts) >= 4:
#         product_part = parts[3]
#         product_part = HTML_SUFFIX_PATTERN.sub('', product_part)
#         product_part = product_part.lstrip('_')
#         parts_dash = product_part.split('-')
#         if len(parts_dash) >= 2:
#             parts_dash = parts_dash[:-2]
#         processed_tokens = [
#             "iphone" if token.lower() == "iphone" else token.title()
#             for token in parts_dash if token.lower() != "apple"
#         ]
#         return " ".join(processed_tokens)
#     return ""
# def turkishize(text):
#     mapping = {
#         "Akilli": "Akıllı",
#         "akilli": "akıllı",
#         "Sari": "Sarı",
#         "sari": "sarı",
#         "kirmizi": "kırmızı",
#         "Kirmizi": "Kırmızı",
#     }
#     for eng, tr in mapping.items():
#         text = text.replace(eng, tr)
#     return text
# def adjust_product_name_for_akakce(text):
#     text = turkishize(text)
#     text = GB_PATTERN.sub(r'\1 GB', text)
#     text = AKILLI_TELEFON_PATTERN.sub('', text)
#     text = EXTRA_SPACES_PATTERN.sub(' ', text).strip()
#     return text