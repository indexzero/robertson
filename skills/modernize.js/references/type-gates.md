# Types that are actually checked

Read this before writing a `tsconfig` in Step 5, and during an `audit`.

Contents: [Choose a strategy](#choose-a-strategy) ·
[The sibling declaration trap](#the-sibling-declaration-trap) ·
[Three gates](#three-gates) · [What assignability misses](#what-assignability-misses) ·
[Annotation lessons](#annotation-lessons) · [Auditing an existing setup](#auditing-an-existing-setup)

## Choose a strategy

**Generated declarations (default).** Write JSDoc in `src/*.js`. One
`tsconfig` includes the JavaScript with `allowJs`, `checkJs`, `declaration`,
and `emitDeclarationOnly`, and emits to `dist/`. `exports` points `types` at
`dist/` and `default` at `src/`. `prepublishOnly` builds. There is one source
of truth, so nothing can drift.

**Hand-written declarations.** Choose this only when the declaration must say
something JSDoc cannot express. The usual case is a correlated union, where
checking one member narrows another:

```ts
type Result<T, E = Error> =
  | (readonly [T, undefined] & { ok: true; value: T; error: undefined })
  | (readonly [undefined, E] & { ok: false; value: undefined; error: E })
```

The cost is that two descriptions of every function now exist, written by
hand, and nothing compares them unless you build the comparison.

## The sibling declaration trap

When `src/thing.d.ts` sits beside `src/thing.js`, TypeScript resolves the
import to the declaration and drops the `.js` from the program. This is true
even when the `tsconfig` lists `src/**/*.js` in `include` and sets
`checkJs: true`.

The consequences, all observed in one released 1.0.0:

- `checkJs` checked nothing. Dozens of JSDoc errors accumulated unseen.
- A script named `build:types` emitted nothing, because there was no source
  left in the program to emit from. It ran in `prepublishOnly` for the whole
  release.
- A declaration said `export { Thing } from './thing.js'` for a class the
  module did not re-export. Consumers' code typechecked and then threw
  `SyntaxError: does not provide an export named 'Thing'` at import.
- A declaration promised a second parameter the implementation had removed.

Every gate was green throughout. The way to see it:

```bash
npx tsc -p tsconfig.json --listFiles | grep -v node_modules
```

If that prints declarations and no JavaScript, the JavaScript is unchecked.

## Three gates

Each has its own config, because no single program can hold both halves.

| Script | Config | Includes | Proves |
|---|---|---|---|
| `check:dts` | `tsconfig.json` | `src/**/*.d.ts`, `noEmit`, `skipLibCheck: false` | The declarations are valid TypeScript. |
| `check:js` | `tsconfig.check.json` | `src/**/*.js`, excludes `src/**/*.d.ts`, `allowJs`, `checkJs`, `noEmit` | The JSDoc agrees with the code under it. |
| `check:types` | `tsconfig.types-gen.json` then `tsconfig.types.json` | generate declarations from the JSDoc into a gitignored `.types-gen/`, then typecheck `test/types/conformance.ts` | The two halves agree with each other. |

`skipLibCheck` skips **every** `.d.ts` in the program, and that includes the
ones you wrote. With it on, `check:dts` reports syntax errors and nothing
else: a parameter typed with a name that does not exist exits 0. Turn it off
in the config whose whole job is to check declarations. If a dependency's
types then fail, fix that with a narrower `types` or `lib` list, not by
turning the check back off. The other configs can keep it.

Put a `"//"` key at the top of each config saying what it checks and why it
is separate. The next reader will otherwise merge them back into one.

`check` runs all three after the linter. `prepublishOnly` runs `check`. CI
runs `check`.

The conformance file imports each module twice and assigns across:

```ts
import type * as Gen from '../../.types-gen/thing.js'
import type * as Hand from '../../src/thing.js'

declare const hand: typeof Hand
declare const gen: typeof Gen

// The declaration must not promise more than the code has.
export const handFromGen: typeof Hand = gen
// The declaration must not be more precise than the JSDoc.
export const genFromHand: typeof Gen = hand
```

Assert both directions. With only the first, the JSDoc is free to be the
vaguer half and loosening an annotation goes unnoticed. When the second
direction reports a divergence, close it by making the JSDoc more precise,
not by loosening the declaration. In practice the hand-written side is
usually right.

A class with `#private` fields is nominally typed. A generated declaration
and a hand-written one for the same class can never be mutually assignable:
omit the brand and the member is missing, declare it and the compiler reports
that it refers to a different member. For modules that export such a class,
assert the second direction per export instead of per module, and describe
inputs structurally (`{ errors: Error[] }`) rather than by class name
wherever the implementation only reads a shape.

## What assignability misses

A function of fewer parameters is assignable to a type that expects more. So
a declaration that adds an **optional** parameter the implementation lacks
passes both directions. That is exactly the drift that happens when a
parameter is refactored away.

Pin arity twice:

```ts
// test/types/conformance.ts
export const arity: Parameters<typeof Hand.toJSON>['length'] = 1
```

```js
// test/thing.test.js
assert.equal(toJSON.length, 1)
```

Either alone is escapable. Arity also matters at runtime: a public optional
second parameter breaks `items.map(fn)`, which passes the index into it.

## Annotation lessons

Checking JSDoc for the first time on old code produces a worklist. Most of
it is annotations that describe a narrower function than the one below them.
Fix the annotation. A correct fix accepts no less than before and changes no
runtime behaviour.

- **Polymorphic parameters.** `{string|object|Array|function}` says "one of
  four" and so forbids reading a property off it. Write a typedef naming each
  form the code handles, including a thunk that returns the others.
- **Reassigned parameters.** `fn(type, opts)` that does `opts = type` when
  called with one argument needs `@overload` tags.
- **Caught values.** A parameter the body guards against `null` and
  non-objects is `unknown`, not `Error`. An error's `cause` is `unknown` too.
- **Constructor types.** `new (...args: unknown[]) => Error` rejects every
  subclass with a typed constructor, because parameters are contravariant.
  Use `any[]` here and write down why.
- **Metadata on errors.** `Error` has no index signature. Code that copies
  arbitrary properties onto one needs a `Error & Record<string, unknown>`
  typedef.
- **Engine-specific APIs.** `@types/node` declares `Error.captureStackTrace`
  as always present, so `if (Error.captureStackTrace)` reads as a mistake.
  `typeof ... === 'function'` says the same thing without the complaint.
- **Type-only re-exports.** A type re-exported from a declaration with
  `export { T }` claims a runtime value. Use `export type { T }`.

## Auditing an existing setup

Ask these of any repository that reports a clean typecheck:

1. `tsc --listFiles` for each config: is the JavaScript in the program?
   And is `skipLibCheck` on in the config that is meant to check the
   hand-written declarations?
2. For each script whose name claims an artifact: does it produce one?
3. Is every export in each declaration also exported by the module? Import
   each name at runtime and find out.
4. Does `fn.length` match the declared parameter count for each export?
5. Does CI run the same aggregate script as `prepublishOnly`?

Then break something on purpose in each direction and confirm a gate fails:
a phantom export in a declaration, an extra optional parameter in a
declaration, a loosened JSDoc annotation, and a reference to an undeclared
type inside a declaration.
