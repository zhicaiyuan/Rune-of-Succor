# -*- coding: utf-8 -*-
import sys
import time

sys.path.insert(
    0,
    r"C:\Program Files\Epic Games\UE_5.8\Engine\Plugins\Experimental\PythonScriptPlugin\Content\Python",
)
from remote_execution import RemoteExecution, RemoteExecutionConfig, MODE_EXEC_FILE

SCRIPT = r"E:\游戏\符济\Rune-of-Succor\符济\Content\Python\probe_pivot_logic.py"


def main():
    for bind in ("127.0.0.1", "0.0.0.0"):
        cfg = RemoteExecutionConfig()
        cfg.multicast_bind_address = bind
        remote = RemoteExecution(cfg)
        remote.start()
        nodes = []
        for i in range(8):
            time.sleep(1)
            nodes = list(remote.remote_nodes)
            print(bind, i, nodes)
            if nodes:
                break
        if nodes:
            break
        remote.stop()
        remote = None
    if not remote or not nodes:
        print("NO_NODES")
        return 2
    remote.open_command_connection(nodes[0]["node_id"])
    result = remote.run_command(SCRIPT, exec_mode=MODE_EXEC_FILE)
    print(result)
    remote.close_command_connection()
    remote.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
