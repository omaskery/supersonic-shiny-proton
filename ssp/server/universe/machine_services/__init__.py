import importlib
from .interface import InterfaceService

BUILTIN_SERVICES = [
    'fs',
    'sys',
]

FACTORIES = {}

for name in BUILTIN_SERVICES:
    mod = importlib.import_module('.{}'.format(name), __name__)
    FACTORIES[name] = mod.factory
