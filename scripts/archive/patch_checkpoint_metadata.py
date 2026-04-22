with open("textgraphx/checkpoint.py", "r") as f:
    text = f.read()

old = """        phase_markers: List[str] = None,
        properties_snapshot: Dict[str, Any] = None
    ) -> Path:"""

new = """        phase_markers: List[str] = None,
        properties_snapshot: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None
    ) -> Path:"""

text = text.replace(old, new)

old_payload = """            "phase_markers": phase_markers or [],
            "properties_snapshot": properties_snapshot or {},
        }"""

new_payload = """            "phase_markers": phase_markers or [],
            "properties_snapshot": properties_snapshot or {},
            "metadata": metadata or {},
        }"""

text = text.replace(old_payload, new_payload)

with open("textgraphx/checkpoint.py", "w") as f:
    f.write(text)
print("done")
