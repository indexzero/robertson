# Documents and release

Read this in Step 8 and Step 9.

## Migration guide

One section per row of the Step 2 table, each in the same form so a reader
can scan it:

````markdown
### <what changed, as a statement>

<One or two sentences: why it changed.>

**Before:**

```js
<old call site>
```

**After:**

```js
<new call site>
```

<How a missed migration fails, and what to grep for if it fails quietly.>
````

Open the guide with the numbered summary of breaks and the requirements
(engines floor, module system). Follow the breaks with a table of renames:
old name, new name, the major that removes the alias.

Say honestly how each break fails when missed. "Array-destructuring the
returned promise throws a `TypeError`" is useful. So is the less comfortable
case next to it: "reading `.ok` on the promise is `undefined`, which looks
like a failure that never happened. Grep for `.trap(`."

Ship one runnable `examples/migration.js` that shows old and new call sites
working against the same build. If it labels a line as old-style code, that
line must have been valid in the old version.

## Changelog

Rebuild the history from the tags, oldest release to newest, in the Keep a
Changelog form. `git log <prev-tag>..<tag> --oneline` gives each section.
Old commit prefixes (`[api]`, `[fix]`, `[dist]`, `[doc]`, `[test]`) map
directly onto Added, Fixed, and Changed. Drop version bumps and CI churn.

For the new major, record removals of things that never worked (a build
script that emitted nothing, an export that threw at import) under Changed or
Fixed with one sentence on what they claimed. Silence about a fake gate
teaches nobody.

## README

Rewrite examples in the new dialect and run every one of them. Keep the
package's voice. A README that explained itself in 2011 with a motivation
section still wants that section.

State the engines floor once, near the install command.

## Release

Prepare, do not publish:

1. `prepublishOnly` runs the aggregate check and the tests.
2. `npm pack --dry-run` lists exactly the files `exports` needs.
3. The version commit is alone and last.
4. The tag follows the repository's existing tag form. Old repositories
   often switched between `v1.2.3` and `1.2.3`. Use the most recent.

Publish from CI through trusted publishing where the owner has it set up,
not from a token on a workstation. Provenance records where the artifact was
built. It does not record that the source was reviewed, so the protection is
only as strong as the controls on the repository and the workflow file.

A first modern release of a package with real dependents is a candidate for
a prerelease tag (`next`) before `latest`.

## Pull request body

Lead with why the package is being revived, then the breaking-change table,
then the new surface with one example each, then the migration pointer.
Section the review findings separately from the features: a reader deciding
whether to trust the branch wants to see what was found and how.

Leave out counts of tests, errors, or examples. Nothing in the repository can
check a PR body, so it is the first place a stale number survives.
