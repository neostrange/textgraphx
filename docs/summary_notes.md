Findings from MEANTIME pdf:
1. "The extent of this portion of text is defined to be the entire nominal phrase used to refer to an entity, thus including modifiers, prepositional phrases, and dependent clauses [...] the maximal extent." -> TextGraphX's minimal chunking is breaking MEANTIME.
2. Sections 6 (TIMEX3) and 7 (VALUE) are completely separate tags from ENTITY MENTION. numerical expressions (PERCENT, MONEY, QUANTITY) like '5.5 percent' and temporal expressions like 'Tuesday' or 'March' are NOT entities in MEANTIME.
3. PTV is strictly for partitives with TWO elements ("part" and "whole", e.g., "some of the lawyers"). A naked "two percent" should never be an entity, just a VALUE. 
