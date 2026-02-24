#!/usr/bin/env python3

"""Build Unicorn.js against upstream Unicorn using CMake workflow."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXPORTED_FUNCTIONS = [
    "_uc_version",
    "_uc_arch_supported",
    "_uc_open",
    "_uc_close",
    "_uc_query",
    "_uc_errno",
    "_uc_strerror",
    "_uc_reg_write",
    "_uc_reg_read",
    "_uc_reg_write_batch",
    "_uc_reg_read_batch",
    "_uc_mem_write",
    "_uc_mem_read",
    "_uc_emu_start",
    "_uc_emu_stop",
    "_uc_hook_add",
    "_uc_hook_del",
    "_uc_mem_map",
    "_uc_mem_map_ptr",
    "_uc_mem_unmap",
    "_uc_mem_protect",
    "_uc_mem_regions",
    "_uc_context_alloc",
    "_uc_free",
    "_uc_context_save",
    "_uc_context_restore",
    "_malloc",
    "_free",
]

EXPORTED_RUNTIME_METHODS = [
    "ccall",
    "getValue",
    "setValue",
    "addFunction",
    "removeFunction",
    "writeArrayToMemory",
]

CONSTANT_FILES = [
    "bindings/python/unicorn/arm64_const.py",
    "bindings/python/unicorn/arm_const.py",
    "bindings/python/unicorn/m68k_const.py",
    "bindings/python/unicorn/mips_const.py",
    "bindings/python/unicorn/ppc_const.py",
    "bindings/python/unicorn/riscv_const.py",
    "bindings/python/unicorn/s390x_const.py",
    "bindings/python/unicorn/sparc_const.py",
    "bindings/python/unicorn/tricore_const.py",
    "bindings/python/unicorn/x86_const.py",
    "bindings/python/unicorn/unicorn_const.py",
]

SUPPORTED_ARCHES = {
    "x86",
    "arm",
    "aarch64",
    "riscv",
    "mips",
    "sparc",
    "m68k",
    "ppc",
    "s390x",
    "tricore",
}

ROOT_DIR = Path(__file__).resolve().parent
UNICORN_DIR = ROOT_DIR / "unicorn"
SRC_DIR = ROOT_DIR / "src"
PATCH_DIR = ROOT_DIR / "patch"

UNICORN_PATCHES = [
    PATCH_DIR / "unicorn-cmakelists-emscripten.patch",
    PATCH_DIR / "unicorn-qemu-configure-emscripten.patch",
    PATCH_DIR / "unicorn-qemu-int128-emscripten.patch",
    PATCH_DIR / "unicorn-qemu-timer-emscripten.patch",
]


def run(cmd, cwd=None, env=None):
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def ensure_submodule():
    if not UNICORN_DIR.exists() or not any(UNICORN_DIR.iterdir()):
        run(["git", "submodule", "update", "--init", "--recursive"], cwd=ROOT_DIR)


def validate_targets(targets):
    unknown = sorted(set(targets) - SUPPORTED_ARCHES)
    if unknown:
        raise ValueError(f"Unsupported architecture(s): {', '.join(unknown)}")


def suffix_for(targets):
    if not targets:
        return ""
    return "-" + "-".join(sorted(targets))


def apply_emscripten_patches():
    for patch in UNICORN_PATCHES:
        if not patch.exists():
            raise RuntimeError(f"Patch file not found: {patch}")

        check = subprocess.run(
            ["git", "apply", "--check", str(patch)],
            cwd=UNICORN_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if check.returncode == 0:
            run(["git", "apply", str(patch)], cwd=UNICORN_DIR)
            continue

        reverse_check = subprocess.run(
            ["git", "apply", "--reverse", "--check", str(patch)],
            cwd=UNICORN_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if reverse_check.returncode == 0:
            continue

        raise RuntimeError(f"Failed to apply patch {patch}: {check.stderr.strip()}")


def generate_constants():
    output = SRC_DIR / "unicorn-constants.js"
    with output.open("w", encoding="utf-8") as out:
        out.write("// Auto-generated from Unicorn Python bindings.\n")
        for rel_path in CONSTANT_FILES:
            const_file = UNICORN_DIR / rel_path
            if not const_file.exists():
                continue
            out.write(f"// Source: {rel_path}\n")
            with const_file.open("r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if not stripped or stripped.startswith("#"):
                        continue
                    if stripped.startswith("UC_"):
                        out.write("uc." + stripped[3:] + "\n")
            out.write("\n")


def configure_and_build_unicorn(targets):
    build_suffix = suffix_for(targets)
    build_dir = UNICORN_DIR / f"build-js{build_suffix}"

    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)

    emcmake = shutil.which("emcmake")
    if not emcmake:
        raise RuntimeError("emcmake not found. Please install and activate Emscripten SDK first.")

    cmake_cmd = [
        emcmake,
        "cmake",
        "..",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DUNICORN_BUILD_TESTS=OFF",
        "-DUNICORN_INSTALL=OFF",
        "-DUNICORN_LEGACY_STATIC_ARCHIVE=ON",
    ]
    if targets:
        cmake_cmd.append("-DUNICORN_ARCH=" + ";".join(sorted(targets)))

    env = os.environ.copy()
    env.pop("NODE", None)
    if "EM_NODE_JS" not in env:
        node_bin = shutil.which("node")
        if node_bin:
            env["EM_NODE_JS"] = node_bin

    run(cmake_cmd, cwd=build_dir, env=env)
    run(
        ["cmake", "--build", ".", "--config", "Release", "-j", str(os.cpu_count() or 4)],
        cwd=build_dir,
        env=env,
    )

    static_lib = build_dir / "libunicorn.a"
    if not static_lib.exists():
        raise RuntimeError(f"Expected library not found: {static_lib}")
    return static_lib


def link_to_javascript(static_lib, targets):
    emcc = shutil.which("emcc")
    if not emcc:
        raise RuntimeError("emcc not found. Please install and activate Emscripten SDK first.")

    out_suffix = suffix_for(targets)
    output_js = SRC_DIR / f"libunicorn{out_suffix}.out.js"
    output_wasm = SRC_DIR / f"libunicorn{out_suffix}.out.wasm"

    cmd = [
        emcc,
        "-O3",
        str(static_lib),
        "-sALLOW_MEMORY_GROWTH=1",
        "-sALLOW_TABLE_GROWTH=1",
        "-sWASM=1",
        "-sSINGLE_FILE=1",
        "-sWASM_ASYNC_COMPILATION=0",
        "-sWASM_BIGINT=0",
        "-sENVIRONMENT=web",
        "-sEXPORT_NAME=MUnicorn",
        "-sEXPORTED_FUNCTIONS=" + json.dumps(EXPORTED_FUNCTIONS),
        "-sEXPORTED_RUNTIME_METHODS=" + json.dumps(EXPORTED_RUNTIME_METHODS),
        "-o",
        str(output_js),
    ]
    run(cmd, cwd=ROOT_DIR)
    if output_wasm.exists():
        output_wasm.unlink()


def build(targets):
    validate_targets(targets)
    ensure_submodule()
    apply_emscripten_patches()
    generate_constants()
    static_lib = configure_and_build_unicorn(targets)
    link_to_javascript(static_lib, targets)


def usage():
    print(f"Usage: {Path(sys.argv[0]).name} <action> [<targets>...]")
    print("Actions:")
    print("  patch  Apply emscripten patches and regenerate constants")
    print("  build  Build unicorn.js with cmake/emscripten")


def main():
    if len(sys.argv) < 2:
        usage()
        return 1

    action = sys.argv[1]
    targets = sorted(sys.argv[2:])

    try:
        if action == "patch":
            ensure_submodule()
            apply_emscripten_patches()
            generate_constants()
            print("Patches and constants regenerated.")
            return 0
        if action == "build":
            build(targets)
            return 0

        usage()
        return 1
    except (subprocess.CalledProcessError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
