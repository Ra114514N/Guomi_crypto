#!/usr/bin/env python3
"""国密安全传输系统命令行入口。"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

ARTIFACTS = Path(__file__).parent / "artifacts"
DEFAULT_PLAIN = Path(__file__).parent / "plain.txt"
DEFAULT_SENDER_ID = "sender@sm9.local"


def cmd_inspect_env(args):
    from crypto.gmssl_loader import error_message, is_available

    print("=== Environment ===")
    print(f"Python: {sys.version.split()[0]}")
    try:
        import gmssl as _gm

        print(f"gmssl package: {getattr(_gm, '__version__', 'installed')}")
    except Exception:
        print("gmssl package: not installed")
    sm9_ok = is_available()
    print(f"GmSSL native library (SM9): {'available' if sm9_ok else 'unavailable - ' + error_message()}")
    print("Protocol: envelope v3.0")
    print("SM2 mode: sm2_wrap")
    print("SM4 modes: CBC / CTR / GCM")
    print("ZUC-128: enabled")


def cmd_gen_sm2(args):
    from crypto.file_utils import ensure_output_dir
    from crypto.key_utils import save_key_hex
    from crypto.sm2_kex_or_wrap import generate_sm2_keypair

    out = ensure_output_dir(args.output_dir)
    pri, pub = generate_sm2_keypair()
    save_key_hex(out / "receiver_pri.txt", pri)
    save_key_hex(out / "receiver_pub.txt", pub)
    print("[gen-sm2] generated receiver SM2 key pair")
    print(f"  private: {out / 'receiver_pri.txt'}")
    print(f"  public:  {out / 'receiver_pub.txt'}")


def cmd_send(args):
    from core.sender import send
    from crypto.file_utils import ensure_output_dir
    from crypto.key_utils import load_key_hex, save_key_hex
    from crypto.sm2_kex_or_wrap import generate_sm2_keypair
    from crypto.sm9_signature import generate_master_key

    out = ensure_output_dir(args.output_dir)
    plain_path = Path(args.input)
    if not plain_path.exists():
        sys.exit(f"[error] plaintext file not found: {plain_path}")

    sm9_master, _ = generate_master_key()
    try:
        receiver_pub = load_key_hex(out / "receiver_pub.txt")
    except FileNotFoundError:
        pri, receiver_pub = generate_sm2_keypair()
        save_key_hex(out / "receiver_pri.txt", pri)
        save_key_hex(out / "receiver_pub.txt", receiver_pub)

    result = send(
        plaintext_path=plain_path,
        receiver_pub=receiver_pub,
        sm9_master_key=sm9_master,
        sender_id=args.sender_id,
        cipher=args.cipher,
        mode=args.mode,
        output_dir=out,
    )
    print("\n[send] done")
    print(f"  algorithm: {result['algo_label']}")
    print(f"  auth tag:  {result['auth_tag'][:32]}...")
    print(f"  signature: {result['signature_hex'][:32]}...")
    print(f"  envelope:  {out / 'message.json'}")
    print("  note: use `demo` for same-process SM9 verification on this Windows binding")


def cmd_receive(args):
    from core.receiver import receive
    from crypto.file_utils import ensure_output_dir
    from crypto.key_utils import load_key_hex

    out = ensure_output_dir(args.output_dir)
    sys.exit(
        "[error] standalone receive is disabled because the installed gmssl-python "
        "SM9 master key object cannot be safely serialized on this Windows binding. "
        "Use `python cli.py demo` or the GUI Send/Receive tab, which keep the SM9 "
        "master key in memory for the full workflow."
    )


def cmd_demo(args):
    from core.workflow import run_full_workflow
    from crypto.file_utils import ensure_output_dir

    out = ensure_output_dir(args.output_dir)
    plain_path = Path(args.input)
    if not plain_path.exists():
        sys.exit(f"[error] plaintext file not found: {plain_path}")

    result = run_full_workflow(
        plaintext_path=plain_path,
        cipher=args.cipher,
        mode=args.mode,
        sender_id=args.sender_id,
        output_dir=out,
    )
    recv = result["receive"]
    print("\n[demo] complete")
    print(f"  integrity: {'OK' if recv['integrity_ok'] else 'FAIL'}")
    print(f"  signature: {'OK' if recv['signature_ok'] else 'FAIL'}")
    print(f"  digest:    {'OK' if recv['digest_ok'] else 'FAIL'}")
    print(f"  result:    {'SUCCESS' if recv['success'] else 'FAIL'}")
    print(f"  envelope:  {out / 'message.json'}")
    if not recv["success"]:
        sys.exit(1)


def cmd_benchmark(args):
    from core.benchmark import run_benchmark
    from crypto.file_utils import ensure_output_dir

    out = ensure_output_dir(args.output_dir)
    md = run_benchmark(data_sizes=[1024, 64 * 1024, 1024 * 1024], output_dir=out)
    print(md)
    print(f"[benchmark] report: {out / 'benchmark.md'}")
    print(f"[benchmark] csv:    {out / 'benchmark.csv'}")


def cmd_test(args):
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"], cwd=str(Path(__file__).parent))
    sys.exit(r.returncode)


def build_parser():
    p = argparse.ArgumentParser(description="SM2/SM3/SM4/ZUC/SM9 secure transport demo")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--output-dir", default=str(ARTIFACTS))
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("inspect-env", parents=[common]).set_defaults(func=cmd_inspect_env)
    sub.add_parser("gen-sm2", parents=[common]).set_defaults(func=cmd_gen_sm2)

    ps = sub.add_parser("send", parents=[common])
    ps.add_argument("--cipher", choices=["sm4", "zuc"], default="sm4")
    ps.add_argument("--mode", choices=["cbc", "ctr", "gcm"], default="gcm")
    ps.add_argument("--in", dest="input", default=str(DEFAULT_PLAIN))
    ps.add_argument("--sender-id", default=DEFAULT_SENDER_ID)
    ps.set_defaults(func=cmd_send)

    sub.add_parser("receive", parents=[common]).set_defaults(func=cmd_receive)

    pd = sub.add_parser("demo", parents=[common])
    pd.add_argument("--cipher", choices=["sm4", "zuc"], default="sm4")
    pd.add_argument("--mode", choices=["cbc", "ctr", "gcm"], default="gcm")
    pd.add_argument("--in", dest="input", default=str(DEFAULT_PLAIN))
    pd.add_argument("--sender-id", default=DEFAULT_SENDER_ID)
    pd.set_defaults(func=cmd_demo)

    sub.add_parser("benchmark", parents=[common]).set_defaults(func=cmd_benchmark)
    sub.add_parser("test").set_defaults(func=cmd_test)
    return p


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
