"""Analyses, grouped by function. Each group owns its facts, its figures and its tables.

Every group exposes run(ctx). It first decides whether it applies to this couple and
records that with facts.module(name, applied, reason), so a same-city couple gets
"timezones: not applied" instead of an error. Order matters where one group reuses
another's results through ctx.shared (sessions -> relationship, timezones -> greetings).

  volume        how much, when, by whom, in which media          6 figures
  rhythm        hours and weekdays on each person's own clock    4 figures
  timezones     the two clocks side by side (long-distance)      2 figures
  sessions      who starts, how long, how fast the replies       4 figures
  language      words, shared words, catchphrases (sensitive)    5 figures
  greetings     good mornings, good nights and their direction   2 figures
  relationship  phases between milestones, recent vs before      2 figures
  calls         call events                                      1 figure
  itinerary     chat volume against where each person was        1 figure
"""
from . import calls, greetings, itinerary, language, relationship, rhythm, sessions, timezones, volume

ANALYSES = [volume, rhythm, timezones, sessions, language, greetings, relationship, calls, itinerary]


def run_all(ctx) -> None:
    for analysis in ANALYSES:
        analysis.run(ctx)
