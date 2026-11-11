# Old idiom to current platform

Read this during Step 3. The survey script reports where each idiom on the
left occurs.

Contents: [Source](#source) · [package.json](#packagejson) ·
[Dependencies](#dependencies) · [Layout](#layout)

Version numbers in this file are the ones that were true when it was written.
Confirm any that matter against the Node documentation for the engines floor
you chose.

## Source

| Legacy | Current | Watch for |
|---|---|---|
| `var x = require('x')` | `import x from 'x'` | A conditional or lazy `require` becomes `await import()`, which makes its caller async. Keep top-level `await` out of the entry graph so CommonJS callers can still `require()` the package. |
| `require('fs')` | `import fs from 'node:fs'` | The `node:` prefix cannot be shadowed by a package of the same name. |
| `exports.a = ...`, `module.exports = fn` | named exports, plus a default export if callers used `const pkg = require('pkg')` | A `module.exports = fn` with properties hung on it needs both the default and the named forms to keep old call sites working. |
| `__dirname`, `__filename` | `import.meta.dirname`, `import.meta.filename` | |
| `require('./package.json')` | `JSON.parse(readFileSync(new URL('./package.json', import.meta.url)))` or an import attribute | |
| `module.parent`, `require.main === module` | `import.meta.main` where the floor has it, otherwise compare `import.meta.url` to `process.argv[1]` | Packages that walked `module.parent` to find their caller have no ESM equivalent. The caller must pass itself in. This is a breaking change and belongs in the Step 2 table. |
| `var` | `const`, then `let` | A `var` hoisted out of a block and read after it is the one place this changes behaviour. |
| `arguments`, `[].slice.call(arguments)` | rest parameters | Functions that reassign their own parameters by position (`if (!cb) { cb = opts; opts = {} }`) keep working, but describe the overloads in JSDoc. |
| `mixin(a, b)`, `util._extend`, `Object.keys(b).forEach(...)` | `Object.assign`, spread | An old mixin often copied getters or non-enumerables. Read it before replacing it. |
| `util.inherits(A, B)` | `class A extends B` | |
| custom error with `Error.call(this)` and `captureStackTrace` | `class X extends Error` with `super(message, { cause })` | `Error.captureStackTrace` is V8 only. Guard with `typeof Error.captureStackTrace === 'function'`. |
| hand-rolled wrapped errors | `new Error(msg, { cause })` | |
| collecting errors into an array and throwing the first | `AggregateError` | |
| `Error.prototype.toJSON = ...` or any patch to a built-in prototype | an exported function | Always a breaking change. Callers relied on `JSON.stringify(err)` working. |
| `function (err, result)` callbacks | `async` functions | Keeping a callback overload alongside the promise form is legitimate for a heavily used API. A function that is sometimes synchronous and sometimes asynchronous is not: give the synchronous path its own name. |
| the `async` package, `step`, `q`, `bluebird` | `async`/`await`, `Promise.all`, `Promise.allSettled`, `for await` | `Promise.all` over started promises cannot limit concurrency. If the old code used `async.eachLimit`, the replacement must take thunks. |
| `process.nextTick(fn)` | `queueMicrotask(fn)` | Ordering relative to other queued work differs slightly. Only matters if a test pins it. |
| `new Buffer(x)` | `Buffer.from(x)`, `Buffer.alloc(n)` | The old form is a security hazard when `x` is a number. |
| `url.parse(u)` | `new URL(u, base)` | WHATWG parsing normalizes differently. If the result reaches a wire, add it to the baseline corpus first. |
| `a && a.b && a.b.c` | `a?.b?.c` | Not equivalent when a link is `0` or `''` and the old code relied on the short-circuit value. |
| `x = x \|\| def` | `x ??= def` | Only where `0`, `''`, and `false` are meant to survive. If the old code relied on them being replaced, this is a behaviour change. |
| string stack surgery (`stack.split('\n').splice(1, 1)`) | check the format before editing it, or stop editing it | V8 puts the message on line 0. Other engines put the first frame there. |
| `'use strict'` | delete | Modules are strict. |

## package.json

The target shape. Fields the legacy file usually lacks are marked.

```jsonc
{
  "type": "module",                      // new
  "exports": {                           // new: closes the package
    ".": { "types": "./dist/index.d.ts", "default": "./src/index.js" },
    "./thing": { "types": "./dist/thing.d.ts", "default": "./src/thing.js" },
    "./package.json": "./package.json"
  },
  "files": ["src", "dist"],              // new: publish an allowlist
  "sideEffects": false,                  // only once the prototype patches are gone
  "engines": { "node": ">=NN" },         // from the release schedule
  "packageManager": "pnpm@X.Y.Z",        // whatever the owner uses elsewhere
  "scripts": {
    "test": "node --test 'test/**/*.test.js'",
    "check": "<lint> && <every type gate>",
    "prepublishOnly": "<pm> run check && <pm> test"
  }
}
```

- Put `types` first in each condition object. Resolution takes the first
  match.
- Quote the test glob. Unquoted, the shell expands it, and `sh` does not
  expand `**`.
- Keep `main` only if a tool the owner uses still reads it.
- Replace `maintainers` with `contributors`. Fix an `http://` repository URL.
- After the first build, run `npm pack --dry-run` and read the file list. A
  `files` allowlist that misses a directory publishes a package that fails at
  import.

## Dependencies

For each dependency, in this order:

1. **Does the platform do it now?** `request`, `node-fetch`, `mkdirp`,
   `rimraf`, `glob`, `uuid` (v4), `colors`, `minimist`, `async`, and most
   promise libraries have built-in replacements at a current floor.
2. **Is it maintained?** Check the last publish date and whether it is
   deprecated on the registry.
3. **Does the replacement have the helper you relied on?** `fetch` does not
   throw on a non-2xx status, does not retry, and does not paginate. If the
   old client did, you are now the author of that behaviour and it needs
   tests.

A dependency on the package's own older self, through a sibling package, is
common in old ecosystems. Modernize the leaf first.

## Layout

A `lib/` to `src/` move is cosmetic. Do it only to match the owner's other
repositories, do it as a commit of pure renames, and add an `exports` subpath
for every file callers deep-imported from `lib/`.
