# Source - https://stackoverflow.com/a/19053800
# Posted by jbaiter, modified by community. See post 'Timeline' for change history
# Retrieved 2024-03-15, License - CC BY-SA 4.0
# Further modified by tigattack
def to_camel_case(snake_str):
    """Convert snake_case string to camelCase"""
    camel_string = "".join(x.capitalize() for x in snake_str.lower().split("_"))
    return snake_str[0].lower() + camel_string[1:]


def from_camel_case(camel_str):
    """Convert camelCase string to snake_case"""
    result = []
    for i, char in enumerate(camel_str):
        if char.isupper() and i > 0:
            result.append("_")
        result.append(char.lower())
    return "".join(result)
