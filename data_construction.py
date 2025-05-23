import spacy
from read_pdf_with_tables import read
from patterns import get_bridge_id, match_component_to_maintence_needs,get_sections, find_maintenance_sections, get_section_boundaries, get_table_and_desc_boundaries
import json

if __name__ == "__main__":
    nlp = spacy.load("en_core_web_lg")

    pdf_path = "reports/sample report.pdf"
    doc = read(pdf_path, nlp=nlp)
    sections, bridge_id,components = get_sections(doc, nlp)
    needs = find_maintenance_sections(pdf_path, nlp=nlp)
    print(json.dumps(match_component_to_maintence_needs(components,needs , sections, bridge_id, nlp), indent=4))
    print("hello")