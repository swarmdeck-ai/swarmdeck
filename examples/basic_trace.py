"""Simplest possible SwarmDeck usage — one decorator, automatic tracing."""

from swarmdeck import trace, observatory


@trace(agent="researcher", team="content")
def research(topic: str) -> str:
    # Your existing agent code — unchanged
    return f"Research results for: {topic}"


@trace(agent="writer", team="content")
def write_article(research_data: str) -> str:
    return f"Article based on: {research_data}"


if __name__ == "__main__":
    data = research("AI agent observability")
    article = write_article(data)
    print(article)

    # Flush pending traces
    observatory.flush()

    # Query what was recorded
    spans = observatory.query(agent="researcher")
    for span in spans:
        print(f"  {span.agent}: {span.operation} ({span.duration_ms:.1f}ms)")

    print(f"\nTraces stored at: {observatory.database_path}")
