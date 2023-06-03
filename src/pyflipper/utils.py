def is_hexstring(value:str) -> bool:
    try:
        int(value.replace(' ', ''), 16)
        return True
    except ValueError:
        return False


def parse_fs_size(value:str) -> int:
    if value.endswith('iB'):
        unit = value[-3:]
        value = value[:-3].strip()

        if unit == 'KiB':
            unit = 1024
        elif unit == 'MiB': # note that it is probably not used
            unit = 1024**2
        elif unit == 'GiB': # note that it is probably not used
            unit = 1024**3
        
        if "." in value:
            value = float(value)
        else:
            value = int(value)
        
        value = int(value * unit)
        
    elif value.endswith('b') or value.endswith('B'): # note that is should be 'B' but the firmware returns 'b'
        value = int(value[:-1])

    else:
        value = int(value.strip())
    if isinstance(value, str):
        return 0
    return value