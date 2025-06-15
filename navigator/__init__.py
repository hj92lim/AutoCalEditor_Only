"""
AutoCalEditor 네비게이터 모듈

기존 시스템과 완전히 독립적인 네비게이터 기능을 제공합니다.
"""

from .navigator_widget import NavigatorWidget
from .navigator_constants import OPCODE_COLORS, OPCODE_MAPPING, ICON_MAPPING

__all__ = ['NavigatorWidget', 'OPCODE_COLORS', 'OPCODE_MAPPING', 'ICON_MAPPING']
