def _Pyceler_Environment():
    import os
    import platform
    import sys
    import builtins as _Pyceler_Builtins
    return [sys.implementation.name, sys.version.split()[0], sys.platform, platform.node(), platform.machine(),
            platform.processor(), os.cpu_count(), _Pyceler_Builtins.sorted([Key, Value] for Key, Value in os.environ.items() if Key.startswith("OMP_"))]
