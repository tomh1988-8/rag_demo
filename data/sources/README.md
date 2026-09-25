# Reviewed real-source batch

`real-sources-v1.json.gz` is lossless gzip-compressed UTF-8 JSON containing eight
complete captured HTTP payloads, capture times/hashes, four reviewed character
identities and revision-specific Wikipedia scope policies. The adjacent plan is
the reproducible input to `ask-phil capture-sources`; a new capture is a separate
artifact and may require new scope review if a Wikipedia revision changes.

The small sample covers Sharon Watts, Ben Mitchell and Kat Slater, with Den Watts
as a supporting character. It admits 79 story paragraphs from the three core
profiles and holds Den's narrative for review. This is not the 20-profile corpus.
Aliases and performers were checked against the captured infoboxes. Supporting
links identify character mentions, not biological or other graph relationships.

| Source | Role and reuse | Capture/access/freshness |
| --- | --- | --- |
| English Wikipedia character pages | Narrative evidence and reviewed identity fields. Wikipedia contributors; [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Preserve attribution, revision links and license; adapted text uses the same license. | Public HTML, explicit project User-Agent, serial bounded requests. See [Wikimedia terms](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use) and [User-Agent policy](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy). No login, protected-source access or images are needed. |
| Wikidata Q7490258, Q2766568, Q3955054 | Identity linkage only; full structured item records retained under [CC0](https://www.wikidata.org/wiki/Wikidata:Data_access). Credit Wikidata contributors. | Public EntityData JSON with `lastrevid`. Missing aliases/sitelinks remain missing. Identifier agreement is not independent plot corroboration. |
| [TVmaze EastEnders, show 793](https://www.tvmaze.com/shows/793/eastenders) | Episode 116520 broadcast metadata only. Credit TVmaze; its [API terms](https://www.tvmaze.com/api) specify CC BY-SA 4.0. | Public JSON; API output can be cached for an hour. Published rate guidance is at least 20 requests/10 seconds; this batch makes one serial TVmaze request. A 429 stops capture explicitly; rerun later rather than retrying without a bound. |

Policy/access references were checked on 25 September 2026. Recheck them before
changing sources or access patterns. The importer makes at most 20 requests per
batch, reads at most 5 MB per response/20 MB total, rejects redirects and HTTP
failures, and uses a 30-second network-operation timeout. It has no automatic
retries. That timeout is not a hard end-to-end deadline. Frozen batch files are
limited to 25 MB after decompression. Capture is a maintainer operation; answering
and source inspection never fetch the web.

Capture dates mean when payloads were checked, not demonstrated story coverage.
Wikipedia revision IDs and Wikidata `lastrevid` identify source revisions;
TVmaze has no corresponding immutable episode revision, so its retained payload
hash identifies this capture. Its `airdate`/`airstamp` stay broadcast fields.
None is converted into a story event date. Manual refresh/recovery is #6; weekly
refresh belongs to deployed operation and is not enabled here.

The raw payloads are unchanged. The paragraph projection removes inline citation
markers and normalises whitespace. It ignores navigation, tables, figures and
non-paragraph markup, which remain inspectable in the raw capture. Offsets are
zero-based, end-exclusive Unicode character positions in the complete retained
paragraph projection, including excluded/unreviewed paragraphs. Paragraph ordinal,
heading path and heading ID preserve ordering and enclosing sections. Retrieval
passages split admitted paragraphs at word boundaries into at most 1,200 UTF-8
bytes; their exact spans reconstruct the admitted paragraph without losing text.

Kat's dedicated Redwater/podcast subsection has five excluded paragraphs. A
main-series mention of Redwater remains eligible. Other mixed lead/development/
production material stays `review_required`, outside retrieval: these 198
paragraphs are neither declared irrelevant nor silently discarded. Scope rules
are a small reviewed policy for each exact revision, not a general canon classifier.
Later sentence-window expansion must use the retained scope decisions; #24 owns
that behavior. Semantic extraction and graph admission are also later work.

[Source inspection notes](../../docs/implementation/issue-5/source-review.md) and
[ordered paragraph labels](../references/source-ingestion-v1.json) record the
reviewed expectations. All cases are exposed development data. Source-supported
does not mean independently cross-checked or human-calibrated.
