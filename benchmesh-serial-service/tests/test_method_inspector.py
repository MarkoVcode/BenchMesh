import os, sys
THIS_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(THIS_DIR, '..', 'src'))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import pytest
from benchmesh_service.method_inspector import (
    inspect_driver_methods,
    generate_example_url,
    _humanize_method_name,
    _get_parameter_type_name
)


# ===== Test Driver Classes =====

class SimpleDriver:
    """Simple driver for testing basic introspection"""

    def query_voltage(self, channel: int):
        return "12.5"

    def query_current(self, channel: int):
        return "0.5"

    def set_voltage(self, channel: int, value: float):
        pass

    def set_output(self, channel: int, state: bool):
        pass

    def non_api_method(self):
        """This should not be included in results"""
        pass

    def _private_method(self):
        """This should not be included in results"""
        pass


class AnnotatedDriver:
    """Driver with type annotations for testing type extraction"""

    def query_identify(self) -> str:
        return "FAKE,IDN"

    def query_output_voltage(self, channel: int) -> float:
        return 12.5

    def set_current(self, channel: int, value: float) -> None:
        pass

    def set_mode(self, channel: int, mode: str) -> None:
        pass


class NoAnnotationsDriver:
    """Driver without type annotations"""

    def query_status(self, channel):
        return {"ok": True}

    def set_output(self, channel, value):
        pass


# ===== Unit Tests for Helper Functions =====

def test_humanize_method_name_query():
    """Test humanizing query_ method names"""
    assert _humanize_method_name("query_voltage") == "Query the voltage"
    assert _humanize_method_name("query_output_voltage") == "Query the output voltage"
    assert _humanize_method_name("query_status") == "Query the status"


def test_humanize_method_name_set():
    """Test humanizing set_ method names"""
    assert _humanize_method_name("set_voltage") == "Set the voltage"
    assert _humanize_method_name("set_current") == "Set the current"
    assert _humanize_method_name("set_output") == "Set the output"


def test_humanize_method_name_acronyms():
    """Test handling of acronyms (short uppercase names)"""
    assert _humanize_method_name("set_ocp") == "Set the OCP"
    assert _humanize_method_name("set_ovp") == "Set the OVP"
    assert _humanize_method_name("query_idn") == "Query the IDN"


def test_get_parameter_type_name_basic_types():
    """Test type name extraction for basic Python types"""
    assert _get_parameter_type_name(int) == "int"
    assert _get_parameter_type_name(float) == "float"
    assert _get_parameter_type_name(str) == "string"
    assert _get_parameter_type_name(bool) == "boolean"


# ===== Integration Tests for Method Inspection =====

def test_inspect_simple_driver():
    """Test basic method discovery without type annotations"""
    driver = SimpleDriver()
    methods = inspect_driver_methods(driver)

    # Should find 4 API methods (2 query, 2 set)
    assert len(methods) == 4

    # Check method names
    method_names = [m['name'] for m in methods]
    assert 'voltage' in method_names
    assert 'current' in method_names
    assert 'output' in method_names

    # Should NOT include non-API or private methods
    assert 'non_api_method' not in method_names
    assert '_private_method' not in method_names


def test_inspect_driver_http_methods():
    """Test HTTP method categorization"""
    driver = SimpleDriver()
    methods = inspect_driver_methods(driver)

    # Find query_voltage
    query_method = next(m for m in methods if m['name'] == 'voltage' and m['http_method'] == 'GET')
    assert query_method['full_name'] == 'query_voltage'
    assert query_method['http_method'] == 'GET'

    # Find set_voltage
    set_method = next(m for m in methods if m['name'] == 'voltage' and m['http_method'] == 'POST')
    assert set_method['full_name'] == 'set_voltage'
    assert set_method['http_method'] == 'POST'


def test_inspect_driver_parameters():
    """Test parameter extraction from method signatures"""
    driver = AnnotatedDriver()
    methods = inspect_driver_methods(driver)

    # Check set_current parameters
    set_current = next(m for m in methods if m['full_name'] == 'set_current')
    assert len(set_current['parameters']) == 2

    # Check channel parameter
    channel_param = next(p for p in set_current['parameters'] if p['name'] == 'channel')
    assert channel_param['type'] == 'int'
    assert channel_param['required'] is True

    # Check value parameter
    value_param = next(p for p in set_current['parameters'] if p['name'] == 'value')
    assert value_param['type'] == 'float'
    assert value_param['required'] is True


def test_inspect_driver_no_annotations():
    """Test that inspection works even without type annotations"""
    driver = NoAnnotationsDriver()
    methods = inspect_driver_methods(driver)

    assert len(methods) == 2

    # Parameters should be discovered even without annotations
    query_status = next(m for m in methods if m['full_name'] == 'query_status')
    assert len(query_status['parameters']) == 1
    assert query_status['parameters'][0]['name'] == 'channel'
    assert query_status['parameters'][0]['type'] == 'any'  # No annotation


def test_inspect_driver_descriptions():
    """Test auto-generated descriptions"""
    driver = AnnotatedDriver()
    methods = inspect_driver_methods(driver)

    # Check auto-generated descriptions
    query_identify = next(m for m in methods if m['full_name'] == 'query_identify')
    assert query_identify['description'] == "Query the identify"

    set_current = next(m for m in methods if m['full_name'] == 'set_current')
    assert set_current['description'] == "Set the current"


def test_inspect_driver_manifest_enrichment():
    """Test enrichment with manifest data"""
    driver = AnnotatedDriver()

    # Mock manifest data
    manifest_methods = {
        "query_output_voltage": {
            "description": "Query the actual output voltage being delivered",
            "parameters": {
                "channel": {
                    "description": "PSU channel number",
                    "range": [1, 3]
                }
            },
            "returns": {
                "type": "float",
                "unit": "V"
            }
        }
    }

    methods = inspect_driver_methods(driver, manifest_methods)

    # Find enriched method
    query_voltage = next(m for m in methods if m['full_name'] == 'query_output_voltage')

    # Check description override
    assert query_voltage['description'] == "Query the actual output voltage being delivered"

    # Check parameter enrichment
    channel_param = query_voltage['parameters'][0]
    assert channel_param['description'] == "PSU channel number"
    assert channel_param['range'] == [1, 3]

    # Check return type enrichment
    assert query_voltage['returns'] == "float"
    assert query_voltage['returns_unit'] == "V"


def test_inspect_driver_sorting():
    """Test that methods are sorted (GET first, then POST, alphabetically within each)"""
    driver = SimpleDriver()
    methods = inspect_driver_methods(driver)

    # First two should be GET methods
    assert methods[0]['http_method'] == 'GET'
    assert methods[1]['http_method'] == 'GET'

    # Last two should be POST methods
    assert methods[2]['http_method'] == 'POST'
    assert methods[3]['http_method'] == 'POST'

    # Within GET methods, should be alphabetically sorted
    get_methods = [m for m in methods if m['http_method'] == 'GET']
    get_names = [m['name'] for m in get_methods]
    assert get_names == sorted(get_names)


def test_generate_example_url_get():
    """Test example URL generation for GET methods"""
    method_info = {
        "name": "voltage",
        "full_name": "query_voltage",
        "http_method": "GET",
        "parameters": [{"name": "channel", "type": "int"}]
    }

    url = generate_example_url(method_info, "PSU", "psu-1", channel=1)
    assert url == "GET /instruments/PSU/psu-1/1/voltage"


def test_generate_example_url_post_with_param():
    """Test example URL generation for POST methods with parameters"""
    method_info = {
        "name": "voltage",
        "full_name": "set_voltage",
        "http_method": "POST",
        "parameters": [
            {"name": "channel", "type": "int"},
            {"name": "value", "type": "float"}
        ]
    }

    url = generate_example_url(method_info, "PSU", "psu-1", channel=1)
    assert url == "POST /instruments/PSU/psu-1/1/voltage/12.5"


def test_generate_example_url_post_bool_param():
    """Test example URL generation for POST methods with boolean parameters"""
    method_info = {
        "name": "output",
        "full_name": "set_output",
        "http_method": "POST",
        "parameters": [
            {"name": "channel", "type": "int"},
            {"name": "state", "type": "bool"}
        ]
    }

    url = generate_example_url(method_info, "PSU", "psu-1", channel=1)
    assert url == "POST /instruments/PSU/psu-1/1/output/true"


def test_generate_example_url_post_string_param():
    """Test example URL generation for POST methods with string parameters"""
    method_info = {
        "name": "mode",
        "full_name": "set_mode",
        "http_method": "POST",
        "parameters": [
            {"name": "channel", "type": "int"},
            {"name": "mode", "type": "string"}
        ]
    }

    url = generate_example_url(method_info, "ELL", "ell-1", channel=1)
    assert url == "POST /instruments/ELL/ell-1/1/mode/ON"
