import re

units_patterns = [
        r'\bLF\b',    # Linear Feet
        r'\bEA\b',    # Each
        r'\bSF\b',    # Square Feet
        r'\bCF\b',    # Cubic Feet
        r'\bFT\b',    # Feet 
        r'\bIN\b',    # Inches
        r'\bM\b',     # Meters
        r'\bMM\b'     # Millimeters
    ]
units_regex = '|'.join(units_patterns)

id_pattern = r"^(\d+)\s+"
units_pattern = r"\b(LF|SF|EA|CF|FT|IN)\b"
values_pattern = r"\b(\d+(?:\s+\d+)*)\s*$"

processed_components =[]
bridge_components = [
    "Deck",
    "Open Girder/Beam",
    "Girder/Beam",
    "Assembly Joint without Seal",
    "Pourable Joint Seal",
    "Open Expansion Joint",
    "Joint",
    "Truss",
    "Column",
    "Arch",
    "Pier Cap",
    "Pier Wall",
    "Pier",
    "Abutment",
    "Bearing",
    "Pile",
    "Railing",
    "Pile Cap",
    "Bent",
    "Parapet/Guard Rail",
    "Expansion Joint",
    "Foundation",
    "Backwall",
    "Diaphragm",
    "Fascia",
    "Elastomeric Bearing",
    "Approach",
    "Slab",
    "Approach Slab",
    "Wingwall",
    "Spandrel",
    "Cantilever",
    "Movable Bearing",
    "Fixed Bearing",
    "Counterweight",
    "Cutwater",
    "Flood Arches",
    "Suspension Cable",
    "Tower",
    "Cable-Stay",
    "Wing/Retaining Wall",
    "Bearing Pedestal",
    "Stringer",
    "Footing",
    "Shear Key",
    "Drainage System",
    "Seismic Device",
    "Crash Barrier",
    "Culvert",
    "Culvert Pipe",
    "Headwall",
    "Apron",
    "Invert",
    "Soffit",
    "Skewback",
    "Keystone",
    "Camber",
    "Tie Rod",
    "Dampener"
]
bridge_components = sorted(list(set(bridge_components)), key=len, reverse=True)
materials = ["Reinforced Concrete", "Prestressed Concrete", "RC", "PC", "Steel", "Concrete", "Timber", "Wood", "Metal", "Metal Bridge"]

def get_component_pattern():
    for component in bridge_components:
        # Handle slash-separated components
        if "/" in component:
            parts = [re.escape(part.strip()) for part in component.split("/")]
            # Create pattern that allows for typos or partial matches
            pattern = f"(?:{'|'.join(parts)}|{re.escape(component)})"
            
            # Special case for "Wing/Retaining Wall" - also match if "Wall" has a typo
            if "Wall" in component:
                wall_variations = ["Wall", "Wal", "Walls"]
                wall_pattern = f"(?:{'|'.join(wall_variations)})"
                # Replace "Wall" in the pattern with the variations
                pattern = pattern.replace(re.escape("Wall"), wall_pattern)
        else:
            pattern = re.escape(component)
        
        # Make trailing 's' optional for plurals (e.g. match "Piers" with "Pier")
        if pattern.endswith("s\\"):
            pattern = pattern[:-2] + "s?"
        else:
            pattern = pattern + "s?"
            
        # Remove number if present (e.g. "Abutment 1" -> "Abutment( \d+)?")
        if " " in pattern and any(c.isdigit() for c in pattern):
            pattern = re.sub(r'\\\ \d+', '', pattern) + r'(\ \d+)?'
            
        processed_components.append(pattern)
    material_pattern = f"(?:{'|'.join(materials)})\\s+"
    component_pattern = f"(?:{'|'.join(processed_components)})"
        
    # Final pattern including optional material prefix and component
    final_pattern = fr"(\d+\s+(?:{material_pattern})?{component_pattern})"
    print(type(final_pattern))
    return final_pattern


def extract_component_values(component_text, full_section, component_data):
    """
    Extract component values directly after the component name and unit.
    
    Args:
        component_text (str): The component text (e.g. "215 Reinforced Concrete Abutment")
        full_section (str): The full text of the component section
        component_data (dict): The component data dictionary to update
    """
    # Escape special characters in the component text for regex
    escaped_component = re.escape(component_text)
    
    # Pattern to find the component's unit and values
    # Look for exactly 5 numbers after the unit (TOTAL + CS1-CS4)
    pattern = fr"{escaped_component}\s+(LF|SF|EA|CF|FT|IN)\s+(\d+\s+\d+\s+\d+\s+\d+\s+\d+)"
    match = re.search(pattern, full_section)
    
    if match:
        component_data["units"] = match.group(1)
        values_str = match.group(2)
        component_data["values"] = [int(val) for val in values_str.split()]
    else:
        # Fallback pattern for cases with fewer or more values
        pattern = fr"{escaped_component}\s+(LF|SF|EA|CF|FT|IN)\s+(\d+(?:\s+\d+)*?)(?:\s+\d{{3,4}}\s|$)"
        match = re.search(pattern, full_section)
        
        if match:
            component_data["units"] = match.group(1)
            values_str = match.group(2)
            component_data["values"] = [int(val) for val in values_str.split()]
        else:
            # Last resort fallback
            unit_pattern = r"\b(LF|SF|EA|CF|FT|IN)\s+(\d+(?:\s+\d+){0,4})"
            pos = full_section.find(component_text) + len(component_text)
            remaining_text = full_section[pos:pos+30]  # Look at limited text to avoid capturing too much
            unit_match = re.search(unit_pattern, remaining_text)
            
            if unit_match:
                component_data["units"] = unit_match.group(1)
                values_str = unit_match.group(2)

                component_data["values"] = [int(val) for val in values_str.split()]
    return component_data


def extract_defects(section_text, component_data):
    """
    Extract defect information from a component section.
    
    Args:
        section_text (str): The full component section text
        component_data (dict): The component data dictionary to update
    """
    # Pattern to match defect entries: ID + Description + Units + Values
    # Use a more specific pattern to match exactly the format we expect
    defect_pattern = r"(\d{3,4})\s+([A-Za-z][A-Za-z\s\/\-\(\)]+)\s+(LF|SF|EA|CF|FT|IN)\s+(\d+(?:\s+\d+){0,4})" # new pattern
    # defect_pattern = r"(\d{3,4})\s+([^L][^F][^S][^E][^A][^\d]+?)\s+(LF|SF|EA|CF|FT|IN)\s+(\d+(?:\s+\d+){0,4})" # old pattern
    
    # Find all defects in the section text
    defect_matches = re.finditer(defect_pattern, section_text)
    
    for match in defect_matches:
        defect_id = match.group(1)
        defect_desc = match.group(2).strip()
        defect_unit = match.group(3)
        defect_values_str = match.group(4)
        defect_values = [int(val) for val in defect_values_str.split()]
        
        # Skip if this is the component ID itself (first entry)
        if defect_id == component_data.get("id"):
            continue
            
        # Create defect entry
        defect = {
            "id": defect_id,
            "description": defect_desc,
            "unit": defect_unit,
            "total": defect_values[0] if defect_values else None,
            "cs_values": defect_values[1:] if len(defect_values) > 1 else []
        }
        
        component_data["defects"].append(defect)
    return component_data
