"""
Router Package

Routes classified text to the appropriate processing module based on the classification result.
"""

from jassist.router.router_cli import route_to_module, parse_classification_result

__all__ = ['route_to_module', 'parse_classification_result']
