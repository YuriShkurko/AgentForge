"""
Generator test fixtures — minimal valid domain packs for each archetype.
Used by generator unit tests to validate pack parsing and module selection
without depending on real domain-pack.yaml files.
"""

FIXTURE_INGESTION_SCORING_PIPELINE = {
    "name": "test-pipeline-pack",
    "display_name": "Test Pipeline Pack",
    "version": "0.1.0",
    "app_archetype": "ingestion_scoring_pipeline",
    "required_shell_modules": [
        "pipeline",
        "provider_adapter",
        "scoring_explanation",
        "operations_ui",
        "persistence",
        "test",
    ],
    "optional_shell_modules": ["notification_action", "triage_ui"],
    "domain": {
        "domain_name": "Test Pipeline",
        "app_type": "ingestion_scoring_pipeline",
        "target_users": ["developer"],
        "product_purpose": "Test fixture for generator unit tests.",
        "main_user_goals": ["ingest_fixture_records", "score_records"],
    },
    "capabilities": [
        {
            "name": "ingest_records",
            "purpose": "Load fixture records and normalize them.",
            "input_summary": "POST /ingest",
            "output_shape": {"fields": ["raw_records_inserted", "normalized_inserted", "run_id"]},
            "mutates_state": True,
            "data_mode": "fixture_provider",
            "deterministic_test_safe": True,
            "implementation_status": "planned",
        },
        {
            "name": "score_records",
            "purpose": "Score normalized records deterministically.",
            "input_summary": "POST /score",
            "output_shape": {"fields": ["scores_written"]},
            "mutates_state": True,
            "data_mode": "deterministic_heuristics",
            "deterministic_test_safe": True,
            "implementation_status": "planned",
        },
    ],
    "providers": {
        "record_sources": [
            {
                "name": "fixture",
                "class": "FixtureRecordProvider",
                "interface": "RecordProvider",
                "source": "deterministic in-code fixture list",
                "current_status": "planned",
            }
        ]
    },
    "adapters": [
        {
            "name": "normalized_dto_from_raw",
            "purpose": "Convert raw provider record to NormalizedRecordDTO.",
            "normalized_shape": ["external_id", "source", "title", "category", "value", "ingested_at"],
        }
    ],
    "run_history": {
        "enabled": True,
        "table_name": "provider_runs",
        "tracked_fields": ["provider_name", "started_at", "finished_at", "status", "stats", "error"],
        "frontend_surface": "run_history_table",
    },
    "seed_data": {
        "fixture_provider_records": "backend/app/providers/fixture/records.py",
    },
    "tests": {
        "expectations": {
            "no_live_provider_in_tests": True,
            "no_live_llm_in_tests": True,
            "deterministic_fixture_data": True,
        },
        "commands": {"backend": "pytest"},
    },
}

FIXTURE_AGENT_DASHBOARD_APP = {
    "name": "test-agent-pack",
    "display_name": "Test Agent Pack",
    "version": "0.1.0",
    "app_archetype": "agent_dashboard_app",
    "required_shell_modules": ["agent", "workspace", "provider_adapter", "test"],
    "optional_shell_modules": [],
    "domain": {
        "domain_name": "Test Agent",
        "app_type": "agentic_dashboard",
        "target_users": ["developer"],
        "product_purpose": "Test fixture for generator unit tests.",
        "main_user_goals": ["ask_question", "pin_widget"],
    },
    "agent_shell_contract": {
        "chat": True,
        "streaming_sse": True,
        "tool_calling": True,
        "persistent_conversations": True,
        "persistent_workspace_widgets": True,
        "guardrails": True,
        "scripted_llm_testing": True,
    },
    "tools": [
        {
            "name": "get_summary",
            "purpose": "Return a summary of the domain data.",
            "input_summary": "No arguments.",
            "output_shape": {"fields": ["summary", "score", "drivers"]},
            "allowed_widget_types": ["summary_card"],
            "mutates_state": False,
            "data_mode": "real_or_mock",
            "deterministic_test_safe": True,
            "implementation_status": "planned",
        }
    ],
    "tool_widget_compatibility": {
        "get_summary": ["summary_card"],
    },
    "widgets": [
        {
            "widget_type": "summary_card",
            "renderer": "SummaryCard",
            "compatible_source_tools": ["get_summary"],
            "section": "overview",
            "expected_data_shape": "summary, score, drivers.",
            "empty_state": "No summary data available.",
            "implementation_status": "planned",
        }
    ],
    "providers": {
        "data_sources": [
            {
                "name": "fixture",
                "class": "FixtureProvider",
                "interface": "DataProvider",
                "source": "deterministic in-code fixture",
                "current_status": "planned",
            }
        ]
    },
    "adapters": [
        {
            "name": "fixture_adapter",
            "purpose": "Normalize fixture provider output.",
            "normalized_shape": ["id", "title", "value"],
        }
    ],
    "seed_data": {"fixture_data": "backend/fixtures/demo.py"},
    "tests": {
        "expectations": {
            "no_live_llm_in_tests": True,
            "deterministic_fixture_data": True,
        },
        "commands": {"backend": "pytest"},
    },
}

FIXTURE_NOTIFICATION_TRIAGE_APP = {
    "name": "test-triage-pack",
    "display_name": "Test Triage Pack",
    "version": "0.1.0",
    "app_archetype": "notification_triage_app",
    "required_shell_modules": [
        "notification_action",
        "triage_ui",
        "persistence",
        "scoring_explanation",
    ],
    "optional_shell_modules": ["pipeline", "agent_runtime"],
    "domain": {
        "domain_name": "Test Triage",
        "app_type": "notification_triage_app",
        "target_users": ["developer"],
        "product_purpose": "Test fixture for generator unit tests.",
        "main_user_goals": ["triage_recommendations", "record_decisions"],
    },
    "capabilities": [
        {
            "name": "list_recommendations",
            "purpose": "Return scored recommendations pending triage.",
            "input_summary": "GET /recommendations",
            "output_shape": {"fields": ["id", "title", "score", "recommendation"]},
            "mutates_state": False,
            "data_mode": "database",
            "deterministic_test_safe": True,
            "implementation_status": "planned",
        }
    ],
    "notification_actions": [
        {
            "name": "triage_decision",
            "trigger": "user swipes or clicks accept/skip/save",
            "delivery_channel": "none_stub",
            "decision_states": ["pending", "accepted", "skipped", "saved"],
            "dedupe_key": "record_id + action_type",
            "persistence_table": "triage_decisions",
        }
    ],
    "providers": {
        "record_sources": [
            {
                "name": "fixture",
                "class": "FixtureRecommendationProvider",
                "interface": "RecommendationProvider",
                "source": "deterministic in-code fixture",
                "current_status": "planned",
            }
        ]
    },
    "adapters": [],
    "seed_data": {"fixture_recommendations": "backend/fixtures/recommendations.py"},
    "tests": {
        "expectations": {
            "no_live_provider_in_tests": True,
            "deterministic_fixture_data": True,
        },
        "commands": {"backend": "pytest"},
    },
}

# Archetype -> required module set mapping (source of truth for generator tests)
ARCHETYPE_REQUIRED_MODULES = {
    "agent_dashboard_app": {"agent", "workspace", "provider_adapter", "test"},
    "ingestion_scoring_pipeline": {
        "pipeline",
        "provider_adapter",
        "scoring_explanation",
        "operations_ui",
        "persistence",
        "test",
    },
    "notification_triage_app": {
        "notification_action",
        "triage_ui",
        "persistence",
        "scoring_explanation",
    },
    "hybrid_agent_pipeline": {"pipeline", "provider_adapter", "operations_ui"},
}
