import pdfplumber
import re
from pdfminer.high_level import extract_text

def read(pdf_path, nlp):

    text_with_tables = ""
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            # Extract tables first
            table_per_page = page.extract_tables()
            if(len(table_per_page) > 0):
                tables.append(table_per_page)
            # # Format tables as text
            for table in tables:
                for row in table:
                    for a_row in row:
                        # print(a_row)
            #         # Filter None values and join cells with tabs
                #     print(row)
                        row_text = "\t".join([cell[0] if cell else "" for cell in a_row])
                        text_with_tables += row_text + "\n"
                    text_with_tables += "\n"  # Extra line between tables
                
            #     # Extract the remaining text
            text = page.extract_text()
            if text:
                text_with_tables += text + "\n\n"
    text = re.sub(r'\s+', ' ', text_with_tables)  # Normalize whitespace
    text = re.sub(r'(\d) - ', r'\1 - ', text_with_tables)
    return nlp(text)

def read_for_maintenance(pdf_path, nlp):
    text4 = extract_text(pdf_path)
    return nlp(text4)