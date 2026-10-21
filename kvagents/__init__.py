"""KooraVision agents: turn match events (and tracking) into fact-checked stories for fans and broadcasters.

Five agents run as a Microsoft Agent Framework workflow:
Interpret -> Explain -> Narrate -> Verify -> (Broadcast desk, Fan desk) -> Publish.
Every handoff is written to a trace. The Interpret and Explain agents never read ground_truth.json.
"""
__version__ = "0.1.0"
