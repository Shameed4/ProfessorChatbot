def pathname_to_name(pathname):
    return pathname.replace('_', ' ').title()

def name_to_pathname(name):
    return name.replace(' ', '_').lower()

def name_to_index_name(professor):
    return professor.lower().replace(' ', '-')