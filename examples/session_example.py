"""Session context manager — group related spans into a workflow."""

from swarmdeck import trace, observatory


@trace(agent="researcher")
def research(topic: str) -> str:
    return f"Found 10 sources on: {topic}"


@trace(agent="writer")
def draft(research_data: str) -> str:
    return f"Draft article from: {research_data}"


@trace(agent="editor")
def review(draft: str) -> str:
    return f"Reviewed: {draft}"


if __name__ == "__main__":
    with observatory.session("weekly-report", project="swarmdeck") as session:
        data = research("multi-agent coordination")
        article = draft(data)
        final = review(article)
        print(final)

    observatory.flush()

    # All spans from this session are queryable together
    spans = observatory.query(session_id=session.id)
    print(f"\nSession '{session.name}' recorded {len(spans)} spans:")
    for span in spans:
        print(f"  {span.agent}: {span.operation} ({span.duration_ms:.1f}ms)")
    print(f"Total session time: {session.duration_ms:.1f}ms")
