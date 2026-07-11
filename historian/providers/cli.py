"""Generic CLI provider: run any command that reads a prompt on stdin and
writes the analysis to stdout. Covers OpenCode, Gemini CLI, Codex, Ollama, and
any custom script — the specific tool is entirely config (command/args/env).

By default the model's output is streamed to the terminal live (config `stream`)
so you can watch it being written; it is captured and returned regardless."""

import os
import subprocess
import sys
import threading


def _cmd_env_timeout(cfg):
    command = cfg.get("command")
    if not command:
        raise RuntimeError("cli provider: 'command' is not set in config")
    cmd = [command] + list(cfg.get("args") or [])
    env = dict(os.environ)
    env.update(cfg.get("env") or {})
    timeout = cfg.get("timeout_sec", cfg.get("provider_timeout_sec", 180))
    return command, cmd, env, timeout


def _run_streamed(command, cmd, env, timeout, prompt):
    """Stream stdout live to the terminal while capturing it. stderr is drained
    on a side thread (avoids pipe-buffer deadlock)."""
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            errors="replace", env=env, bufsize=1)
    err_lines = []
    err_thread = threading.Thread(target=lambda: err_lines.extend(proc.stderr), daemon=True)
    err_thread.start()
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    out = []
    try:
        proc.stdin.write(prompt)
        proc.stdin.close()
        sys.stdout.write(f"\n--- {command} output ---\n")
        for line in proc.stdout:
            out.append(line)
            try:  # best-effort live display; never let a console encoding error break the save
                sys.stdout.write(line)
                sys.stdout.flush()
            except Exception:
                pass
        sys.stdout.write("\n--- end ---\n")
        proc.wait()
    finally:
        timer.cancel()
        err_thread.join(timeout=1)
    return proc.returncode, "".join(out), "".join(err_lines)


def analyze(prompt, cfg):
    command, cmd, env, timeout = _cmd_env_timeout(cfg)
    if cfg.get("stream", True):
        code, out, err = _run_streamed(command, cmd, env, timeout, prompt)
    else:
        r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env, timeout=timeout)
        code, out, err = r.returncode, r.stdout, r.stderr
    if code != 0:
        raise RuntimeError(f"{command} failed ({code}): {err.strip()[:500]}")
    out = out.strip()
    if not out:
        raise RuntimeError(f"{command} returned empty output")
    return out
