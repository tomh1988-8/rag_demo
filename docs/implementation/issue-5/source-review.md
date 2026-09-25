# Source inspection before parser completion

Inspected public inputs on 25 September 2026. The frozen batch retains complete
HTTP response payloads as UTF-8 inside a lossless gzip JSON file. Initial discovery
used ordinary `httpx` requests with the named project User-Agent, not a model.

- Sharon Watts: Wikipedia revision 1372798905, item Q7490258. The `Storylines`
  section has three dated subsections and 30 paragraphs. Its first paragraph
  retains pre-1990 history, adoption by Den and Angie, and performer names in
  parentheses. Infobox aliases are Sharon Mitchell, Rickman and Beale. Letitia
  Dean is a performer, not an alias. Den is supporting context, not a core-roster
  addition. The text is source-supported; its adoption wording is not a
  biological-parent claim.
- Ben Mitchell (EastEnders): revision 1369268749, item Q2766568. Three story
  subsections contain 19 paragraphs. Six credited performers represent recasts
  of the same character. The first story paragraph gives March 1996; neither
  article capture time nor programme broadcast metadata establishes its day.
- Kat Slater: revision 1375940007, item Q3955054. A `Storylines` subsection named
  `Kat & Alfie: Redwater and EastEnders: The Podcast` is out of scope. Other
  main-series paragraphs mention Redwater; a keyword ban would incorrectly lose
  these. Production discussion and the lead mix narrative and other material;
  keep them for review, outside retrieval. The policy is tied to this revision.
  Direct HTML reinspection of the subsection shows five paragraphs: four about
  Redwater and one about the podcast. An initial test expectation of two counted
  only the paragraphs containing discovery keywords; corrected against the raw
  heading-to-heading HTML before acceptance, without changing the parser policy.
- Den Watts: retain the full captured article and its Q5256484 link as supporting
  identity evidence. No Den narrative section is admitted in this small batch.
  The independent spec review caught omitted infobox aliases: Dennis Alan Watts
  and Dirty Den. Both now resolve to Den in the frozen catalogue and capture plan;
  a public identity regression failed before the correction. Raw captures and
  ordered paragraph labels were unchanged; only the batch fingerprint changed.
- Wikidata: the three core-item JSON responses contain `entities`, `id`,
  `lastrevid`, English labels and `enwiki` sitelinks. These link identities only.
  English aliases are absent on the sampled Sharon/Ben records; do not manufacture
  missing aliases or override the separately reviewed Wikipedia names.
- TVmaze: EastEnders is show 793. `/shows/793/episodebynumber?season=1&number=1`
  returned HTTP 404 during discovery. The successful
  `/shows/793/episodesbydate?date=1985-02-19` returned episode 116520, season 1985,
  number 1. Its date is a broadcast date. The empty summary is missing content,
  not a narrative assertion. Retain this failed attempt in the compatibility
  record; do not substitute invented episode data.

The scope policy admits only reviewed narrative sections, retains excluded and
unreviewed paragraphs with their order and enclosing heading IDs, and does not
perform semantic claim extraction. Ordinary HTML/JSON parsing suffices. Script,
navigation, infobox/table and reference markup stay in the original capture;
the paragraph projection is explicitly narrower than the full article. Inline
reference markers are removed and whitespace is normalised; source locators
refer to that retained paragraph projection, never to HTML byte offsets.

All examples are exposed development inputs. Reviews check retained source
content, not independent truth; no held-out, human-calibrated or broad-canon
quality claim follows from these fixtures.
