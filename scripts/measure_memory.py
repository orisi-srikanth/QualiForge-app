import os
import sys
import time

sys.path.insert(0, ".")

# Measure memory via Windows API
import ctypes
from ctypes import wintypes

class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t)
    ]

def get_memory_mb():
    pmc = PROCESS_MEMORY_COUNTERS()
    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    hProcess = ctypes.windll.kernel32.GetCurrentProcess()
    ctypes.windll.psapi.GetProcessMemoryInfo(hProcess, ctypes.byref(pmc), ctypes.sizeof(pmc))
    return pmc.WorkingSetSize / (1024 * 1024)

m0 = get_memory_mb()
from backend.app.main import app
m1 = get_memory_mb()

print(f"Python interpreter base memory: {m0:.2f} MB")
print(f"Backend application loaded memory: {m1:.2f} MB")
print(f"Memory overhead of full application: {m1 - m0:.2f} MB")
print(f"Comfortably within 512 MB Render free tier: {m1 < 512}")
