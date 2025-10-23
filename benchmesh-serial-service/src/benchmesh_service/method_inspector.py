"""
Method introspection utility for discovering and documenting driver methods.

This module provides functionality to:
- Discover query_* and set_* methods on driver classes
- Extract method signatures and parameter information
- Auto-generate descriptions from method names
- Optionally enrich with manifest-defined metadata
"""

import inspect
import re
from typing import Any, Dict, List, Optional, get_type_hints


def _humanize_method_name(method_name: str) -> str:
    """
    Convert method name to human-readable description.

    Examples:
        query_output_voltage -> Query the output voltage
        set_current -> Set the current
        set_ocp -> Set the OCP
        query_status -> Query the status
    """
    # Remove prefix
    if method_name.startswith('query_'):
        action = "Query the"
        name = method_name[6:]  # Remove 'query_'
    elif method_name.startswith('set_'):
        action = "Set the"
        name = method_name[4:]  # Remove 'set_'
    else:
        return method_name

    # Handle acronyms (e.g., ocp, ovp, idn)
    if len(name) <= 3 and name.isupper():
        return f"{action} {name}"
    if len(name) <= 3:
        return f"{action} {name.upper()}"

    # Convert snake_case to space-separated words
    words = name.replace('_', ' ')

    # Capitalize first letter
    return f"{action} {words}"


def _get_parameter_type_name(param_annotation: Any) -> str:
    """
    Convert parameter annotation to simple type name string.

    Examples:
        int -> "int"
        float -> "float"
        bool -> "bool"
        str -> "string"
        typing.Union[int, float] -> "number"
    """
    if param_annotation == inspect.Parameter.empty:
        return "any"

    # Handle string annotations (from __future__ import annotations)
    if isinstance(param_annotation, str):
        # Simple heuristic
        if param_annotation in ('int', 'float'):
            return param_annotation
        if param_annotation == 'str':
            return 'string'
        if param_annotation == 'bool':
            return 'boolean'
        return param_annotation

    # Handle actual type objects
    if param_annotation == int:
        return "int"
    if param_annotation == float:
        return "float"
    if param_annotation == str:
        return "string"
    if param_annotation == bool:
        return "boolean"

    # Try to get the name attribute
    if hasattr(param_annotation, '__name__'):
        return param_annotation.__name__

    # Fallback to string representation
    return str(param_annotation)


def inspect_driver_methods(driver_instance: Any, manifest_methods: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Inspect driver instance and return list of available methods with metadata.

    Args:
        driver_instance: Instance of driver class to inspect
        manifest_methods: Optional dict from manifest.json with method enrichment data

    Returns:
        List of method metadata dicts with structure:
        {
            "name": "output_voltage",           # Partial name (without prefix)
            "full_name": "query_output_voltage", # Full method name
            "http_method": "GET",               # GET or POST
            "description": "Query the output voltage",
            "parameters": [
                {
                    "name": "channel",
                    "type": "int",
                    "required": true,
                    "default": null,
                    "description": "Channel number"
                }
            ],
            "returns": "string"
        }
    """
    methods = []
    manifest_methods = manifest_methods or {}

    # Get all callable attributes
    for attr_name in dir(driver_instance):
        # Skip private/internal methods
        if attr_name.startswith('_'):
            continue

        # Only process query_ and set_ methods
        if not (attr_name.startswith('query_') or attr_name.startswith('set_')):
            continue

        attr = getattr(driver_instance, attr_name)

        # Verify it's callable
        if not callable(attr):
            continue

        # Determine HTTP method
        if attr_name.startswith('query_'):
            http_method = "GET"
            partial_name = attr_name[6:]  # Remove 'query_' prefix
        else:  # set_
            http_method = "POST"
            partial_name = attr_name[4:]  # Remove 'set_' prefix

        # Get manifest enrichment if available
        manifest_data = manifest_methods.get(attr_name, {})

        # Extract signature
        try:
            sig = inspect.signature(attr)
        except (ValueError, TypeError):
            # Can't get signature, skip this method
            continue

        # Build parameter list
        parameters = []
        for param_name, param in sig.parameters.items():
            # Skip 'self' parameter
            if param_name == 'self':
                continue

            # Get type annotation
            param_type = _get_parameter_type_name(param.annotation)

            # Get manifest parameter data if available
            manifest_param_data = manifest_data.get('parameters', {}).get(param_name, {})

            param_info = {
                "name": param_name,
                "type": param_type,
                "required": param.default == inspect.Parameter.empty,
                "default": None if param.default == inspect.Parameter.empty else param.default,
                "description": manifest_param_data.get('description', f"{param_name.capitalize()} parameter")
            }

            # Add optional range/unit info from manifest
            if 'range' in manifest_param_data:
                param_info['range'] = manifest_param_data['range']
            if 'unit' in manifest_param_data:
                param_info['unit'] = manifest_param_data['unit']

            parameters.append(param_info)

        # Auto-generate or use manifest description
        description = manifest_data.get('description', _humanize_method_name(attr_name))

        # Determine return type
        return_annotation = sig.return_annotation
        if return_annotation == inspect.Signature.empty:
            returns = "any"
        else:
            returns = _get_parameter_type_name(return_annotation)

        # Add manifest return metadata if available
        manifest_returns = manifest_data.get('returns', {})
        if isinstance(manifest_returns, dict):
            if 'type' in manifest_returns:
                returns = manifest_returns['type']

        method_info = {
            "name": partial_name,
            "full_name": attr_name,
            "http_method": http_method,
            "description": description,
            "parameters": parameters,
            "returns": returns
        }

        # Add optional manifest metadata
        if 'unit' in manifest_returns:
            method_info['returns_unit'] = manifest_returns['unit']
        if 'example' in manifest_data:
            method_info['example'] = manifest_data['example']

        methods.append(method_info)

    # Sort methods: query methods first, then set methods, alphabetically within each group
    methods.sort(key=lambda m: (m['http_method'] == 'POST', m['name']))

    return methods


def generate_example_url(method_info: Dict[str, Any], klass: str, device_id: str, channel: int = 1) -> str:
    """
    Generate example API URL for a method.

    Args:
        method_info: Method metadata dict from inspect_driver_methods
        klass: Instrument class (e.g., 'PSU', 'DMM')
        device_id: Device ID (e.g., 'psu-1')
        channel: Channel number (default: 1)

    Returns:
        Example URL string
    """
    base_url = f"/instruments/{klass}/{device_id}/{channel}/{method_info['name']}"

    if method_info['http_method'] == 'GET':
        return f"GET {base_url}"
    else:  # POST
        # Add example parameter value if method has non-channel parameters
        non_channel_params = [p for p in method_info['parameters'] if p['name'] != 'channel']
        if non_channel_params:
            # Use first parameter as example
            first_param = non_channel_params[0]
            if first_param['type'] == 'bool' or first_param['type'] == 'boolean':
                example_value = 'true'
            elif first_param['type'] in ('int', 'float'):
                example_value = '12.5'
            elif first_param['type'] == 'string':
                example_value = 'ON'
            else:
                example_value = 'value'
            return f"POST {base_url}/{example_value}"
        else:
            return f"POST {base_url}"
