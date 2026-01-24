from __future__ import annotations

import json
from app.config.settings import settings
from app.ingest.pipeline import PipelineStep, PipelineContext
from app.ingest.domain.persistence import batch_process_raw_matches


class ParseMatchStep(PipelineStep):
    """
    Step 2: Parse Raw JSONs into 'clean match' files.

    Input:
      - Raw JSON: raw/NA/CHALLENGER/I/2024-01-01/MATCH_ID.json

    Output:
      - Parsed JSON: parsed/NA/CHALLENGER/I/2024-01-01.json
        (Contains list of flattened match objects)
    """

    name = "Parse Matches"

    def run(self, context: PipelineContext) -> None:
        raw_dir = context.state.get("raw_dir")
        if not raw_dir:
            return

        output_format = settings.ingest.paths.processed_file_type
        parsed_output_dir = settings.data_root / settings.ingest.paths.parsed_dir
        parsed_output_dir.mkdir(parents=True, exist_ok=True)

        champion_map_path = context.state.get("champion_map_path", settings.champion_map_path)
        match_rank_map = context.state.get("match_rank_map", {})
        min_time = context.state.get("min_match_time", 0)

        # Load ID Map
        id_map = {}
        if champion_map_path.exists():
            try:
                id_map = json.loads(champion_map_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Use functional domain logic
        # Use functional domain logic
        batch_process_raw_matches(
            input_dir=raw_dir,
            output_root=parsed_output_dir,
            id_map=id_map,
            rank_map=match_rank_map,
            min_time=min_time,
            output_format=output_format,
        )

        context.state["parsed_dir"] = parsed_output_dir
