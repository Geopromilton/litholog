$env:PYTHONPATH = "D:\LithoLog Studio\portable\LithoLogStudio\_internal\base_library.zip;D:\LithoLog Studio\portable\LithoLogStudio\_internal"
$env:PATH = "D:\LithoLog Studio\portable\LithoLogStudio\_internal;" + $env:PATH

$code = @"
using System;
using System.Runtime.InteropServices;
public class PyRunner {
    [DllImport("python312.dll", CallingConvention = CallingConvention.Cdecl)]
    public static extern void Py_Initialize();
    
    [DllImport("python312.dll", CallingConvention = CallingConvention.Cdecl)]
    public static extern int PyRun_SimpleString(string command);
    
    [DllImport("python312.dll", CallingConvention = CallingConvention.Cdecl)]
    public static extern void Py_Finalize();
}
"@
Add-Type -TypeDefinition $code

[PyRunner]::Py_Initialize()
$script = Get-Content "D:\LithoLog Studio\scratch\repack_312_native.py" -Raw
[PyRunner]::PyRun_SimpleString($script)
[PyRunner]::Py_Finalize()
