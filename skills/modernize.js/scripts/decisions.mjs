#!/usr/bin/env node
/*
 * decisions.mjs: the questions the owner must answer, with the evidence for
 * each, as JSON.
 *
 *   node decisions.mjs [package-dir]
 *
 * Runs survey.mjs and joins its facts to assets/decisions.json. For each
 * question it reports whether it applies to this package, the evidence the
 * survey found, and a suggestion. A suggestion is not an answer: the owner
 * answers. It exists so the question arrives with its facts, and so an
 * unattended run has something to take and report as unconfirmed.
 */

import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'

const here = new URL('.', import.meta.url)
const dir = process.argv[2] ?? '.'
const survey = JSON.parse(
  execFileSync(process.execPath, [new URL('survey.mjs', here).pathname, dir], { encoding: 'utf8' })
)
const { questions } = JSON.parse(readFileSync(new URL('../assets/decisions.json', here), 'utf8'))

const flags = new Set(survey.flags.map(flag => flag.id))
const callbackFiles = survey.idioms.error_first_callback.files.filter(
  entry => !/(?:^|\/)(?:tests?|examples?)\//.test(entry.file)
)
const lockfile = survey.lockfiles[0]
const manager =
  survey.package.package_manager?.split('@')[0] ??
  (lockfile?.startsWith('pnpm') ? 'pnpm' : lockfile?.startsWith('yarn') ? 'yarn' : lockfile ? 'npm' : null)
const dev = Object.keys(survey.dependencies.dev)
const linter =
  ['@biomejs/biome', 'oxlint', 'eslint', 'standard'].find(name => dev.includes(name)) ?? null
const deadRunner = flags.has('unmaintained-test-runner') || flags.has('no-tests')

// Each entry: does the question apply, what the survey saw, and a suggestion.
const facts = {
  callbacks: {
    applies: callbackFiles.length > 0,
    evidence: { files: callbackFiles },
    suggested: null,
    why: 'No suggestion. Loud or quiet, and whether to carry the old form, is the owner\'s call. Dependents and downloads inform it; look them up.'
  },
  module_system: {
    applies: true,
    evidence: { now: survey.module_system, type: survey.package.type, uses_module_parent: flags.has('uses-module-parent') },
    suggested: 'esm',
    why: 'One build, and current Node can require() it.'
  },
  engines: {
    applies: true,
    evidence: { now: survey.package.engines?.node ?? null },
    suggested: 'active-lts',
    why: 'Look up the release schedule before asking, and offer only supported lines by number.'
  },
  types: {
    applies: true,
    evidence: {
      declaration_files: survey.types.declaration_files,
      sibling_declarations: survey.types.sibling_declarations.length,
      has_tsconfig: survey.types.tsconfigs.length > 0
    },
    suggested: survey.types.sibling_declarations.length ? 'handwritten' : 'jsdoc-generated',
    why: survey.types.sibling_declarations.length
      ? 'Hand-written declarations already exist. Keeping them means adding the conformance gates.'
      : 'One source of truth.'
  },
  package_manager: {
    applies: true,
    evidence: { package_manager: survey.package.package_manager, lockfiles: survey.lockfiles },
    suggested: manager ?? 'pnpm',
    why: manager ? 'Already in use here.' : 'Nothing in use here; pnpm is the default.'
  },
  lint: {
    applies: true,
    evidence: { now: linter },
    suggested: linter ? 'existing' : 'biome',
    why: linter ? `${linter} is already configured.` : 'Nothing configured.'
  },
  test_runner: {
    applies: true,
    evidence: { now: survey.tests.runners, script: survey.tests.script },
    suggested: deadRunner || !survey.tests.runners.length ? 'node-test' : 'existing',
    why: deadRunner ? 'The current runner is unmaintained or absent.' : 'The current runner is maintained.'
  },
  runtimes: {
    applies: true,
    evidence: { bin: Boolean(survey.package.bin), process_next_tick: survey.idioms.process_next_tick.count },
    suggested: 'node',
    why: 'Nothing in the repository says otherwise.'
  },
  dependencies: {
    applies: survey.dependencies.superseded.length > 0,
    evidence: { superseded: survey.dependencies.superseded },
    suggested: 'replace',
    why: 'Each has a built-in replacement at a current floor.'
  },
  known_defects: {
    applies: null,
    evidence: {},
    suggested: null,
    why: 'Known only after Step 1. Ask once the baseline has pinned the defects, and name each one.'
  },
  scope: { applies: true, evidence: {}, suggested: 'parity', why: 'The smallest revival that meets the goal.' },
  deep_imports: {
    applies: !survey.package.has_exports_map,
    evidence: { main: survey.package.main, source_files: survey.source.files },
    suggested: 'closed',
    why: 'Search for deep imports among dependents before asking, and name the paths found.'
  },
  release: { applies: true, evidence: { tags: survey.git.tags, last_tag: survey.git.last_tag }, suggested: 'prepare-only', why: 'The release is the owner\'s to make.' },
  old_major: { applies: true, evidence: { version: survey.package.version }, suggested: 'frozen', why: 'No sign of a maintenance branch.' }
}

const out = {
  package: `${survey.package.name}@${survey.package.version}`,
  root: survey.root,
  questions: questions.map(question => ({ ...question, ...facts[question.id], answer: null }))
}

console.log(JSON.stringify(out, null, 2))
