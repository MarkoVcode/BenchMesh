"""SI formatting utilities.

format_scientific_to_si("1.166309E+00", unit='A') -> '1.166 A'
format_scientific_to_si("1.166309E-03", unit='A') -> '1.166 mA'

Handles zero, negative numbers, and returns a string with SI prefix and full prefix name optional.
"""
from typing import Tuple

SI_PREFIXES = [
    (24, 'Y', 'yotta'),
    (21, 'Z', 'zetta'),
    (18, 'E', 'exa'),
    (15, 'P', 'peta'),
    (12, 'T', 'tera'),
    (9, 'G', 'giga'),
    (6, 'M', 'mega'),
    (3, 'k', 'kilo'),
    (0, '', ''),
    (-3, 'm', 'milli'),
    (-6, 'µ', 'micro'),
    (-9, 'n', 'nano'),
    (-12, 'p', 'pico'),
    (-15, 'f', 'femto'),
    (-18, 'a', 'atto'),
    (-21, 'z', 'zepto'),
    (-24, 'y', 'yocto'),
]


def _parse_float(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if value is None:
        raise ValueError("None is not a number")
    # support strings with E or e
    s = str(value).strip()
    # replace uppercase unicode micro if present
    s = s.replace('\u00b5', 'e-6')
    try:
        return float(s)
    except Exception as e:
        # try to handle things like '1.23E+03' explicitly
        try:
            return float(s.replace('E', 'e'))
        except Exception:
            raise


def format_scientific_to_si(value, unit: str = '', sig_figs: int = 3) -> Tuple[str, str, str]:
    """Format numeric value (or scientific string) into SI-scaled components.

    Returns a tuple (number_str, prefix_symbol, prefix_full_name).
    - number_str: the scaled numeric value as a string (no unit appended)
    - prefix_symbol: SI abbreviation (e.g. 'm', 'µ', '')
    - prefix_full_name: full prefix name (e.g. 'milli', 'micro', '')

    Examples:
        format_scientific_to_si('1.166309E+00') -> ('1.166', '', '')
        format_scientific_to_si('1.166309E-03') -> ('1.166', 'm', 'milli')

    Precision: sig_figs controls significant digits in the returned number_str.
    """
    num = _parse_float(value)
    if num == 0:
        return ("0", '', '')

    # determine exponent in base10
    import math

    exp = int(math.floor(math.log10(abs(num))))
    # find closest SI power (multiple of 3)
    si_power = max(p for p, _a, _b in SI_PREFIXES if p <= exp - (exp % 3))
    # Adjust: ensure we pick power such that scaled value is between 1 and 1000
    scaled = num / (10 ** si_power)
    # if scaled is >=1000, shift up
    if abs(scaled) >= 1000:
        si_power += 3
        scaled = num / (10 ** si_power)
    # if scaled < 1, shift down
    if abs(scaled) < 1:
        si_power -= 3
        scaled = num / (10 ** si_power)

    # clamp to available prefixes
    powers = [p for p, _a, _b in SI_PREFIXES]
    si_power = max(min(si_power, max(powers)), min(powers))

    # find prefix symbol and name
    symbol = ''
    fullname = ''
    for p, s, name in SI_PREFIXES:
        if p == si_power:
            symbol = s
            fullname = name
            break

    # format number with sig_figs significant digits
    # compute decimals: keep sig_figs significant digits
    digits = sig_figs
    # use general formatting
    fmt = f"{{:.{digits}g}}"
    formatted_num = fmt.format(scaled)

    # ensure decimal point uses dot and remove trailing zeros for nice format
    # but keep as-is from format
    # return only the numeric string (no unit), the symbol and the full name
    return formatted_num, symbol, fullname


# quick examples when executed directly
if __name__ == '__main__':
    tests = [
        '1.166309E+00',
        '1.166309E-03',
        '1.166309E-06',
        '0',
        '-2.3E6',
        0.00000045,
    ]
    for t in tests:
        num_str, sym, n = format_scientific_to_si(t, '', sig_figs=5)
        print(t, '->', num_str, sym, n)
