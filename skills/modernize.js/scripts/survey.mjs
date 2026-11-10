#!/usr/bin/env node
/*
 * survey.mjs: mechanical facts about a legacy Node.js package, as JSON.
 *
 *   node survey.mjs [package-dir]
 *
 * Reads only. No network, no dependencies, no installs. It decides nothing:
 * it answers the questions that would otherwise take a dozen greps, so the
 * judgement calls get the attention.
 */

import { execFileSync } from 'node:child_process'
import { existsSync, readdirSync, readFileSync, realpathSync, statSync } from 'node:fs'
import path from 'node:path'

const root = path.resolve(process.argv[2] ?? '.')

const SKIP = new Set([
  'node_modules', '.git', 'dist', 'build', 'coverage', 'vendor', '.types-gen', '.pnpm-store'
])
const SOURCE = /\.(?:js|cjs|mjs)$/

const exists = rel => existsSync(path.join(root, rel))
const readText = rel => readFileSync(path.join(root, rel), 'utf8')

function readJson(rel) {
  try {
    return JSON.parse(readText(rel))
  } catch {
    return null
  }
}

// tsconfig files allow comments and trailing commas.
function readJsonc(rel) {
  try {
    const text = readText(rel)
      .replace(/("(?:\\.|[^"\\])*")|\/\/[^\n]*|\/\*[\s\S]*?\*\//g, (_, str) => str ?? '')
      .replace(/,(\s*[}\]])/g, '$1')
    return JSON.parse(text)
  } catch {
    return null
  }
}

function walk(dir, out = []) {
  let entries
  try {
    entries = readdirSync(path.join(root, dir), { withFileTypes: true })
  } catch {
    return out
  }
  for (const entry of entries) {
    if (SKIP.has(entry.name)) continue
    const rel = path.join(dir, entry.name)
    if (entry.isDirectory()) walk(rel, out)
    else if (entry.isFile()) out.push(rel)
  }
  return out
}

function git(...args) {
  try {
    return execFileSync('git', ['-C', root, ...args], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore']
    }).trim()
  } catch {
    return null
  }
}

const pkg = readJson('package.json')
if (!pkg) {
  console.error(`survey: no readable package.json in ${root}`)
  process.exit(1)
}

const files = walk('.').map(file => file.split(path.sep).join('/'))
const sources = files.filter(file => SOURCE.test(file))

// Each idiom: what it is called, and the pattern that finds it.
const IDIOMS = {
  require: /\brequire\s*\(/g,
  commonjs_exports: /\bmodule\.exports\b|(?<![.\w])exports\.\w+\s*=/g,
  esm_syntax: /^\s*(?:import\s[^(]|export\s)/gm,
  var: /^\s*var\s/gm,
  arguments_object: /(?<![.\w])arguments(?:\[|\.length|\s*[,)])/g,
  util_inherits: /\butil\.inherits\s*\(|\binherits\s*\(\s*\w+\s*,/g,
  util_extend: /\butil\._extend\s*\(/g,
  new_buffer: /\bnew\s+Buffer\s*\(/g,
  url_parse: /\burl\.parse\s*\(/g,
  process_next_tick: /\bprocess\.nextTick\s*\(/g,
  error_first_callback: /function\s*\w*\s*\(\s*err(?:or)?\s*[,)]|\(\s*err(?:or)?\s*,[^)]*\)\s*=>/g,
  builtin_prototype_patch:
    /(?:^|[^.\w])(?:Error|Object|Array|String|Function|Number|Date|Promise|RegExp)\.prototype(?:\.\w+\s*=[^=]|\[[^\]]+\]\s*=[^=])|Object\.definePropert(?:y|ies)\s*\(\s*(?:Error|Object|Array|String|Function|Number|Date|Promise|RegExp)\.prototype/g,
  stack_surgery: /\.stack\s*=|\.stack\.split\s*\(|captureStackTrace/g,
  dirname_filename: /\b__dirname\b|\b__filename\b/g,
  module_parent: /\bmodule\.parent\b|\brequire\.main\b/g,
  use_strict: /^\s*['"]use strict['"]/gm,
  domains: /require\s*\(\s*['"]domain['"]\s*\)/g,
  process_binding: /\bprocess\.binding\s*\(/g
}

const idioms = {}
for (const name of Object.keys(IDIOMS)) idioms[name] = { count: 0, files: [] }

let sourceLines = 0
for (const file of sources) {
  let text
  try {
    if (statSync(path.join(root, file)).size > 2_000_000) continue
    text = readText(file)
  } catch {
    continue
  }
  sourceLines += text.split('\n').length
  for (const [name, pattern] of Object.entries(IDIOMS)) {
    const count = text.match(pattern)?.length ?? 0
    if (!count) continue
    idioms[name].count += count
    idioms[name].files.push({ file, count })
  }
}
for (const entry of Object.values(idioms)) {
  entry.files.sort((a, b) => b.count - a.count)
  if (entry.files.length > 12) {
    entry.more_files = entry.files.length - 12
    entry.files.length = 12
  }
}

const allDeps = { ...pkg.dependencies, ...pkg.devDependencies, ...pkg.peerDependencies }

const RUNNERS = [
  'vows', 'mocha', 'tap', 'tape', 'jasmine', 'nodeunit', 'expresso', 'ava', 'jest', 'vitest', 'lab'
]
const testScript = pkg.scripts?.test ?? null
const runners = RUNNERS.filter(
  name => name in allDeps || new RegExp(`\\b${name}\\b`).test(testScript ?? '')
)
if (/node\s+(?:--\S+\s+)*--test\b/.test(testScript ?? '')) runners.push('node:test')

// Dependencies the platform has since absorbed, or that are known dead ends.
const SUPERSEDED = {
  request: 'fetch',
  'node-fetch': 'fetch',
  got: 'fetch, unless its retry or pagination helpers are in use',
  superagent: 'fetch',
  axios: 'fetch',
  async: 'async/await and Promise combinators',
  q: 'native Promise',
  bluebird: 'native Promise',
  step: 'async/await',
  mkdirp: 'fs.mkdir with recursive',
  rimraf: 'fs.rm with recursive',
  glob: 'fs.glob at a recent floor',
  optimist: 'util.parseArgs',
  minimist: 'util.parseArgs',
  colors: 'util.styleText',
  'node-uuid': 'crypto.randomUUID',
  uuid: 'crypto.randomUUID for v4',
  underscore: 'language built-ins',
  lodash: 'language built-ins, per function used',
  'object-assign': 'Object.assign',
  inherits: 'class extends',
  'safe-buffer': 'Buffer.from and Buffer.alloc',
  xtend: 'object spread',
  'left-pad': 'String.prototype.padStart'
}
const superseded = Object.keys(pkg.dependencies ?? {})
  .filter(name => name in SUPERSEDED)
  .map(name => ({ name, range: pkg.dependencies[name], consider: SUPERSEDED[name] }))

const ci = {
  travis: exists('.travis.yml'),
  appveyor: exists('appveyor.yml') || exists('.appveyor.yml'),
  circleci: exists('.circleci/config.yml'),
  github_actions: files.filter(file => /^\.github\/workflows\/[^/]+\.ya?ml$/.test(file))
}

// The sibling declaration trap: a .d.ts beside a .js removes the .js from
// TypeScript's program, so checkJs in a config that includes both is inert.
const siblingDeclarations = sources
  .filter(file => file.endsWith('.js'))
  .filter(file => files.includes(file.replace(/\.js$/, '.d.ts')))

const tsconfigs = files
  .filter(file => /^tsconfig[^/]*\.json$/.test(file))
  .map(file => {
    const config = readJsonc(file)
    const options = config?.compilerOptions ?? {}
    const include = config?.include ?? null
    const exclude = config?.exclude ?? []
    const includesJs = !include || include.some(glob => /\.js$|\*\*\/\*$|^[^*.]+\/?$/.test(glob))
    const excludesDts = exclude.some(glob => /\.d\.ts$/.test(glob))
    return {
      file,
      parsed: config !== null,
      checkJs: options.checkJs ?? false,
      allowJs: options.allowJs ?? false,
      noEmit: options.noEmit ?? false,
      skipLibCheck: options.skipLibCheck ?? false,
      emitDeclarationOnly: options.emitDeclarationOnly ?? false,
      outDir: options.outDir ?? null,
      include,
      exclude,
      checkjs_probably_inert:
        Boolean(options.checkJs) && includesJs && !excludesDts && siblingDeclarations.length > 0
    }
  })

const exportTypes = []
;(function collect(node) {
  if (!node || typeof node !== 'object') return
  for (const [key, value] of Object.entries(node)) {
    if (key === 'types' && typeof value === 'string') exportTypes.push(value)
    else collect(value)
  }
})(pkg.exports)

// History is scoped to this directory, so a package inside a monorepo reports
// its own timeline. Tags describe the whole repository, so they are reported
// only when this directory is the repository root.
const toplevel = git('rev-parse', '--show-toplevel')
const isRepoRoot = toplevel !== null && realpathSync(toplevel) === realpathSync(root)
const tags = isRepoRoot ? (git('tag', '--sort=creatordate')?.split('\n').filter(Boolean) ?? []) : []
const scripts = pkg.scripts ?? {}
const workflowText = ci.github_actions.map(readText).join('\n')
const aggregate = ['check', 'verify', 'validate'].find(name => name in scripts) ?? null

const report = {
  root,
  package: {
    name: pkg.name ?? null,
    version: pkg.version ?? null,
    type: pkg.type ?? 'commonjs (implicit)',
    main: pkg.main ?? null,
    has_exports_map: pkg.exports !== undefined,
    export_subpaths: pkg.exports && typeof pkg.exports === 'object' ? Object.keys(pkg.exports) : [],
    types: pkg.types ?? pkg.typings ?? null,
    export_types: exportTypes,
    bin: pkg.bin ?? null,
    files: pkg.files ?? null,
    engines: pkg.engines ?? null,
    package_manager: pkg.packageManager ?? null,
    scripts
  },
  module_system:
    idioms.require.count + idioms.commonjs_exports.count === 0
      ? 'esm'
      : idioms.esm_syntax.count === 0
        ? 'commonjs'
        : 'mixed',
  source: { files: sources.length, lines: sourceLines },
  idioms,
  tests: {
    script: testScript,
    runners,
    test_files: files.filter(file => /(?:^|\/)tests?\//.test(file) && SOURCE.test(file)).length,
    example_files: files.filter(file => /^examples?\//.test(file) && SOURCE.test(file)).length,
    examples_run_by_a_script: Object.values(scripts).some(cmd => /examples?/.test(cmd)),
    needs_config_or_credentials: files.filter(file =>
      /(?:^|\/)tests?\/.*(?:config|credentials|secrets?)[^/]*\.(?:json|ya?ml)(?:\.example|\.sample)?$/.test(file)
    )
  },
  ci: {
    ...ci,
    aggregate_script: aggregate,
    workflows_run_aggregate_script: aggregate
      ? new RegExp(`\\brun\\s+${aggregate}\\b|\\b(?:pnpm|yarn|bun)\\s+${aggregate}\\b`).test(workflowText)
      : null,
    prepublish_only: scripts.prepublishOnly ?? scripts.prepublish ?? null
  },
  lockfiles: ['package-lock.json', 'npm-shrinkwrap.json', 'pnpm-lock.yaml', 'yarn.lock', 'bun.lock', 'bun.lockb']
    .filter(exists),
  dependencies: {
    runtime: pkg.dependencies ?? {},
    dev: pkg.devDependencies ?? {},
    peer: pkg.peerDependencies ?? {},
    superseded
  },
  types: {
    declaration_files: files.filter(file => file.endsWith('.d.ts')).length,
    sibling_declarations: siblingDeclarations,
    tsconfigs
  },
  docs: {
    readme: files.find(file => /^readme(?:\.\w+)?$/i.test(file)) ?? null,
    changelog: files.find(file => /(?:^|\/)(?:changelog|history|changes)(?:\.\w+)?$/i.test(file)) ?? null,
    migration: files.filter(file => /(?:^|\/)(?:migrat\w*|upgrad\w*)[^/]*\.md$/i.test(file))
  },
  git: {
    is_repository_root: isRepoRoot,
    first_commit: git('log', '--reverse', '--format=%ad', '--date=short', '--', '.')?.split('\n')[0] || null,
    last_commit: git('log', '-1', '--format=%ad', '--date=short', '--', '.') || null,
    commits: Number(git('rev-list', '--count', 'HEAD', '--', '.') ?? 0),
    tags: tags.length,
    first_tag: tags[0] ?? null,
    last_tag: tags.at(-1) ?? null,
    tag_forms: [...new Set(tags.map(tag => (tag.startsWith('v') ? 'v1.2.3' : '1.2.3')))]
  }
}

// Plain statements of what the facts above imply. Each names its evidence.
const flags = []
const flag = (id, detail) => flags.push({ id, detail })

if (report.module_system !== 'esm') {
  flag('commonjs', `${idioms.require.count} require() calls, ${idioms.commonjs_exports.count} CommonJS exports`)
}
if (!report.package.has_exports_map) {
  flag('no-exports-map', 'every file is deep-importable; adding a map closes the package')
}
if (!pkg.engines?.node) flag('no-engines', 'no engines.node')
else if (/(?:^|[^\d.])0\.\d+/.test(pkg.engines.node)) flag('ancient-engines', `engines.node is "${pkg.engines.node}"`)
if (idioms.builtin_prototype_patch.count) {
  flag(
    'patches-builtin-prototype',
    `${idioms.builtin_prototype_patch.files.map(entry => entry.file).join(', ')}: removing this is a breaking change`
  )
}
if (idioms.module_parent.count) flag('uses-module-parent', 'no ESM equivalent; the caller must pass itself in')
const deadRunners = runners.filter(name => ['vows', 'nodeunit', 'expresso'].includes(name))
if (deadRunners.length) flag('unmaintained-test-runner', deadRunners.join(', '))
if (!testScript || /no test specified/.test(testScript)) flag('no-tests', 'no usable test script')
if (report.tests.needs_config_or_credentials.length) {
  flag('tests-need-credentials', report.tests.needs_config_or_credentials.join(', '))
}
if (report.tests.example_files && !report.tests.examples_run_by_a_script) {
  flag('examples-not-run', `${report.tests.example_files} example files, no script runs them`)
}
if ((ci.travis || ci.appveyor || ci.circleci) && !ci.github_actions.length) {
  flag('dead-ci', 'only legacy CI configuration present')
}
if (!ci.travis && !ci.appveyor && !ci.circleci && !ci.github_actions.length) flag('no-ci', 'no CI configuration')
if (aggregate && ci.github_actions.length && report.ci.workflows_run_aggregate_script === false) {
  flag('ci-skips-aggregate-check', `no workflow runs "${aggregate}"; its gates run only where a human runs them`)
}
for (const config of tsconfigs) {
  if (config.checkjs_probably_inert) {
    flag(
      'checkjs-probably-inert',
      `${config.file} sets checkJs, but ${siblingDeclarations.length} source files have a sibling .d.ts, which removes them from the program. Confirm with: tsc -p ${config.file} --listFiles`
    )
  }
}
if (siblingDeclarations.length && !tsconfigs.some(config => config.checkJs && !config.checkjs_probably_inert)) {
  flag('jsdoc-unchecked', 'hand-written declarations exist and no config typechecks the JavaScript beside them')
}
if (siblingDeclarations.length && tsconfigs.length && tsconfigs.every(config => config.skipLibCheck)) {
  flag(
    'declarations-unchecked',
    'every tsconfig sets skipLibCheck, which also skips the hand-written .d.ts files; only their syntax is checked'
  )
}
if (superseded.length) flag('superseded-dependencies', superseded.map(dep => dep.name).join(', '))
if (!report.lockfiles.length) flag('no-lockfile', 'no lockfile committed')
if (report.git.tag_forms.length > 1) flag('mixed-tag-forms', 'tags use both v1.2.3 and 1.2.3; follow the most recent')

report.flags = flags
console.log(JSON.stringify(report, null, 2))
