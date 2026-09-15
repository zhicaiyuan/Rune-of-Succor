# -*- coding: utf-8 -*-
import sys
import time

sys.path.insert(
    0,
    r"C:\Program Files\Epic Games\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python",
)
from remote_execution import RemoteExecution, RemoteExecutionConfig

SCRIPTS = [
    r"E:\游戏\符济\Rune-of-Succor\符济\Content\Python\fix_alt_walk.py",
    r"E:\游戏\符济\Rune-of-Succor\符济\Content\Python\probe_alt_walk.py",
]


def main():
    cfg = RemoteExecutionConfig()
    cfg.multicast_bind_address = "0.0.0.0"
    remote = RemoteExecution(cfg)
    remote.start()
    nodes = []
    for i in range(12):
        time.sleep(1)
        nodes = remote.remote_nodes
        print(i, nodes)
        if nodes:
            break
    if not nodes:
        print("NO_NODES — enable Edit > Plugins > Python Editor Script Plugin + remote execution, or close editor and use UnrealEditor-Cmd")
        remote.stop()
        return 2

    node_id = nodes[0]["node_id"]
    remote.open_command_connection(node_id)
    for script in SCRIPTS:
        cmd = "import runpy\nrunpy.run_path(r'%s', run_name='__main__')\n" % script.replace("\\", "\\\\")
        ok, res = remote.run_command(cmd, exec_mode="ExecuteStatement")
        print("SCRIPT", script)
        print("ok", ok)
        print(res)
    remote.close_command_connection()
    remote.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
