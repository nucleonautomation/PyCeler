def _Pyceler_Environment():  # Capture machine and runtime identity used to scope measured dispatch decisions.
    import os
    import platform
    import sys
    import builtins as _Pyceler_Builtins
    return [sys.implementation.name, sys.version.split()[0], sys.platform, platform.node(), platform.machine(),
            platform.processor(), os.cpu_count(), _Pyceler_Builtins.sorted([Key, Value] for Key, Value in os.environ.items() if Key.startswith("OMP_"))]
