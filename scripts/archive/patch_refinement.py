with open("textgraphx/RefinementPhase.py", "r") as f:
    content = f.read()

old_block = """        logger.info(
            "tag_discourse_relevant_entities: tagged %d NamedEntity + %d nominal mentions as :DiscourseEntity",
            tagged_ne,
            tagged_nom,
        )
        return ""
"""

new_block = """
        fa_query = \"\"\"
            MATCH (fa:FrameArgument)
            MATCH (fa)-[:EVENT_PARTICIPANT|PARTICIPANT|PARTICIPATES_IN|IN_RELATION|HAS_STATE|IS_A*1..2]-(ev)
            SET fa:DiscourseEntity
            RETURN count(DISTINCT fa) AS tagged
        \"\"\"
        data_fa = self.graph.run(fa_query).data()
        tagged_fa = data_fa[0].get("tagged", 0) if data_fa else 0

        logger.info(
            "tag_discourse_relevant_entities: tagged %d NamedEntity + %d nominal mentions + %d FrameArgument as :DiscourseEntity",
            tagged_ne,
            tagged_nom,
            tagged_fa,
        )
        return ""
"""
content = content.replace(old_block, new_block)
with open("textgraphx/RefinementPhase.py", "w") as f:
    f.write(content)
