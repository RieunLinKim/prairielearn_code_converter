from bs4 import BeautifulSoup

input_path = "../sample_questions/4/Quiz 1_102DF_Fa2022.problem"
output_path = "../sample_questions/4/Quiz 1_102DF_Fa2022.xml"

with open(input_path, "r", encoding="utf-8") as f:
    html = f.read()

# Parse with BeautifulSoup
soup = BeautifulSoup(html, "html.parser")

# Remove script and style tags (optional)
for tag in soup(["script", "style"]):
    tag.decompose()

# Get the body content
body_content = soup.body or soup

# Wrap in <problem> root
xml_content = f'<?xml version="1.0" encoding="UTF-8"?>\n<problem>\n{body_content.decode_contents()}\n</problem>'

with open(output_path, "w", encoding="utf-8") as f:
    f.write(xml_content)

print(f"Converted to {output_path}")