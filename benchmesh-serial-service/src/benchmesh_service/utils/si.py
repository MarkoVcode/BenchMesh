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

    # try to auto-detect significant digits when the input was a scientific string
    digits = sig_figs
    try:
        import re
        if isinstance(value, str):
            m = re.match(r"^[\s]*([+-]?)(\d+)(?:\.(\d*))?[eE]([+-]?\d+)[\s]*$", value)
            if m:
                intpart = m.group(2) or ''
                frac = m.group(3) or ''
                sig = (intpart + frac).lstrip('0')
                if len(sig) > 0:
                    digits = max(digits, len(sig))
    except Exception:
        # fall back to provided sig_figs on any failure
        digits = sig_figs
    # use general formatting
    fmt = f"{{:.{digits}g}}"
    formatted_num = fmt.format(scaled)

    # ensure decimal point uses dot and remove trailing zeros for nice format
    # but keep as-is from format
    # return only the numeric string (no unit), the symbol and the full name
    return formatted_num, symbol, fullname


def trim_digits_to(s: str, n: int = 5) -> str:
    """Trim least-significant digits from numeric string `s` until it contains at most
    `n` digit characters (digits do not include '-' or '.').

    Does not perform rounding; it simply removes characters from the end of the
    significant portion. Preserves sign, decimal point and exponent (if present).

    Examples:
        trim_digits_to('-1.571223', 5) -> '-1.5712'
        trim_digits_to('4.994804E+01', 5) -> '4.9948E+01' -> but if exponent present we trim mantissa digits
    """
    import re
    if not isinstance(s, str):
        s = str(s)

    # separate exponent if present
    m = re.match(r"^([+-]?.*?)([eE][+-]?\d+)?$", s.strip())
    if not m:
        return s
    mantissa = m.group(1)
    exponent = m.group(2) or ''

    # preserve sign
    sign = ''
    if mantissa.startswith(('+', '-')):
        sign = mantissa[0]
        mantissa = mantissa[1:]

    # count digits
    digits = sum(1 for ch in mantissa if ch.isdigit())
    if digits <= n:
        return s

    # remove characters from the end until digits <= n
    while digits > n and mantissa:
        last = mantissa[-1]
        mantissa = mantissa[:-1]
        if last.isdigit():
            digits -= 1

    # remove trailing decimal point if left at end
    if mantissa.endswith('.'):
        mantissa = mantissa[:-1]

    return f"{sign}{mantissa}{exponent}"


def si_to_scientific(s: str, sig_figs: int = None) -> str:
    """Convert an SI-scaled numeric string into scientific notation.

    Examples:
        si_to_scientific('1.166 m') -> '1.166E-03'
        si_to_scientific('1.166mA') -> '1.166E-03'
        si_to_scientific('49.948') -> '4.9948E+01'
    """
    import re

    if not isinstance(s, str):
        s = str(s)
    st = s.strip()
    if st == '':
        return st

    # build symbol -> power map
    symbol_map = {sym: p for p, sym, name in SI_PREFIXES if sym}
    # accept 'u' as micro as well
    symbol_map.setdefault('u', -6)
    symbol_map.setdefault('\u00b5', -6)

    # split number and trailing suffix
    m = re.match(r'^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)(.*)$', st)
    if not m:
        return st
    num_part = m.group(1)
    suffix = m.group(2).strip()

    # detect symbol at start of suffix (e.g., 'mA' or 'µ')
    symbol = ''
    if suffix:
        first = suffix[0]
        if first in symbol_map:
            symbol = first
        else:
            # maybe suffix is like 'm' separated by space
            # try to find any symbol char in the suffix
            for ch in suffix:
                if ch in symbol_map:
                    symbol = ch
                    break

    try:
        base_val = float(num_part)
    except Exception:
        return st

    power = symbol_map.get(symbol, 0)
    value = base_val * (10 ** power)

    if value == 0:
        return '0'

    # determine significant digits if not provided
    digits = sig_figs
    if digits is None:
        m2 = re.match(r'^[+-]?(\d+)(?:\.(\d*))?(?:[eE][+-]?\d+)?$', num_part)
        if m2:
            intp = m2.group(1) or ''
            frac = m2.group(2) or ''
            sig = (intp + frac).lstrip('0')
            digits = len(sig) if sig else 1
        else:
            digits = 6

    fmt = f'{{:.{digits}E}}'
    return fmt.format(value)


def si_to_value(s: str, sig_figs: int = 5) -> dict:
        """Convert an SI-style string to a structured value.

        Returns a dict with keys:
            - 'si': {'number': <numeric string>, 'symbol': <SI symbol>, 'prefix': <full name>}
            - 'sci': <scientific notation string>
            - 'val': <input value>

        Example:
            si_to_value('1.166 m') -> {'si': {'number':'1.166', 'symbol':'m', 'prefix':'milli'}, 'sci':'1.16600E-03'}
        """
        sci = si_to_scientific(s, sig_figs=sig_figs)
        # format back to SI components using our formatter
        num_str, sym, fullname = format_scientific_to_si(sci, sig_figs=sig_figs)
        si_obj = {'number': num_str}
        if sym:
            si_obj['symbol'] = sym
        if fullname:
            si_obj['prefix'] = fullname
        return {
            'si': si_obj,
            'sci': sci,
            'val': str(s),
        }


def sci_to_value(sci: str, sig_figs: int = 5) -> dict:
        """Convert a scientific-notation string to structured SI and scientific forms.

        Returns same structure as si_to_value.
        Example:
            sci_to_value('1.166309E-03') -> {'si': {'number':'1.1663','symbol':'m','prefix':'milli'}, 'sci':'1.16631E-03'}
        """
        # normalize scientific string to requested sig_figs
        try:
                val = _parse_float(sci)
        except Exception:
                # if not parseable, return raw
                return {'si': {'number': '', 'symbol': '', 'prefix': ''}, 'sci': sci}

        fmt = f'{{:.{sig_figs}E}}'
        sci_norm = fmt.format(val)
        num_str, sym, fullname = format_scientific_to_si(sci_norm, sig_figs=sig_figs)
        si_obj = {'number': num_str}
        if sym:
            si_obj['symbol'] = sym
        if fullname:
            si_obj['prefix'] = fullname
        return {
            'si': si_obj,
            'sci': sci_norm,
            'val': str(sci),
        }


# quick examples when executed directly "measurement1_num": "1.63""measurement1_num": "1.61"  "+1.6003E+00", "measurement1_num": "1.6","4.994804E+01", "measurement1_num": "49.9",
if __name__ == '__main__':
    tests = [
        '+1.6310E+00', 
        '4.994804E+01',
        '+1.6097E+00',
        '+0.0000E-308',
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
    # trim examples
    trim_tests = ['-1.571223', '1.571223', '4.994804E+01', '12345.6789', '0.000123456']
    print('\nTrim examples:')
    for t in trim_tests:
        print(t, '->', trim_digits_to(t, 5))

    # si_to_scientific tests
    print('\nSI -> scientific tests:')
    si_tests = ['1.166 m', '1.166mA', '49.948', '4.994804E+01', '1.1663 µ']
    for t in si_tests:
        print(t, '->', si_to_scientific(t, sig_figs=5))

    # Simple assertions / tests
    print('\nRunning quick assertions...')
    import math

    # format_scientific_to_si preserves digits for scientific input
    assert format_scientific_to_si('4.990767E+01', sig_figs=5)[0] == '49.90767'

    # trim_digits_to behavior
    assert trim_digits_to('-1.571223', 5) == '-1.5712'
    assert trim_digits_to('1.571223', 5) == '1.5712'

    # si_to_scientific
    s = si_to_scientific('1.166 m', sig_figs=5)
    assert s == '1.16600E-03'

    # si_to_value returns SI symbol and scientific string; numeric part close to expected
    v = si_to_value('1.166 m', sig_figs=5)
    assert v['si']['symbol'] == 'm'
    assert math.isclose(float(v['si']['number']), 1.166, rel_tol=1e-6)
    assert v['sci'] == '1.16600E-03'

    # sci_to_value normalizes scientific string and returns SI parts
    sv = sci_to_value('1.166309E-03', sig_figs=5)
    assert sv['sci'] == '1.16631E-03'
    assert sv['si']['symbol'] == 'm'
    assert math.isclose(float(sv['si']['number']), 1.16631, rel_tol=1e-6)
    
    v = si_to_value('1.166 m', sig_figs=5)
    print(v)
    sv = sci_to_value('1.166309E-03', sig_figs=5)
    print(sv)
    print('All quick tests passed.')
