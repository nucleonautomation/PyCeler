cdef str _Python_Module(str Source, str Native, object File, str Prefix):  # Join application code and generated native helpers into one readable Cython source file.
    from .Direct_Source import _Direct_Module
    Source, Native = _Dispatch_Instrument(Source, Native, Prefix)
    return _Direct_Module(Source, Native, File, Prefix)
