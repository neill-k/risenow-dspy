# Modular Refactor & GEPA Caching Plan

## 1. Core Runtime Enhancements
- Create  package with helpers for environment loading, LM configuration, tool creation, and GEPA defaults.
- Add program persistence utilities (, , cache-path resolver) in  for reuse by all services.

## 2. Service Modules
- Move vendor logic to  with signature .
  - When , skip optimization, instantiate the base DSPy program, and do **not** touch cache files.
  - When  and cache exists, load the saved program instead of re-running GEPA; otherwise optimize and save if allowed.
- Mirror the pattern in  (and future modules) so each service can run optimized, cached, or raw.

## 3. Workflow Layer & CLI
- Introduce  package (e.g., , ) that composes services.
- Update  to delegate to workflows and expose flags:
  -  (choose vendor-only, market dossier, etc.).
  -  (force  across services).
  -  (enable caching). Automatically disable cache writes when  is set.
  -  (run GEPA but skip persistence).

## 4. GEPA Caching Behavior
- Define cache file naming per service (e.g., , ). Include metadata (timestamp, DSPy version, model IDs) to detect stale cache.
- Allow workflows to run immediately without optimization via , yet reuse cached programs when available.
- Provide helper  with builders (, ) that accept reflection LM and cache settings.

## 5. Testing Strategy
- Service tests: mock DSPy agents/GEPA to verify each of the three modes (cached, optimized, raw) trigger expected code paths.
- Workflow smoke tests: ensure combined outputs when , when using cache, and when forcing re-optimization.
- Use temporary directories in tests to validate cache save/load and to ensure no cache writes happen when .

## 6. Documentation
- Update  and  with architecture overview (, , ), CLI examples, and GEPA caching instructions.
- Document steps for adding new analytical modules (models → service → workflow → tests → docs).
- Provide quick snippets:
  

## 7. Milestones
1. Scaffold  package, add runtime & persistence helpers.
2. Migrate vendor service; implement GEPA toggle/cache; add service tests.
3. Migrate PESTLE service; update workflows & CLI flags; add workflow tests.
4. Refresh documentation, finalize integration tests, and prep scaffolding for future modules (e.g., Porter’s Five Forces).

## 8. Rollout Notes
- Keep legacy  wrappers delegating to new workflows for backwards compatibility until downstream code migrates.
- Warn and re-optimize when cache metadata mismatches current model configuration.
- Encourage storing cache dir outside repo (e.g., ) for CI/CD reuse.
