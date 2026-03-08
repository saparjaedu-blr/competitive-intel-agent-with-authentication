from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.nodes.web_scraper import web_scraper_node
from agent.nodes.youtube_scraper import youtube_scraper_node
from agent.nodes.gdoc_reader import gdoc_reader_node
from agent.nodes.synthesizer import synthesizer_node
from agent.nodes.diff_engine import diff_engine_node
from agent.nodes.report_writer import report_writer_node


# Ordered node names — used by UI to compute exact progress %
PIPELINE_STEPS = [
    "web_scraper",
    "youtube_scraper",
    "gdoc_reader",
    "synthesizer",
    "diff_engine",
    "report_writer",
]

# Human-readable labels for each node
STEP_LABELS = {
    "web_scraper":     ("🌐", "Scraping websites, blogs, docs & changelogs"),
    "youtube_scraper": ("🎬", "Fetching YouTube transcripts"),
    "gdoc_reader":     ("📄", "Reading scrapbook notes and images"),
    "synthesizer":     ("🧠", "GPT-4o synthesizing intelligence per vendor"),
    "diff_engine":     ("🔄", "Computing delta vs previous run"),
    "report_writer":   ("📝", "Compiling and archiving final report"),
}


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("web_scraper",    web_scraper_node)
    graph.add_node("youtube_scraper", youtube_scraper_node)
    graph.add_node("gdoc_reader",    gdoc_reader_node)
    graph.add_node("synthesizer",    synthesizer_node)
    graph.add_node("diff_engine",    diff_engine_node)
    graph.add_node("report_writer",  report_writer_node)

    graph.set_entry_point("web_scraper")
    graph.add_edge("web_scraper",     "youtube_scraper")
    graph.add_edge("youtube_scraper", "gdoc_reader")
    graph.add_edge("gdoc_reader",     "synthesizer")
    graph.add_edge("synthesizer",     "diff_engine")
    graph.add_edge("diff_engine",     "report_writer")
    graph.add_edge("report_writer",   END)

    return graph.compile()


def run_agent(vendors: list[str], research_query: str,
              save_to_drive: bool = False, user_id: int = None) -> AgentState:
    """Invoke the full pipeline (blocking). Returns final state."""
    app = build_graph()
    initial_state = _make_initial_state(vendors, research_query, save_to_drive, user_id)
    return app.invoke(initial_state)


def stream_agent(vendors: list[str], research_query: str,
                 save_to_drive: bool = False, user_id: int = None):
    """Stream the pipeline node-by-node."""
    app = build_graph()
    initial_state = _make_initial_state(vendors, research_query, save_to_drive, user_id)

    final_state = initial_state
    for event in app.stream(initial_state, stream_mode="updates"):
        for node_name, node_output in event.items():
            final_state = {**final_state, **node_output}
            yield node_name, final_state

    yield "__end__", final_state


def _make_initial_state(vendors, research_query, save_to_drive, user_id=None) -> AgentState:
    return {
        "vendors":        vendors,
        "research_query": research_query,
        "save_to_drive":  save_to_drive,
        "user_id":        user_id,
        "raw_data":       [],
        "syntheses":      [],
        "diffs":          [],
        "final_report_markdown": "",
        "gdrive_link":           "",
        "analysis_duration_seconds": 0.0,
        "drive_duration_seconds":    0.0,
        "errors":       [],
        "current_step": "starting",
    }
