# -*- coding: utf-8 -*-
import sys
import time

sys.path.insert(
    0,
    r"C:\Program Files\Epic Games\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python",
)
from remote_execution import RemoteExecution, RemoteExecutionConfig

SCRIPT = r"E:\游戏\符济\Rune-of-Succor\符济\Content\Python\fix_tps_camera.py"


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
        print("NO_NODES")
        remote.stop()
        return 2

    node_id = nodes[0]["node_id"]
    remote.open_command_connection(node_id)
    # Prefer ExecuteFile if supported; fall back to statement
    cmd = (
        "import runpy\n"
        f"runpy.run_path(r'{SCRIPT}', run_name='__main__')\n"
    )
    ok, res = remote.run_command(cmd, exec_mode="ExecuteStatement")
    print("ok", ok)
    print(res)
    remote.close_command_connection()
    remote.stop()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
