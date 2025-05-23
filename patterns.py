import re
from regex_patterns import units_regex, materials, get_component_pattern, extract_component_values, extract_defects, values_pattern, units_pattern, id_pattern
from helpers import get_desc_text
from read_pdf_with_tables import read_for_maintenance

def get_bridge_id(doc):
    pattern = f"Structure\s+#(\d+)"
    matches = re.finditer(pattern, doc.text, re.IGNORECASE)
    structure_numbers = []
    for match in matches:
        if match.group(1) not in structure_numbers:
            structure_numbers.append(match.group(1))
    bridge_id = structure_numbers[0] if len(structure_numbers) == 1 else "Unknown"
    return bridge_id

def get_section_boundaries(doc):
    lines = doc.text.split('\n')
    section_boundaries = []

    section_headers = [
            "deck", "approach", "superstructure", "substructure", 
            "channel", "general observation","channel profile",
        ]
    for i, line in enumerate(lines):
        clean_line = line.strip().lower()
        if not clean_line:
            continue
        for header in section_headers:
            if clean_line == header:
                section_boundaries.append((i, header.upper()))
                break
    section_boundaries.sort(key=lambda x: x[0])
    return section_boundaries, lines

def get_sections(doc, nlp):
    section_boundaries, lines = get_section_boundaries(doc)
    section= {}
    sections = []

    for i, (line_idx, header) in enumerate(section_boundaries):
        end_idx = section_boundaries[i + 1][0] if  i < len(section_boundaries) - 1 else len(lines)
        
        section = {
            "index": (line_idx, end_idx),
            "content_array": lines[line_idx:end_idx],
            "content": "\n".join(lines[line_idx:end_idx]),
            "header": header
        }
        sections.append(section)
    components = get_table_and_desc_boundaries(sections, nlp)

    return sections, get_bridge_id(doc), components

def get_table_and_desc_boundaries(sections, nlp):
    for section in sections:
        # if "DECK" in section['header'] or "SUPERSTRUCTURE" in section['header'] or "SUBSTRUCTURE" in section['header']: 
        if "DECK" in section['header'] : 
            # print(section['header'])
            if "LF" in section["content"]:
                doc_ = nlp(section["content"])
                lines = doc_.text.split("\n")
                last_table_line = -1
        
                for idx, line in enumerate(lines):
                    # print(re.search(units_regex, line))
                    if re.search(units_regex, line):
                        # print(line)
                        last_table_line = idx
                
                table = lines[:last_table_line+1]
                desc = lines[last_table_line+1:]
                print(section['header'])
                print(lines[last_table_line])  
                print(table)
                print("\n")
                table_text = '\n'.join(table)
                desc_text = '\n'.join(desc)
                # print(get_desc_text(desc_text))
                # print(get_desc_sections(get_desc_text(desc_text)))
                import json
                print(json.dumps(match_components_and_desc(get_component_sections(table_text, nlp), get_desc_sections(get_desc_text(desc_text))), indent=4))
                # get_component_sections(table_text, nlp)
    return match_components_and_desc(get_component_sections(table_text, nlp), get_desc_sections(get_desc_text(desc_text)))

def get_component_sections(table_text, nlp):
    component_sections = []
    doc_t = nlp(table_text)

    matches = list(re.finditer(get_component_pattern(), doc_t.text))
    for i, match in enumerate(matches):
        start_pos = match.start()
            
        # Determine end position (either next component or end of text)
        if i < len(matches) - 1:
            end_pos = matches[i+1].start()
        else:
            end_pos = len(table_text)
            
        # Extract the full section text
        section_text = table_text[start_pos:end_pos].strip()
            
        # Extract just the component name (may include material)
        component_text = match.group(1)
            
        component_sections.append({
                "full_section": section_text,
                "component": component_text,
                "start": start_pos,
                "end": end_pos
           })
    # for comp in component_sections:
    #     print(comp['full_section'])
    #     print("\n")
    return get_component_and_defect_values(component_sections)
    # print(component_sections[0]["full_section"])

def get_component_and_defect_values(component_sections):
    structured_components = []
    for section in component_sections:
        print(section["component"])
        component_data = {
                "text": section["component"],
                "full_section": section["full_section"],
                "defects": []  # Will hold defect information
            }
            
        # Extract ID
        id_match = re.search(id_pattern, section["component"])
        if id_match:
            print(id_match.group(1))
            component_data["id"] = id_match.group(1)
        units_match = re.search(units_pattern, section["full_section"])
        if units_match:
            print(units_match.group(1))
            component_data["units"] = units_match.group(1)
        values_match = re.search(values_pattern, section["full_section"])
        component_data = extract_component_values(section["component"], section["full_section"], component_data)
        component_data = extract_defects(section["full_section"], component_data)
        structured_components.append(component_data)
    return structured_components

def get_desc_sections(desc_text):
    header_pattern = r'(?:([A-Z](?:\.[A-Z])?(?:\.\d+)?(?:\s+-)?|\d+\s+-)\s+([^()]+))(?:\s*\(([^)]+)\))?'

    header_matches = list(re.finditer(header_pattern, desc_text))
        
        # If no headers found, return the whole text as one section
    if not header_matches:
        desc_sections = [{"header": None, "condition_text": None, "condition_rating": None, 
                    "assessment": None, "content": desc_text.strip()}]
        
        # Create sections by finding the text between headers
    desc_sections = []
        
    for i, match in enumerate(header_matches):
            # Combine the prefix and title parts to form the complete header
        prefix = match.group(1).strip() if match.group(1) else ""
        title = match.group(2).strip() if match.group(2) else ""
        header = f"{prefix} {title}".strip()
            
        condition_text = match.group(3).strip() if match.group(3) else None
            
            # Parse the condition and assessment
        condition_rating, assessment = parse_condition(condition_text)
            
            # Find the start of the content (after the header and condition)
        content_start = match.end()
            
            # Find the end of the content (start of next header or end of text)
        if i < len(header_matches) - 1:
            content_end = header_matches[i + 1].start()
        else:
            content_end = len(desc_text)
            
            # Extract the content
        content = desc_text[content_start:content_end].strip()
            
        desc_sections.append({
                "header": header,
                "condition_text": condition_text,
                "condition_rating": condition_rating,
                "assessment": assessment,
                "content": content if len(content) > 5 else ""
            })
    return desc_sections
    

def parse_condition(condition_text):
    """
    Parse condition text to extract rating and assessment description.
    
    Args:
        condition_text (str): The condition text from the header
        
    Returns:
        tuple: (condition_rating, assessment_description)
    """
    if not condition_text:
        return None, None
    
    # Handle "N/A" or "Not Applicable" cases
    if condition_text.upper() in ["N/A", "NOT APPLICABLE"]:
        return "Not Applicable", None
    
    # Handle simple condition ratings without explanations
    if condition_text.upper() in ["SATISFACTORY", "GOOD", "FAIR", "POOR"]:
        return condition_text.upper(), None
    
    # Pattern for conditions with numeric codes: "6 - SATISFACTORY CONDITION - explanation"
    code_pattern = r'(?:(\d+)\s*-\s*)?([A-Z\s]+)(?:\s*-\s*(.+))?'
    match = re.match(code_pattern, condition_text)
    
    if match:
        code = match.group(1)  # Numeric code like "6"
        rating = match.group(2).strip()  # Rating like "SATISFACTORY CONDITION"
        assessment = match.group(3)  # Explanation text
        
        # Normalize rating text (remove "CONDITION" if present)
        rating = rating.replace("CONDITION", "").strip()
        
        return rating, assessment
    
    # Default case - return the whole text as the rating
    return condition_text, None

# Matching components and desc
def extract_component_name(text):
    """
    Extract the core component name from the text, removing ID and material prefixes.
    
    Args:
        text (str): The component text (e.g., "215 Reinforced Concrete Abutment")
        
    Returns:
        str: The core component name (e.g., "Abutment")
    """
    # Remove leading ID number
    text = re.sub(r'^\d+\s+', '', text)
    
    # Remove common material prefixes
    for material in materials:
        text = text.replace(material, '').strip()

    # we will need to extend special cases
    if text == "Open Girder" or text == "Girder":
        text = "Beam"
    if "Bearing" in text:
        text = "Bearing"
    
    # Handle special case for "Wing/Retaining Wall"
    if "Wing" in text and "Wall" not in text:
        text = "Wing/Retaining Wall"
    
    return text

def generate_component_variations(component_name):
    """
    Generate variations of a component name for flexible matching.
    
    Args:
        component_name (str): The core component name
        
    Returns:
        list: List of possible variations of the component name
    """
    variations = [component_name]

    if component_name == "Beam":
        component_names = ["Beam", "Girder"]

        for c_name in component_names:
            variations.append(c_name.lower())
    
        # Handle singular/plural variations
        if c_name.endswith('s'):
            variations.append(c_name[:-1])  # Remove 's'
        else:
            variations.append(c_name + 's')  # Add 's'
            variations.append(c_name + r' \d+')
        variations.append(c_name + r' \d+') 
    else:
    
        # Handle variations with numbers
        variations.append(component_name + r' \d+')  # Component followed by number
        
        # Add lowercase version
        variations.append(component_name.lower())
        
        # Handle singular/plural variations
        if component_name.endswith('s'):
            variations.append(component_name[:-1])  # Remove 's'
        else:
            variations.append(component_name + 's')  # Add 's'
        
        # Handle variations with numbers
        variations.append(component_name + r' \d+')  # Component followed by number
    
    # Handle compound components with slashes
    if '/' in component_name:
        parts = [part.strip() for part in component_name.split('/')]
        variations.extend(parts)
        
        # Special case for "Wing/Retaining Wall"
        if "Wing" in component_name and "Wall" in component_name:
            variations.append("Wingwall")
    return variations

def find_in_headers(component_variations, description_sections):
    """
    Try to find component variations in the section headers.
    
    Args:
        component_variations (list): List of component name variations
        description_sections (list): List of section dictionaries
        
    Returns:
        dict or None: The matching section or None if no match found
    """
    for section in description_sections:
        header = section["header"]
        header_2 = ''
        trough_joint = False
        
        if not header:  # to check if a string exists in a larger string just do this 
            continue
        # print(header)
        if "joint" in header.lower() and "trough" in header.lower():
            # print("here")
            # print(header)    
            header = "Open Expansion Joint"
            header_2 = "Assembly Joint without Seal"
            trough_joint = True
        elif "joint" in header.lower() and "bridge" in header.lower():
            header = "Pourable Joint Seal"
        # Check if any variation appears in the header
        for variation in component_variations:
            # print(variation)
            if trough_joint:
                if variation.lower() in header.lower() or variation.lower() in header_2.lower():
                    # print("here 2")
                    return section
            else:
                if variation.lower() in header.lower():
                    # print("here 2")
                    return section
    
    return None

def find_in_content(component_variations, description_sections):
    """
    Try to find component variations in the section content.
    
    Args:
        component_variations (list): List of component name variations
        description_sections (list): List of section dictionaries
        
    Returns:
        dict or None: The matching section or None if no match found
    """
    for section in description_sections:
        content = section["content"]
        
        if not content:
            continue
            
        # Check if any variation appears in the content
        for variation in component_variations:
            # Create a pattern that matches the variation as a whole word
            pattern = r'\b' + variation + r'\b'
            if re.search(pattern, content, re.IGNORECASE):
                return section
                
            # For patterns with \d+, we need a special approach
            if r'\d+' in variation:
                base = variation.replace(r'\d+', '')
                pattern = r'\b' + base + r'\d+\b'
                if re.search(pattern, content, re.IGNORECASE):
                    return section
    
    return None

def match_components_and_desc(structured_components, desc_sections):
    updated_components = []
    print(structured_components)
    for component in structured_components:
            # Create a copy of the component data
            updated_component = component.copy()
            
            # Extract the component name without the ID and material prefixes
            component_name = extract_component_name(component["text"])
            component_variations = generate_component_variations(component_name)
            
            # Try to find a match in the section headers first
            header_match = find_in_headers(component_variations, desc_sections)
            
            if header_match:
                # If found in a header, add the section information
                updated_component["description_section"] = header_match
            else:
                # If not found in headers, try to find mentions in the content
                content_match = find_in_content(component_variations, desc_sections)
                
                if content_match:
                    updated_component["description_section"] = content_match
                else:
                    updated_component["description_section"] = {}
            
            updated_components.append(updated_component)
    return updated_components

def find_maintenance_sections(pdf_path, nlp):
    """
    Find all "Maintenance Needs" sections in the document, from the header to "Remarks".
    
    Args:
        doc: spaCy Doc object
        
    Returns:
        list: List of section text strings
    """
    text = read_for_maintenance(pdf_path, nlp=nlp).text
    
    # Pattern to match "Maintenance Needs" header
    maintenance_pattern = r'Maintenance\s+Needs'
    
    # Pattern to match "Remarks" header
    remarks_pattern = r'Remarks'
    
    # Find all occurrences of "Maintenance Needs"
    maintenance_matches = list(re.finditer(maintenance_pattern, text, re.IGNORECASE))
    
    sections = []
    
    for i, match in enumerate(maintenance_matches):
        # Find the start of this maintenance section
        section_start = match.start()
        
        # Find the end of this maintenance section (next "Remarks" or next "Maintenance Needs" or end of text)
        # First look for "Remarks" after this match
        remarks_match = re.search(remarks_pattern, text[section_start:], re.IGNORECASE)
        
        if remarks_match:
            section_end = section_start + remarks_match.start()
        else:
            # If no "Remarks" found, check if there's another "Maintenance Needs"
            if i < len(maintenance_matches) - 1:
                section_end = maintenance_matches[i + 1].start()
            else:
                # If this is the last maintenance section, go to the end of the text
                section_end = len(text)
        
        # Extract the section text
        section_text = text[section_start:section_end].strip()
        sections.append(section_text)
    extract_maintenance_info(sections)
    import json
    print(json.dumps(extract_maintenance_info(sections), indent=4))
    return extract_maintenance_info(sections)

def extract_maintenance_info(maintenance_sections):
    """
    Extract maintenance information from an array of text sections
    
    Args:
        maintenance_sections: List of text strings, each representing a maintenance section
        
    Returns:
        List of dictionaries containing extracted maintenance information
    """
    # List to store all processed maintenance sections
    processed_sections = []
    
    # Process each section
    for section_text in maintenance_sections:
        current_section = {}
        current_section["full_text"] = section_text
        # Extract date reported
        date_match = re.search(r"Date Reported:\s*(\d{1,2}/\d{1,2}/\d{4})", section_text)
        if date_match:
            current_section["date_reported"] = date_match.group(1).strip()
        
        # Extract priority - look for content between "Priority:" and the next field
        priority_match = re.search(r"Priority:(?:\s*\n)?(.*?)(?=\n\s*(?:Type of Work:|Status:|Component:))", section_text, re.DOTALL)
        if priority_match:
            priority_text = priority_match.group(1).strip()
            # Clean up multi-line text
            priority_text = re.sub(r'\s+', ' ', priority_text)
            current_section["priority"] = priority_text
        
        # Extract type of work - look for content between "Type of Work:" and the next field
        work_match = re.search(r"Type of Work:(?:\s*\n)?(.*?)(?=\n\s*(?:Status:|Component:|Deficiency))", section_text, re.DOTALL)
        if work_match:
            work_text = work_match.group(1).strip()
            # Clean up multi-line text
            work_text = re.sub(r'\s+', ' ', work_text)
            current_section["type_of_work"] = work_text
        
        # Extract status
        status_match = re.search(r"Status:(?:\s*\n)?(.*?)(?=\n\s*(?:Component:|Deficiency))", section_text, re.DOTALL)
        if status_match:
            status_text = status_match.group(1).strip()
            current_section["status"] = status_text
        
        # Extract component
        component_match = re.search(r"Component:(?:\s*\n)?(.*?)(?=\n\s*(?:Deficiency|Remarks))", section_text, re.DOTALL)
        if component_match:
            component_text = component_match.group(1).strip()
            current_section["component"] = component_text
        
        # Try multiple patterns for deficiency description, just like in the first code
        deficiency_patterns = [
            r"Deficiency Description\s*(.+?)(?=Remarks:|$)",
            r"Deficiency Description\n(.+?)(?=\n\n|\n[A-Z]|$)"
        ]
        
        for pattern in deficiency_patterns:
            deficiency_match = re.search(pattern, section_text, re.DOTALL | re.IGNORECASE)
            if deficiency_match:
                deficiency_text = deficiency_match.group(1).strip()
                # Clean up multi-line text
                deficiency_text = re.sub(r'\s+', ' ', deficiency_text)
                current_section["deficiency_description"] = deficiency_text
                break  # Found a match, no need to try other patterns
        
        # Only add sections that have at least some data
        if current_section:
            processed_sections.append(current_section)
    return processed_sections

def match_by_component_name(need, components):
    """
    Match a maintenance need to a component by direct component name comparison.
    
    Args:
        need (dict): Maintenance need dictionary
        components (list): List of component dictionaries
        
    Returns:
        dict or None: Matched component or None if no match found
    """
    if not need.get("component"):
        return None
    
    need_component = need["component"].lower()
    
    for component in components:
        # Extract clean component name
        clean_name = extract_component_name(component["text"]).lower()
        
        # Check for direct match or substring match
        if (clean_name == need_component or 
            clean_name in need_component or 
            need_component in clean_name):
            return component
        
        # Handle special cases
        if clean_name == "wing/retaining wall" and ("wing" in need_component or "retaining" in need_component or "wall" in need_component):
            return component
        
        if clean_name == "abutment" and "abutment" in need_component:
            return component
    
    return None

def match_by_description(need, components):
    """
    Match a maintenance need to a component by finding component mentions in the description.
    
    Args:
        need (dict): Maintenance need dictionary
        components (list): List of component dictionaries
        
    Returns:
        dict or None: Matched component or None if no match found
    """
    if not need.get("deficiency_description"):
        return None
    
    description = need["deficiency_description"].lower()
    
    # Special case for bearings
    bearing_matches = []
    if "bearing" in description or "bearings" in description:
        for component in components:
            if "bearing" in component["text"].lower():
                bearing_matches.append(component)
        
        # If we found multiple bearing components, prioritize based on context
        if len(bearing_matches) > 1:
            # Check for specific bearing types in description
            if "fixed" in description and any("fixed" in c["text"].lower() for c in bearing_matches):
                for comp in bearing_matches:
                    if "fixed" in comp["text"].lower():
                        return comp
            elif "movable" in description and any("movable" in c["text"].lower() for c in bearing_matches):
                for comp in bearing_matches:
                    if "movable" in comp["text"].lower():
                        return comp
            
            # If description mentions bearing numbers, check both components
            if re.search(r'bearing\s+#?\d+', description, re.IGNORECASE):
                # Here's where we modify behavior - we add maintenance need to ALL bearing components
                # but still return only the first one to maintain compatibility
                
                # First, add the maintenance need to ALL bearing components
                for comp in bearing_matches:
                    # Get the original need to avoid reference issues
                    comp["maintenance_needs"].append(need)
                
                # Return the first one to maintain compatibility with existing code
                # (Note: we've already added the need to all bearing components)
                return bearing_matches[0]
    
    # Try each component
    for component in components:
        # Extract clean component name and variations
        clean_name = extract_component_name(component["text"])
        variations = generate_component_variations(clean_name)
        
        # Check if any variation appears in the description
        for variation in variations:
            pattern = r'\b' + variation.lower() + r'\b'
            if re.search(pattern, description):
                return component
            
            # Handle numbered components like "abutment 1"
            if variation.lower() + r' \d+' in variations:
                pattern = r'\b' + variation.lower() + r' \d+\b'
                if re.search(pattern, description):
                    return component
    
    return None

def match_component_to_maintence_needs(components, needs, sections, bridge_id,nlp):
    updated_components_new = []
    for component in components:
            updated_component = component.copy()
            updated_component["maintenance_needs"] = []
            updated_components_new.append(updated_component)
    for need in needs:
            # Try to match by direct component name
        matched_component = match_by_component_name(need, updated_components_new)
                
                # If no match, try to match by mentions in the deficiency description
        if not matched_component:
            matched_component = match_by_description(need, updated_components_new)

            # If a match was found, add the maintenance need to the component
        if matched_component:
            if len(matched_component["maintenance_needs"]) < 1:
                    matched_component["maintenance_needs"].append(need)
    updated_components_new = add_bridge_id_and_observation(sections, updated_components_new, bridge_id)   # get necessar stuff
    match_needs_to_components_verification(updated_components_new, nlp)
    return updated_components_new

def add_bridge_id_and_observation(sections, components, bridge_id):
    go = sections[5]["content"].split("\n")
    go = "\n".join(go[:go.index("")])
    for com in components:
        com["bridge_id"] = bridge_id
        if len(go.split("\n")) > 1:
            com["general_observation"] = go
    return components

def extract_keywords(text, nlp):
    """
    Extract meaningful keywords from text using spaCy, filtering out stop words and non-meaningful tokens.
    """
    if not text:
        return []
    
    # Process text with spaCy
    doc_in = nlp(text.lower())
    
    # Extract meaningful tokens
    keywords = []
    for token in doc_in:
        # Keep tokens that are:
        # - Not stop words
        # - Not punctuation
        # - Not spaces
        # - Longer than 2 characters
        # - Are alphabetic or contain important numbers/codes
        if (not token.is_stop and 
            not token.is_punct and 
            not token.is_space and 
            len(token.text) > 2 and
            (token.is_alpha or token.like_num or '#' in token.text)):
            
            # Use lemma for better matching (e.g., "cleaning" and "clean" will match)
            keyword = token.lemma_ if token.lemma_ != '-PRON-' else token.text
            keywords.append(keyword)
    
    return list(set(keywords))

def calculate_match_confidence(component_text, type_keywords, deficiency_keywords, nlp):
    """
    Calculate a confidence score for the match based on keyword overlap.
    """
    all_keywords = set(type_keywords + deficiency_keywords)
    component_words = set(extract_keywords(component_text, nlp))
    
    if not all_keywords:
        return 0.0
    
    overlap = len(all_keywords.intersection(component_words))
    confidence = overlap / len(all_keywords)
    
    return round(confidence, 2)

def match_needs_to_components_verification(updated_components_new, nlp):
    all_maintenance_needs = []
    
    for component in updated_components_new:
        if component.get('maintenance_needs'):
            for need in component['maintenance_needs']:
                    # Add source component info to the maintenance need
                need_with_source = need.copy()
                need_with_source['source_component_id'] = component['id']
                need_with_source['source_component_text'] = component['text']
                all_maintenance_needs.append(need_with_source)
        
    print(f"Found {len(all_maintenance_needs)} maintenance needs total")
        
        # Step 2: Find components without maintenance needs
    components_without_maintenance = [comp for comp in updated_components_new if not comp.get('maintenance_needs') or len(comp['maintenance_needs']) == 0]
        
    print(f"Found {len(components_without_maintenance)} components without maintenance needs")
        
        # Step 3: Match maintenance needs to components without them
    matches = []
        
    for component in components_without_maintenance:
        component_text = component.get('text', '').lower()
            
            # Get all text content from the component for matching
        all_component_text = []
        all_component_text.append(component_text)
            
            # Add description section content if available
        if component.get('description_section') and component['description_section'].get('content'):
            all_component_text.append(component['description_section']['content'].lower())
            
        #     # Add defect descriptions if available
        # if component.get('defects'):
        #     for defect in component['defects']:
        #         if defect.get('description'):
        #             all_component_text.append(defect['description'].lower())
            
            # Combine all text for this component
        combined_component_text = ' '.join(all_component_text)
            
            # Check each maintenance need for matches
        for need in all_maintenance_needs:
            type_of_work = need.get('type_of_work', '').lower()
            deficiency_desc = need.get('deficiency_description', '').lower()
                
                # Extract keywords from type_of_work and deficiency_description
            type_of_work_keywords = extract_keywords(type_of_work, nlp)
            deficiency_keywords = extract_keywords(deficiency_desc, nlp)
                
                # Check for matches in type_of_work first (primary match)
            type_of_work_match = any(
                    keyword in combined_component_text 
                    for keyword in type_of_work_keywords
                )
                
                # Check for matches in deficiency_description (fallback match)
            deficiency_match = any(
                    keyword in combined_component_text 
                    for keyword in deficiency_keywords
                )
                
            if type_of_work_match or deficiency_match:
                match_info = {
                        'component_id': component['id'],
                        'component_text': component['text'],
                        'maintenance_need': need,
                        'match_type': 'type_of_work' if type_of_work_match else 'deficiency_description',
                        'matched_keywords': type_of_work_keywords if type_of_work_match else deficiency_keywords,
                        'confidence': calculate_match_confidence(combined_component_text, type_of_work_keywords, deficiency_keywords, nlp)
                    }
                matches.append(match_info)
    for comp in updated_components_new:
        comp_name =comp['text']
        if comp.get('description_section') and comp.get('description_section').get('condition_rating') and comp.get('description_section').get('condition_rating') == "GOOD":
            continue
        for match in matches:
            if match["component_text"] == comp_name:
                if isinstance(comp['maintenance_needs'], list):
                    comp['maintenance_needs'] .append(match['maintenance_need'])  

    return  updated_components_new    