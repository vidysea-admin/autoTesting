import ctypes, sys, time
k = ctypes.windll.kernel32
pid, which = int(sys.argv[1]), sys.argv[2]
k.FreeConsole()
ok = k.AttachConsole(pid)
print("attach", ok, ctypes.get_last_error(), flush=True)
k.SetConsoleCtrlHandler(None, True)           # ignore Ctrl-C here; BREAK may kill this helper
k.GenerateConsoleCtrlEvent(0 if which == "C" else 1, 0)
time.sleep(1.5)
