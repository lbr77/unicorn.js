Unicorn.js
==========
[![Last Release](https://img.shields.io/badge/version-0.9-brightgreen.svg?style=flat)](https://github.com/AlexAltea/unicorn.js/releases)

Port of the [Unicorn](https://github.com/unicorn-engine/unicorn) CPU emulator framework for JavaScript. Powered by [Emscripten](https://github.com/kripken/emscripten).

**Notes:** _Unicorn_ is a lightweight multi-architecture CPU emulator framework originally developed by Nguyen Anh Quynh, Dang Hoang Vu et al. and released under GPLv2 license. More information about contributors and license terms can be found in the files `AUTHORS.TXT`, `CREDITS.TXT` and `COPYING` inside the *unicorn* submodule of this repository.

## Installation
To add Unicorn.js to your web application, include it with:
```html
<script src="unicorn.min.js"></script>
```
or install it with the Bower command:
```bash
bower install unicornjs
```

## Usage                                                      
```javascript
var addr = 0x10000;
var code = [
  0x37, 0x00, 0xA0, 0xE3,  // mov r0, #0x37
  0x03, 0x10, 0x42, 0xE0,  // sub r1, r2, r3
];

// Initialize engine
var e = new uc.Unicorn(uc.ARCH_ARM, uc.MODE_ARM);

// Write registers and memory
e.reg_write_i32(uc.ARM_REG_R2, 0x456);
e.reg_write_i32(uc.ARM_REG_R3, 0x123);
e.mem_map(addr, 4*1024, uc.PROT_ALL);
e.mem_write(addr, code);

// Start emulator
var begin = addr;
var until = addr + code.length;
e.emu_start(begin, until, 0, 0);

// Read registers
var r0 = e.reg_read_i32(uc.ARM_REG_R0);  // 0x37
var r1 = e.reg_read_i32(uc.ARM_REG_R1);  // 0x333
```

If you load unicorn.js in an async module pipeline, use `uc.block_until_ready(function () { ... })` or `uc.ready.then(...)`.

## Building
Unicorn.js now builds Unicorn via CMake, following Unicorn's `docs/COMPILE.md` workflow.

1. Initialize and update the Unicorn submodule:
   - `git submodule update --init --recursive`
   - `git submodule update --remote --recursive`
2. Install Unicorn native build dependencies (`cmake`, `pkg-config`, `make`, C compiler toolchain).
3. Install [Emscripten SDK](https://emscripten.org/docs/getting_started/downloads.html) and activate it (`emcmake` and `emcc` must be in `PATH`).
4. Install [Python 3.8+](https://www.python.org/downloads/) (both `python3` and `python` callable).
5. Install JavaScript dependencies and grunt CLI:
   - `npm ci --include=dev`
   - `npm install -g grunt-cli`
6. Build:
   - `grunt build`
   - `grunt build:arm` (ARM-only build, outputs `dist/unicorn-arm.min.js`)
   - (optional) `grunt release` for all configured architectures.
