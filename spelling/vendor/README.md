# Reproducible spelling-engine build inputs

This directory holds the **unmodified** build input from
[melker12345/Spell-Checker](https://github.com/melker12345/Spell-Checker)
at commit `de4d06e04f406b6ea098c11770398069888275c9`. It is retained
separately from the Firefox runtime package.

- `src/index.js`: readable CommonJS entry point for the nspell factory.
- `package.json`, `package-lock.json`: original npm configuration and
  integrity-locked dependency tree (official npm registry).
- `nspell@2.1.5`: original MIT-licensed spellchecker by Titus Wormer,
  https://github.com/wooorm/nspell.
- `browserify@17.0.1`: build-only bundler, installed by `npm ci`.
- `is-buffer@2.0.5`: transitive runtime dependency of nspell (MIT);
  the bundled notice is in `../IS-BUFFER-LICENSE.txt`.

The shipped `../nspell-bundle.js` is byte-for-byte identical to the
`nspell-bundle.js` file at the pinned Melker commit (Git blob
`a94f143a256f96ce12d261aff4ade2a400cddd2b`). That identity
by itself is **not** proof of a reproducible build: the verification
command below rebuilds it from the locked source and compares all bytes.

## Rebuild/verification instructions for AMO

Use Node.js 22+ and npm on Ubuntu/Linux or another supported Node platform,
with network access to the official npm registry for the initial install.
From repository root, run:

```sh
node scripts/verify-spelling.cjs
npm run build-for-amo
```

The verifier calls `npm ci --ignore-scripts --no-audit --no-fund` in
this directory, executes the locked Browserify CLI with
`browserify src/index.js -s nspell -o <temporary-output>`, then
requires a **byte-for-byte** match with the shipped bundle. It does not
rewrite the shipped file. If any byte differs, it fails and the extension
must not be submitted to Mozilla.

`npm run build-for-amo` repeats verification and creates the clean AMO
runtime ZIP at `dist/ELF-SHELL-Ayarime-v0.5.4-AMO.zip`.

The source package for Mozilla must include this directory and the project
source scripts. Never package `node_modules` or this build-input directory
in the runtime extension.
