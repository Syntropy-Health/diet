# TODOs for SSS Pipeline Debugging and Implementation

## Immediate Debugging Tasks
- [ ] Fix import error in `demo/symptom_diet_solver.py` (should use relative import or run from correct entrypoint)
- [ ] Ensure `symptom_diet_solver` is treated as a package (has `__init__.py`)
- [ ] Confirm all imports resolve for `models.symptom_diet_solver.schema` and `utils.logger`
- [ ] Validate that the pipeline can be run end-to-end with synthetic data

## Technical Implementation Checklist (from CODING_INSTRUCTIONS.md)
- [ ] Modularize components by functionality (engine, pipeline, schema, utils, etc.)
- [ ] All parameters and prompts defined in YAML (Hydra config)
- [ ] No hardcoded values for LLM or config in code
- [ ] Use Pydantic models for all LLM output and schema validation
- [ ] Use LangChain's PydanticParser for LLM output parsing
- [ ] Centralized logging via `utils/logger.py`
- [ ] Load environment variables from `.env.template` using dotenv
- [ ] Update VS Code `launch.json` for debugging
- [ ] Use `uv` for package management
- [ ] Keep documentation up to date in README.md
- [ ] Maintain clean, hierarchical project structure
- [ ] Use comments for TODOs and clarifications
- [ ] Keep main function and CLI entrypoint separate
- [ ] Use `tqdm` for progress tracking in long-running tasks

## Testing & Validation
- [ ] Implement lean tests with dummy data for all modules
- [ ] Validate pipeline with synthetic data (`data/synthetic_raw_entries.json`)
- [ ] Ensure robust error handling and logging for all pipeline steps

## Observability & Monitoring
- [ ] Integrate LangSmith for LLM observability (if available)
- [ ] Log all key pipeline steps and errors

## Housekeeping
- [ ] Remove outdated or unused code
- [ ] Keep root directory clean (only main entrypoints and config)
- [ ] Use clear, functional names for all modules

---
Add to this list as new issues or improvements are discovered during debugging and development.
