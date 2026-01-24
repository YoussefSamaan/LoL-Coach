from __future__ import annotations

from app.config.settings import settings
from app.ingest.pipeline import PipelineStep, PipelineContext
from app.ingest.clients.crawler import RiotCrawler
from app.utils.logger import get_logger
from app.utils.time import get_date_str

logger = get_logger(__name__)


class ScanHistoryStep(PipelineStep):
    """
    Step 1b: Identify which matches need to be downloaded.

    This step acts as a "Deduplication Filter":
    1. It fetches recent Match IDs for each player found in the Ladder Step.
    2. It checks our local 'Manifests' (text files containing list of already-processed Match IDs).
       - Manifest Path: data/manifests/{Region}/{Tier}/{Division}/{Date}.txt
    3. If a Match ID is NEW (not in manifests):
       - It is added to the download queue (`context.state["match_ids"]`).
       - It is appended to today's manifest file so we don't process it again in the future.
    """

    name = "Scan Histories"

    def run(self, context: PipelineContext) -> None:
        players = context.state.get("players", [])
        if not players:
            return

        crawler = RiotCrawler()
        region = settings.ingest.defaults.get("region", "NA")
        count = settings.ingest.defaults.get("matches_per_player", 2)
        min_time = context.state.get("min_match_time", 0)

        # Manifest Base
        manifest_root = settings.data_root / settings.ingest.paths.manifest_dir
        manifest_root.mkdir(parents=True, exist_ok=True)

        matches_to_download = set()
        new_manifest_entries: dict[
            str, set[str]
        ] = {}  # Key: "Region/Tier/Div", Value: set(match_ids)
        today_str = get_date_str()

        for player in players:
            puuid = player["puuid"]
            tier = player["tier"]
            division = player["division"]

            try:
                # 1. Fetch recent match IDs from Riot API
                recent_ids = crawler.scan_match_history(region, [puuid], count, start_time=min_time)
            except Exception as e:
                logger.warning(f"Failed to scan history for {puuid}: {e}")
                continue

            # Standardized Path: manifests/REGION/TIER/DIV/Date.txt
            rank_params = f"{region}/{tier}/{division}"
            rank_manifest_dir = manifest_root / region / tier / division
            rank_manifest_dir.mkdir(parents=True, exist_ok=True)

            # 2. Caching: Load all existing Match IDs from disk for this rank bucket
            # We cache this in `context.state` to avoid re-reading files for every player in the same rank.
            if f"manifest_{rank_params}" not in context.state:
                existing_ids = set()
                # Read all date files in this bucket
                for m_file in rank_manifest_dir.glob("*.txt"):
                    try:
                        content = m_file.read_text().splitlines()
                        existing_ids.update(content)
                    except Exception as e:
                        logger.warning(f"Failed to read manifest {m_file}: {e}")
                context.state[f"manifest_{rank_params}"] = existing_ids

            known_ids = context.state[f"manifest_{rank_params}"]

            # 3. Filter: Keep only NEW matches
            for match_id in recent_ids:
                if match_id not in known_ids and match_id not in matches_to_download:
                    # Add to queue for DownloadContentStep
                    matches_to_download.add(match_id)
                    # Mark as known locally so duplicates in this same run are skipped
                    known_ids.add(match_id)

                    if rank_params not in new_manifest_entries:
                        new_manifest_entries[rank_params] = set()
                    new_manifest_entries[rank_params].add(match_id)

                    if "match_rank_map" not in context.state:
                        context.state["match_rank_map"] = {}
                    # Store Region in context too for DownloadStep
                    context.state["match_rank_map"][match_id] = {
                        "tier": tier,
                        "division": division,
                        "region": region,
                    }

        # 4. Persistence: Append new matches to Manifest files
        # We append to `data/manifests/.../TODAY.txt` to record that we have processed these IDs.
        for rank_key, new_ids in new_manifest_entries.items():
            region, tier, division = rank_key.split("/")
            man_file = manifest_root / region / tier / division / f"{today_str}.txt"
            man_file.parent.mkdir(parents=True, exist_ok=True)
            with open(man_file, "a") as f:
                for match_id in new_ids:
                    f.write(f"{match_id}\n")

        context.state["match_ids"] = matches_to_download
        logger.info(f"Queued {len(matches_to_download)} new matches for download.")
