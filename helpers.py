def get_team_index(lines):
    for idx, line in enumerate(lines):
        if line.startswith('Team Lead:'):
            return idx
    return None

def check_for_team(lines):
    for line  in lines:
        if line.startswith('Team Lead:'):
            return True
    return False

def get_desc_text(desc_text):
    if '' in desc_text.split("\n") and check_for_team(desc_text.split("\n")):
        clean_idx_start = desc_text.split("\n").index('')
        lines = desc_text.split("\n")
        clean_idx_end = get_team_index(lines)
        desc_text_start = desc_text.split("\n")[:clean_idx_start]
        if len(lines) > clean_idx_end:
            desc_text_end = desc_text.split("\n")[clean_idx_end+1:]
            desc_test = desc_text_start + desc_text_end
        else:
            desc_test = desc_text_start
    elif '' in desc_text.split("\n"):
        cleaned_idx = desc_text.split("\n").index('')
        desc_test = desc_text.split("\n")[:cleaned_idx]
    else:
        cleaned_idx = len(desc_text.split("\n")) + 1
        desc_test = desc_text.split("\n")[:cleaned_idx]
    return "\n".join(desc_test)