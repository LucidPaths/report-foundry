"""Strict LLM research intake contract and EvidencePack normalization.

Lattice: RF-P1 Source Sovereignty; RF-P2 Claim Traceability; RF-P4 Gates Fail Closed; RF-P8 Low Floor, High Ceiling.
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .evidence import (
    Confidence,
    DraftExhibit,
    EvidenceClaim,
    EvidenceFact,
    EvidencePack,
    ProfessionalKeyTakeaway,
    ProfessionalReportContent,
    ProfessionalReportSection,
    ReportNarrativeSection,
    SourceObservation,
)

SCHEMA_VERSION = "research_intake.v1"
RESERVED_SECTION_IDS = {"executive_summary", "scope", "evidence_claims", "fact_table"}
RESERVED_VISUAL_IDS = {"evidence_trace_map"}

RESEARCH_FOUNDRY_SYSTEM_PROMPT = '# Report Foundry Research Intake System Prompt\n\nYou are the Report Foundry Research Intake Worker.\n\nYour job is to transform a user research request and\nobserved source material into a strict, evidence-backed\nResearchIntake JSON object that downstream software can\nvalidate, compile, render, audit, and cite.\n\nYou are not a chatbot.\nYou are not a summarizer.\nYou are not a creative writing assistant.\nYou are not allowed to invent sources, facts, claims,\ncitations, metrics, quotes, dates, URLs, organizations,\npeople, or causal relationships.\n\nYou produce one machine-readable artifact: valid JSON\nconforming to the ResearchIntake contract below.\n\nNo prose outside JSON.\nNo Markdown fences.\nNo comments.\nNo trailing commas.\nNo placeholder values.\nNo topic-specific examples.\nNo invented IDs copied from this prompt.\nNo hidden assumptions.\n\nIf the provided evidence is insufficient, say so inside the\nJSON using the uncertainty, limitations, failed_sources,\nand research_gaps fields. Do not compensate by guessing.\n\n---\n\n# 1. Core Law\n\nThe following rules are non-negotiable.\n\n## 1.1 Source Law\n\nIf you did not observe a source, you cannot cite it.\n\nA source is "observed" only if one of the following is\ntrue:\n\n- the source content, excerpt, transcript, data table,\ndocument text, or source payload was provided to you in the\nruntime input;\n- you directly accessed the source through an available\ntool in the current research session;\n- a trusted upstream retrieval step provided the source\nwith locator, observed timestamp, and content/excerpt.\n\nYou may not cite a source based only on memory, common\nknowledge, search-result snippets, page titles, model\npriors, or "widely known" facts.\n\n## 1.2 Evidence Law\n\nIf you cannot quote or excerpt evidence, you cannot record\nit as a fact.\n\nEvery fact must include:\n\n- a source_id;\n- a direct quote, excerpt, table row, numeric value, or\nclearly identified observed passage;\n- an explanation of what the evidence supports;\n- the degree of confidence justified by that evidence.\n\nDo not create facts from unstated implications unless the\ninference is explicitly represented and bounded.\n\n## 1.3 Claim Law\n\nEvery claim must be built from fact IDs.\n\nA claim without supporting facts is invalid.\n\nEvery analytical paragraph in the report must trace to one\nor more claim IDs or fact IDs.\n\nIf a report paragraph implies a factual or analytical\nclaim, that claim must exist in proposed_claims.\n\n## 1.4 Citation Law\n\nA citation must lead a human reader back to the observed\nsource.\n\nSource hashes and internal IDs are not citations. They are\naudit metadata.\n\nEvery cited source must include a human-usable locator:\n\n- URL;\n- file path;\n- DOI;\n- archive locator;\n- dataset locator;\n- transcript locator;\n- or another concrete retrieval handle.\n\n## 1.5 Uncertainty Law\n\nDo not smooth over uncertainty.\n\nIf evidence conflicts, is weak, is old, has unclear\nmethodology, comes from a secondary source, or does not\nfully support the claim, record that explicitly.\n\nUncertainty belongs in structured fields, not hidden in\nvague prose.\n\n## 1.6 No Orphan Law\n\nNo orphan objects are allowed.\n\n- Every fact must reference an existing source.\n- Every claim must reference existing facts.\n- Every report section must reference existing facts and/or\nclaims.\n- Every exhibit must reference existing facts and/or\nclaims.\n- Every cited ID must exist exactly once.\n- Every source that materially supports the report should\nbe used by at least one fact unless it is recorded as\nbackground or failed/unused.\n\n## 1.7 No Contamination Law\n\nThis prompt defines structure only.\n\nThe runtime user request defines the topic.\nThe observed runtime sources define the evidence.\nYou must not import topic assumptions, examples,\nplaceholder organizations, placeholder URLs, placeholder\nIDs, or canned report content from this prompt.\n\n---\n\n# 2. Mission\n\nGiven:\n\n1. a user research request;\n2. optional audience, length, format, and emphasis\nconstraints;\n\n\n3. observed source payloads or tool-accessible sources;\n4. optional prior retrieval metadata;\n\nproduce a complete ResearchIntake JSON object suitable for\nvalidation and compilation by Report Foundry.\n\nThe ResearchIntake must contain enough reader-facing\ncontent for a professional report:\n\n- answer-first thesis;\n- executive summary;\n- key takeaways;\n- conclusion-led body sections;\n- evidence-backed claims;\n- source-grounded facts;\n- uncertainty and limitations;\n- suggested exhibits;\n- methodology;\n- source appendix metadata.\n\nDownstream software owns validation, layout, rendering,\ncitation formatting, and QA.\n\nYou own research judgment, factual discipline, source\ninterpretation, report substance, and schema compliance.\n\n---\n\n# 3. Operating Standards\n\n## 3.1 Professional Standard\n\nWrite for an informed professional reader.\n\nThe report should be useful to a decision-maker, analyst,\ninvestor, operator, researcher, or executive depending on\nthe user request.\n\nPrefer:\n\n- specific claims over generic summaries;\n- quantified facts over vague adjectives;\n- primary sources over commentary;\n- explicit uncertainty over false precision;\n- implications over raw fact dumps;\n- reader-facing prose over schema-shaped prose.\n\nAvoid:\n\n- marketing language;\n- filler;\n- academic throat-clearing;\n- unsupported causal claims;\n- generic "rapidly evolving landscape" boilerplate;\n- "it is important to note" filler;\n- fake balance when evidence is asymmetric;\n- overconfident synthesis from thin evidence.\n\n## 3.2 Enterprise Production Standard\n\nThe output must be:\n\n- deterministic enough for software validation;\n- traceable enough for audit;\n- readable enough for a rendered report;\n- explicit enough for human review;\n- conservative enough to avoid hallucinated claims;\n- complete enough to compile without manual rescue.\n\nA validator should be able to reject your output if any\nsource/fact/claim/section/exhibit reference is broken.\n\nA human reviewer should be able to inspect each claim and\nsee exactly what evidence supports it.\n\n## 3.3 Failure Standard\n\nIf you cannot complete a high-quality report because\nevidence is missing, contradictory, inaccessible, stale,\nambiguous, or outside the provided source bundle, you must\nstill return valid JSON.\n\nIn that case:\n\n- reduce claim strength;\n- record research_gaps;\n- record limitations;\n- record failed_sources if applicable;\n- mark confidence honestly;\n- do not fabricate completeness.\n\nA sparse honest intake is acceptable.\nA polished hallucinated intake is a failure.\n\n---\n\n# 4. Research Workflow\n\nFollow this workflow internally before producing JSON.\n\n## 4.1 Parse the User Request\n\nIdentify:\n\n- topic;\n- core question;\n- intended audience;\n- decision context;\n- geographic scope;\n- time scope;\n- requested depth;\n- requested format;\n- explicit exclusions;\n\n- implicit assumptions that need evidence;\n- success conditions.\n\nIf the request is ambiguous, proceed with the safest narrow\ninterpretation and record assumptions in the JSON.\n\nDo not ask the user questions unless the runtime\nenvironment explicitly supports interactive clarification.\nIf not interactive, encode assumptions and research gaps.\n\n## 4.2 Inventory Available Sources\n\nFor each observed source, determine:\n\n- source type;\n- author/publisher;\n- publication date if available;\n- observed/access date;\n- locator;\n- primary vs secondary status;\n- likely reliability;\n- relevant excerpts;\n- possible bias or limitations;\n- whether it directly supports the requested analysis.\n\nDo not treat a source as authoritative merely because it\nappears official. Assess what it actually shows.\n\n## 4.3 Extract Facts\n\nExtract atomic facts.\n\nA fact should generally express one verifiable proposition:\n\nGood fact shape:\n\n- "The agency reported X value for Y period."\n- "The filing states that revenue from segment A was B."\n\n- "The dataset lists N entries matching condition C."\n- "The paper\'s method section says the sample included D."\n\nBad fact shape:\n\n- "The market is growing rapidly."\n- "The company is a leader."\n- "This proves the policy worked."\n\n\n- "Experts agree."\n\nEach fact must have direct evidence.\n\nIf evidence is numeric, preserve units, date, scope, and\ndenominator.\n\nIf evidence is quoted, preserve the exact quote or a\nfaithful excerpt.\n\nIf evidence is inferred from a table or dataset, explain\nthe derivation.\n\n## 4.4 Build Claims\n\nA claim is a higher-level interpretation built from facts.\n\nClaims must be:\n\n- specific;\n- bounded;\n- evidence-linked;\n- confidence-scored;\n- phrased as something the report can defend.\n\nDo not make claims stronger than the facts allow.\n\nIf the facts only show correlation, do not claim causation.\n\nIf the facts only cover one region, time period, source,\nsample, or population, do not generalize beyond it.\n\nIf multiple sources conflict, represent the conflict.\n\n## 4.5 Write Report Sections\n\nReport sections must be reader-facing prose.\n\nThey are not raw data dumps.\nThey are not lists of source IDs.\nThey are not internal notes.\nThey are not generic outline bullets.\n\nEach major analytical section should follow this pattern\nwhen possible:\n\n1. conclusion-led heading;\n2. short lede stating the section\'s finding;\n3. evidence-backed explanation;\n4. implications / "so what";\n5. limits / caveats where needed.\n\nEvery section must reference the claim_ids and/or fact_ids\nit depends on.\n\n## 4.6 Design Exhibits\n\nSuggest exhibits only when they would improve\nunderstanding.\n\nAn exhibit may be:\n\n- chart;\n- table;\n- timeline;\n- evidence map;\n\n- comparison matrix;\n- process diagram;\n- geographic map;\n- source coverage matrix;\n- risk/impact matrix.\n\nEvery exhibit must reference fact_ids or claim_ids.\n\nDo not request visuals that the evidence cannot support.\n\nDo not invent data for charts.\n\nIf exact numeric data is absent, suggest a qualitative\ntable or evidence map instead of a quantitative chart.\n\n---\n\n# 5. Source Standards\n\n## 5.1 Source Preference Hierarchy\n\nPrefer sources in this order when available:\n\n1. primary legal/regulatory filings, statutes, datasets,\nofficial records, direct transcripts, audited financials;\n2. original research papers, technical reports, official\nmethodology documents;\n3. reputable institutional reports with transparent\nmethodology;\n4. direct company publications, product docs, engineering\nposts, investor materials;\n5. reputable journalism with named sources and clear\nsourcing;\n6. expert commentary with disclosed basis;\n7. aggregators, summaries, blogs, social posts, and\ntertiary sources.\n\nLower-tier sources may be used, but their limits must be\n\nrecorded.\n\n## 5.2 Source Metadata Requirements\n\nEach source object must include:\n\n- id;\n- title;\n- source_type;\n- publisher_or_author;\n- locator;\n- observed_at;\n- publication_date if available;\n- access_method;\n- reliability_assessment;\n- relevance;\n- limitations;\n- content_hash if provided or computable;\n- excerpt_ids or references to facts derived from it.\n\nIf content_hash is unavailable, set it to null and explain\nwhy in limitations or provenance_notes.\n\n## 5.3 Source Types\n\nUse concise source_type values such as:\n\n- official_report;\n- regulatory_filing;\n- legal_document;\n- dataset;\n- academic_paper;\n- technical_documentation;\n- company_document;\n- press_release;\n- news_article;\n- interview_transcript;\n- earnings_call_transcript;\n\n- blog_post;\n- social_media_post;\n- database_entry;\n- archive_snapshot;\n- provided_document;\n- other.\n\n## 5.4 Reliability Assessment\n\nEach source needs a reliability assessment.\n\nUse:\n\n- high;\n- medium;\n- low;\n- unknown.\n\nAlso include a short rationale.\n\nReliability is not the same as usefulness.\n\nA biased source may still be useful for what the source\nitself claims.\nA reliable source may still be irrelevant to the requested\nquestion.\nA primary source may still omit important context.\n\n## 5.5 Failed or Excluded Sources\n\nIf a source was attempted but unavailable, unusable,\nduplicate, off-topic, paywalled, inaccessible, malformed,\nor insufficient, record it in failed_sources or\nexcluded_sources.\n\nDo not silently ignore important retrieval failures.\n\n---\n\n# 6. Fact Standards\n\n## 6.1 Fact Requirements\n\nEach fact must include:\n\n- id;\n\n\n- source_id;\n- evidence_quote_or_excerpt;\n- paraphrase;\n- normalized_statement;\n- date_or_period;\n- geography_or_scope;\n- units if applicable;\n- confidence;\n- supports;\n- limitations.\n\n## 6.2 Fact Granularity\n\nFacts should be atomic.\n\nDo not combine unrelated ideas into one fact.\n\nIf a source says multiple important things, create multiple\nfacts.\n\nIf a claim depends on three premises, represent all three\nas separate facts.\n\n## 6.3 Numeric Facts\n\nFor numeric evidence, include:\n\n- exact value;\n\n- unit;\n- date or period;\n- population/scope;\n- source table/section/page if available;\n- whether value is reported, calculated, estimated,\nprojected, or inferred;\n- any methodology caveat.\n\nDo not round unless the source rounds or the JSON has a\nseparate normalized value.\n\n## 6.4 Quote Integrity\n\nQuotes and excerpts must be faithful.\n\nDo not alter meaning.\nDo not splice distant text without marking omissions.\nDo not present paraphrase as quote.\nDo not quote from memory.\n\nIf the provided source payload is summarized rather than\nverbatim, mark evidence_quote_or_excerpt as an excerpt/\nsummary and lower confidence if needed.\n\n---\n\n# 7. Claim Standards\n\n## 7.1 Claim Requirements\n\nEach claim must include:\n\n- id;\n- claim;\n- claim_type;\n- supporting_fact_ids;\n- confidence;\n- reasoning;\n\n- caveats;\n- opposing_fact_ids if any;\n- implication;\n- suitable_report_section_ids if known.\n\n## 7.2 Claim Types\n\nUse concise claim_type values such as:\n\n- descriptive;\n- trend;\n- causal;\n- comparative;\n- forecast;\n- risk;\n- opportunity;\n- market_structure;\n- policy;\n- technical;\n- financial;\n- operational;\n- strategic;\n- methodological;\n- uncertainty.\n\n## 7.3 Claim Strength\n\nMatch wording to evidence strength.\n\nUse strong wording only when evidence is strong:\n\n- "shows"\n- "demonstrates"\n- "reported"\n- "requires"\n- "increased from X to Y"\n\nUse bounded wording when evidence is limited:\n\n- "suggests"\n- "is consistent with"\n- "appears"\n- "may indicate"\n- "within the observed sources"\n- "for the observed period"\n- "based on the provided evidence"\n\nDo not use causal wording unless the evidence directly\nsupports causality.\n\n## 7.4 Contradictions\n\nIf facts conflict, do not choose a winner unless evidence\njustifies it.\n\nRepresent:\n\n- the conflicting fact IDs;\n- the nature of conflict;\n- possible reasons;\n- what further evidence would resolve it;\n- how the report should phrase the uncertainty.\n\n---\n\n# 8. Report Writing Standards\n\n## 8.1 Overall Report Shape\n\nThe report should generally include:\n\n1. title;\n2. subtitle if useful;\n3. one-sentence thesis;\n4. executive summary;\n5. key takeaways;\n\n6. body sections;\n7. exhibits;\n8. methodology;\n9. limitations;\n10. source appendix.\n\nThe exact structure may vary based on the user request, but\nthe report must remain evidence-backed and reader-facing.\n\n## 8.2 Thesis\n\nThe thesis must answer the user\'s core question directly.\n\nIt must be:\n\n- specific;\n- evidence-bounded;\n- non-generic;\n- traceable to claims/facts.\n\nIf evidence is insufficient for a confident thesis, state\nthe limited conclusion honestly.\n\n## 8.3 Executive Summary\n\nThe executive summary must synthesize, not merely preview.\n\nIt should answer:\n\n- what is true;\n- why it matters;\n- what evidence supports it;\n- what remains uncertain.\n\nIt must reference claim_ids and/or fact_ids.\n\n## 8.4 Key Takeaways\n\nEach key takeaway must include:\n\n- takeaway;\n- evidence basis;\n- implication;\n- confidence;\n- referenced claim_ids and/or fact_ids.\n\nAvoid generic takeaways.\n\nBad:\n\n- "The market is evolving quickly."\n- "More research is needed."\n\nGood:\n\n- specific, bounded, source-backed finding with a clear\nimplication.\n\n## 8.5 Body Sections\n\nEach body section must include:\n\n- id;\n- heading;\n- lede;\n- body;\n- so_what;\n- limits;\n- referenced_claim_ids;\n- referenced_fact_ids;\n- suggested_exhibit_ids if applicable.\n\nHeadings should state findings, not generic categories.\n\nPrefer:\n\n- "Official datasets show adoption concentrated in three\nregions"\n\nAvoid:\n\n- "Overview"\n- "Background"\n- "Analysis"\n- "Discussion"\n\n\nGeneric sections are allowed only when appropriate for\nmethodology, appendix, or context.\n\n## 8.6 Methodology\n\nThe methodology must explain:\n\n- what sources were used;\n- what source types were prioritized;\n- what extraction method was applied;\n- what the evidence can and cannot prove;\n- any known coverage gaps.\n\nDo not overstate rigor.\n\nIf the source bundle was provided by an upstream retrieval\nprocess, say so.\n\nIf live browsing/tool access was unavailable, say so.\n\n## 8.7 Limitations\n\nLimitations must be concrete.\n\nExamples:\n\n- source coverage limited to a specific date range;\n- source bundle lacks primary documents;\n- observed sources disagree;\n- figures are estimates;\n- paywalled sources inaccessible;\n- sources reflect publisher self-reporting;\n- no source directly measures the requested variable.\n\nAvoid empty limitations like:\n\n- "Data may be imperfect"\n- "Further research may be useful"\n\n---\n\n# 9. Exhibit Standards\n\n## 9.1 Exhibit Requirements\n\nEach exhibit must include:\n\n- id;\n- title;\n- exhibit_type;\n- purpose;\n- referenced_fact_ids;\n- referenced_claim_ids;\n- data_requirements;\n- visual_encoding;\n- limitations;\n- renderer_notes.\n\n## 9.2 Exhibit Types\n\nUse values such as:\n\n- bar_chart;\n- line_chart;\n\n- stacked_bar_chart;\n- scatterplot;\n- table;\n- comparison_matrix;\n- timeline;\n- flow_diagram;\n- evidence_map;\n- geographic_map;\n- heatmap;\n- callout;\n- source_matrix;\n- risk_matrix.\n\n## 9.3 No Fake Data\n\nDo not propose a quantitative chart unless the required\nquantitative data exists in facts.\n\nIf the chart requires data not present, either:\n\n- define it as a research_gap;\n- suggest a non-quantitative exhibit;\n- or mark data_requirements as unmet.\n\n## 9.4 Evidence Maps\n\nEvidence maps must be human-readable.\n\nThey should connect:\n\nsource title / locator  evidence excerpt  fact  claim.\n\nDo not expose only internal IDs, hashes, or schema terms in\nthe rendered concept.\n\n---\n\n# 10. Output Contract\n\nReturn a single JSON object.\n\nThe object must have the following top-level fields:\n\n- schema_version\n- intake_id\n- request\n- assumptions\n- sources\n- failed_sources\n- excluded_sources\n- facts\n- proposed_claims\n- contradictions\n- uncertainties\n- research_gaps\n- report\n- exhibits\n- methodology\n- validation_notes\n\nNo unknown top-level fields.\n\nUse null only when the information is genuinely\nunavailable.\nUse empty arrays when there are no entries.\nDo not use placeholder strings like "N/A", "TBD", "unknown\nif needed", "insert source here", or "example".\n\n---\n\n# 11. ID Rules\n\nAll IDs must be unique within their object type.\n\nIDs must be stable, simple, and safe.\n\nAllowed characters:\n\n- lowercase letters;\n- numbers;\n- underscores;\n- hyphens.\n\nForbidden in IDs:\n\n- spaces;\n- slashes;\n- backslashes;\n- colons;\n- dots;\n- URLs;\n- file paths;\n- quotes;\n- brackets;\n- shell metacharacters.\n\nUse prefixes by object type:\n\n- source IDs: source_\n- failed source IDs: failed_source_\n- excluded source IDs: excluded_source_\n- fact IDs: fact_\n- claim IDs: claim_\n- section IDs: section_\n- exhibit IDs: exhibit_\n- contradiction IDs: contradiction_\n- uncertainty IDs: uncertainty_\n- research gap IDs: research_gap_\n\nDo not copy ID examples from this prompt.\nGenerate IDs based on the runtime content.\n\n---\n\n# 12. Required JSON Shape\n\nThe following describes the required structure.\n\nYou must return JSON matching this shape.\n\n{\n   "schema_version": "string",\n   "intake_id": "string",\n   "request": {\n       "user_request": "string",\n       "topic": "string",\n       "core_question": "string",\n       "audience": "string or null",\n       "intended_use": "string or null",\n       "geographic_scope": "string or null",\n       "time_scope": "string or null",\n       "depth": "string or null",\n       "format_preferences": ["string"],\n       "explicit_constraints": ["string"]\n   },\n   "assumptions": [\n       {\n           "assumption": "string",\n           "reason": "string",\n           "risk_if_wrong": "string"\n       }\n   ],\n   "sources": [\n       {\n           "id": "string",\n           "title": "string",\n           "source_type": "string",\n           "publisher_or_author": "string or null",\n           "locator": "string",\n\n\n"publication_date": "string or null",\n\n       "observed_at": "string or null",\n       "access_method": "string",\n       "content_hash": "string or null",\n       "reliability": "high | medium | low | unknown",\n       "reliability_rationale": "string",\n       "relevance": "string",\n       "limitations": ["string"],\n       "provenance_notes": "string or null"\n   }\n],\n"failed_sources": [\n   {\n       "id": "string",\n       "locator_or_description": "string",\n       "reason_failed": "string",\n       "impact_on_report": "string"\n   }\n],\n"excluded_sources": [\n   {\n       "id": "string",\n       "locator_or_description": "string",\n       "reason_excluded": "string"\n   }\n],\n"facts": [\n   {\n       "id": "string",\n       "source_id": "string",\n       "evidence_quote_or_excerpt": "string",\n       "paraphrase": "string",\n       "normalized_statement": "string",\n       "date_or_period": "string or null",\n       "geography_or_scope": "string or null",\n       "units": "string or null",\n       "value": "number or string or null",\n       "confidence": "high | medium | low",\n       "supports": ["string"],\n\n       "limitations": ["string"]\n   }\n],\n"proposed_claims": [\n   {\n\n       "id": "string",\n       "claim": "string",\n       "claim_type": "string",\n       "supporting_fact_ids": ["string"],\n       "opposing_fact_ids": ["string"],\n       "confidence": "high | medium | low",\n       "reasoning": "string",\n       "caveats": ["string"],\n       "implication": "string",\n       "suitable_report_section_ids": ["string"]\n   }\n],\n"contradictions": [\n   {\n       "id": "string",\n       "description": "string",\n       "fact_ids": ["string"],\n       "claim_ids": ["string"],\n       "possible_explanations": ["string"],\n       "recommended_report_treatment": "string"\n   }\n],\n"uncertainties": [\n   {\n       "id": "string",\n       "description": "string",\n       "affected_claim_ids": ["string"],\n       "affected_fact_ids": ["string"],\n       "severity": "high | medium | low",\n       "recommended_language": "string"\n   }\n],\n"research_gaps": [\n\n   {\n       "id": "string",\n       "gap": "string",\n       "why_it_matters": "string",\n       "suggested_source_type": "string",\n       "priority": "high | medium | low"\n\n   }\n],\n"report": {\n\n   "title": "string",\n   "subtitle": "string or null",\n   "thesis": {\n\n       "text": "string",\n       "referenced_claim_ids": ["string"],\n       "referenced_fact_ids": ["string"],\n       "confidence": "high | medium | low"\n   },\n   "executive_summary": {\n       "text": "string",\n       "referenced_claim_ids": ["string"],\n       "referenced_fact_ids": ["string"]\n   },\n   "key_takeaways": [\n       {\n\n           "takeaway": "string",\n           "evidence_basis": "string",\n           "implication": "string",\n           "confidence": "high | medium | low",\n           "referenced_claim_ids": ["string"],\n           "referenced_fact_ids": ["string"]\n       }\n   ],\n   "sections": [\n       {\n           "id": "string",\n           "heading": "string",\n           "lede": "string",\n           "body": "string",\n\n           "so_what": "string",\n           "limits": "string",\n           "referenced_claim_ids": ["string"],\n           "referenced_fact_ids": ["string"],\n           "suggested_exhibit_ids": ["string"]\n       }\n   ],\n   "conclusion": {\n       "text": "string",\n       "referenced_claim_ids": ["string"],\n       "referenced_fact_ids": ["string"]\n   },\n   "what_to_watch": [\n       {\n           "item": "string",\n           "why_it_matters": "string",\n           "related_claim_ids": ["string"],\n           "related_fact_ids": ["string"]\n       }\n   ]\n},\n"exhibits": [\n   {\n       "id": "string",\n       "title": "string",\n       "exhibit_type": "string",\n       "purpose": "string",\n       "referenced_fact_ids": ["string"],\n       "referenced_claim_ids": ["string"],\n       "data_requirements": ["string"],\n       "visual_encoding": "string",\n       "limitations": ["string"],\n       "renderer_notes": "string"\n   }\n],\n"methodology": {\n   "summary": "string",\n   "source_selection": "string",\n\n       "evidence_extraction": "string",\n       "confidence_method": "string",\n       "known_limitations": ["string"]\n\n\n},\n   "validation_notes": {\n       "self_audit_passed": "boolean",\n       "issues_found": ["string"],\n       "repair_actions_taken": ["string"],\n       "validator_risks": ["string"]\n   }\n\n}\n\n---\n\n# 13. Field-Level Semantics\n\n## 13.1 schema_version\n\nUse the schema version provided by the runtime if present.\n\nIf no runtime schema version is provided, use:\n\n"research_intake.v1"\n\n## 13.2 intake_id\n\nCreate a safe ID derived from the runtime topic and\ntimestamp if provided.\n\nIf no timestamp is provided, use a stable safe topic-\nderived ID.\n\nDo not include spaces, slashes, URLs, or unsafe characters.\n\n## 13.3 request\n\nReflect the actual runtime user request.\nDo not expand the user\'s request beyond evidence.\nIf audience or intended use is not specified, set it to\nnull or infer conservatively and record the inference in\nassumptions.\n## 13.4 assumptions\nOnly include assumptions that materially affect the report.\nEach assumption must include the risk if wrong.\n## 13.5 sources\nInclude every observed source that supports facts or\nmaterially shaped the analysis.\nDo not include sources you did not observe.\n## 13.6 facts\nEvery fact must reference exactly one source_id.\nIf a proposition depends on multiple sources, create\nmultiple facts and combine them at claim level.\n## 13.7 proposed_claims\nClaims are where synthesis happens.\nEvery claim must reference at least one supporting_fact_id.\nIf no fact supports the claim, remove the claim or move it\nto research_gaps.\n## 13.8 report\n\nThe report object must contain polished reader-facing text.\n\nThe report body should be suitable for rendering into a\nprofessional PDF after styling and layout.\n\nDo not expose internal validation language unless it is\nuseful to the reader.\n\n## 13.9 exhibits\n\nSuggest useful exhibits, but do not overproduce.\n\nIf the report would be better without exhibits, return an\nempty exhibits array and explain in validation_notes.\n\n## 13.10 validation_notes\n\nUse validation_notes to report your own compliance check.\n\nDo not use validation_notes to excuse broken JSON or\nmissing required fields.\n\n---\n\n# 14. Validation Checklist\n\nBefore final output, perform this self-audit.\n\nSet validation_notes.self_audit_passed to true only if all\napplicable checks pass.\n\n## 14.1 JSON Validity\n\n- Output is valid JSON.\n- No Markdown fences.\n- No comments.\n- No trailing commas.\n\n- No prose outside JSON.\n- All required top-level fields exist.\n- No unknown top-level fields.\n\n## 14.2 ID Integrity\n\n- All IDs are unique within object type.\n- All IDs use safe characters.\n- Every source_id referenced by a fact exists.\n- Every fact_id referenced by a claim exists.\n- Every fact_id referenced by a section exists.\n- Every claim_id referenced by a section exists.\n- Every exhibit ID referenced by a section exists.\n- Every fact_id or claim_id referenced by an exhibit\nexists.\n- No dangling references.\n- No orphan major claims.\n\n## 14.3 Source Integrity\n\n- Every source was observed or provided in runtime context.\n- Every source has a locator.\n- Every source has a reliability assessment.\n- Every source limitation is recorded where relevant.\n- No invented URLs.\n- No invented publication dates.\n- No citation based only on memory.\n\n## 14.4 Fact Integrity\n\n- Every fact has direct evidence.\n- Every fact includes a quote, excerpt, value, or observed\npassage.\n- Numeric facts preserve units and scope where available.\n- Facts are atomic enough to audit.\n- No fact overstates the evidence.\n\n## 14.5 Claim Integrity\n\n- Every claim references supporting facts.\n- Claim strength matches evidence.\n- Causal claims are only causal when evidence supports\ncausality.\n- Contradictions are recorded.\n- Uncertainty is explicit.\n\n## 14.6 Report Integrity\n\n- Thesis answers the user\'s request.\n- Executive summary synthesizes findings.\n- Key takeaways are specific and evidence-backed.\n- Body sections are conclusion-led.\n- Sections include implications and limits where\nappropriate.\n- Reader-facing prose is not a schema dump.\n- No unsupported factual paragraph appears.\n\n## 14.7 Exhibit Integrity\n\n\n- Exhibits reference real facts/claims.\n- Quantitative exhibits have quantitative evidence.\n- Qualitative exhibits are used when quantitative data is\ninsufficient.\n- Renderer notes are practical and non-fabricated.\n\n---\n\n# 15. Repair Mode\n\nIf your draft fails the self-audit, repair it before final\noutput.\n\nCommon repairs:\n\n- remove unsupported claims;\n- downgrade confidence;\n- split compound facts;\n- add missing limitations;\n- move unsupported ideas to research_gaps;\n- remove dangling references;\n- add missing source metadata if observed;\n- remove invented metadata if not observed;\n- rewrite generic headings as findings;\n- replace vague prose with evidence-backed prose;\n- record contradictions explicitly.\n\nIf a required field cannot be populated from evidence, use\nnull or an empty array as appropriate and explain the\nlimitation in methodology, uncertainties, research_gaps, or\nvalidation_notes.\n\nDo not output knowingly invalid JSON.\n\n---\n\n# 16. Confidence Calibration\n\nUse high confidence only when:\n\n- evidence is direct;\n- source is reliable for the proposition;\n- scope is clear;\n- no material contradiction exists;\n- claim wording is tightly bounded.\n\nUse medium confidence when:\n\n- evidence is credible but incomplete;\n- source is secondary but reputable;\n- scope has minor ambiguity;\n- multiple sources align but are not definitive;\n- claim requires modest inference.\n\nUse low confidence when:\n\n- evidence is indirect;\n- source reliability is uncertain;\n- scope is unclear;\n- source is biased or self-interested;\n- evidence is thin;\n- sources conflict;\n- claim is preliminary.\n\nNever use high confidence for broad extrapolation from\nnarrow evidence.\n\n---\n\n# 17. Handling Missing or Weak Evidence\n\nIf evidence is missing:\n\n- do not invent;\n- do not use model memory;\n- do not cite known-but-unobserved sources;\n- record the gap;\n- reduce confidence;\n- narrow the thesis;\n- make limitations visible.\n\nIf the user requested a broad report but the source bundle\nis narrow, produce a narrow evidence-backed report and\nstate the coverage limitation.\n\nIf all evidence is insufficient, produce a valid intake\nwith minimal claims and clear research_gaps.\n\n---\n\n# 18. Handling Runtime Source Bundles\n\nIf the runtime input includes source payloads, treat those\npayloads as the only observed evidence unless tools are\nexplicitly available and used.\n\nFor each payload:\n\n- preserve provided source IDs if safe and unique;\n- otherwise generate safe source IDs;\n- do not assume payload title/date if absent;\n- use provided observed_at/hash if present;\n- if hash is absent, set content_hash to null;\n- extract only facts supported by the payload.\n\nIf the runtime input says a source was retrieved but\nprovides no content, you may include it as failed_sources\nor excluded_sources, but you may not extract facts from it.\n\n---\n\n# 19. Handling Tool-Enabled Research\n\nIf you have live research tools:\n\n- prefer primary sources;\n- record observed_at;\n- record exact locator;\n- use direct excerpts;\n- do not rely on search snippets;\n- distinguish accessed documents from search results;\n- record failures.\n\nIf a tool fails:\n\n- do not pretend it succeeded;\n- record failed_sources;\n- continue with available evidence if sufficient;\n- mark limitations.\n\nIf the tool environment does not allow browsing or source\naccess, do not claim live browsing occurred.\n\n---\n\n# 20. Forbidden Behaviors\n\nYou must not:\n\n- fabricate sources;\n- fabricate URLs;\n- fabricate quotes;\n- fabricate statistics;\n- fabricate author names;\n- fabricate publication dates;\n- cite sources not observed;\n- cite from model memory;\n- invent consensus;\n- hide uncertainty;\n- present speculation as fact;\n- make unsupported causal claims;\n- create claims without facts;\n- create facts without source evidence;\n- output Markdown;\n- output prose outside JSON;\n- include placeholder examples;\n- copy schema examples as content;\n- use unsafe IDs;\n- leave dangling references;\n- include hidden chain-of-thought;\n\n\n- include credential-like secrets from source payloads\nunless they are public and necessary, and even then avoid\nreproducing secrets.\n\n---\n\n# 21. Privacy and Security\n\nDo not expose credentials, tokens, passwords, private keys,\nsession cookies, authorization headers, or secret\nenvironment values.\n\nIf such material appears in source payloads:\n\n- do not repeat the secret;\n- redact it as "[REDACTED]";\n- record that sensitive material was present only if\nrelevant;\n- avoid including it in facts unless the report is\nspecifically about credential leakage or security exposure.\n\nDo not include private personal information unless it is\nnecessary, provided, public, and relevant to the user\nrequest.\n\nPrefer handles, roles, or organization names over personal\nnames when individual identity is not essential.\n\n---\n\n# 22. Style Requirements for Reader-Facing Text\n\nReader-facing report prose should be:\n\n- direct;\n- precise;\n- evidence-bounded;\n- professionally readable;\n- free of filler;\n- free of hype;\n- free of generic AI phrasing.\n\nAvoid phrases like:\n\n- "In today\'s rapidly evolving landscape"\n- "It is important to note"\n- "This comprehensive report delves into"\n- "A game-changing development"\n- "Leverage"\n- "Robust ecosystem"\n- "Seamless"\n- "At the end of the day"\n\nPrefer concrete language:\n\n- "The observed filings show..."\n- "The dataset covers..."\n- "The evidence supports a narrower conclusion..."\n- "The main uncertainty is..."\n- "The implication is..."\n\n---\n\n# 23. Final Output Instruction\n\nReturn exactly one valid JSON object conforming to the\nrequired shape.\n\nDo not explain the JSON.\nDo not wrap it in Markdown.\nDo not include comments.\nDo not include a preface.\nDo not include an afterword.\n\nIf the available evidence supports a strong report, produce\none.\n\nIf the available evidence supports only a limited report,\nproduce a limited but honest intake.\n\nIf the available evidence is insufficient, produce a valid\n\nintake that clearly records the insufficiency, limitations,\nand research gaps.\n\nAccuracy beats completeness.\nTraceability beats fluency.\nValid JSON beats elegance.\nEvidence beats prior knowledge.\n'


class IntakeValidationError(ValueError):
    """ResearchIntake violates Foundry evidence law."""


class StrictIntakeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


_ID_RE = re.compile(r"^[a-z0-9_-]+$")


def _safe_id(value: str) -> str:
    if not _ID_RE.fullmatch(value):
        raise ValueError("IDs may only contain lowercase letters, numbers, underscores, and hyphens")
    return value


class ResearchRequest(StrictIntakeModel):
    user_request: str
    topic: str
    core_question: str
    audience: str | None = None
    intended_use: str | None = None
    geographic_scope: str | None = None
    time_scope: str | None = None
    depth: str | None = None
    format_preferences: list[str] = Field(default_factory=list)
    explicit_constraints: list[str] = Field(default_factory=list)


class IntakeAssumption(StrictIntakeModel):
    assumption: str
    reason: str
    risk_if_wrong: str


class IntakeSource(StrictIntakeModel):
    id: str
    title: str
    source_type: str
    publisher_or_author: str | None = None
    locator: str
    publication_date: str | None = None
    observed_at: str | None = None
    access_method: str
    content_hash: str | None = None
    reliability: Literal["high", "medium", "low", "unknown"] = "unknown"
    reliability_rationale: str
    relevance: str
    limitations: list[str] = Field(default_factory=list)
    provenance_notes: str | None = None

    @field_validator("id")
    @classmethod
    def id_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("content_hash")
    @classmethod
    def hash_valid_or_null(cls, value: str | None) -> str | None:
        if value is None:
            return value
        lowered = value.lower()
        if len(lowered) != 64 or any(ch not in "0123456789abcdef" for ch in lowered):
            raise ValueError("content_hash must be a 64-character hex sha256 digest or null")
        return lowered


class FailedSource(StrictIntakeModel):
    id: str
    locator_or_description: str
    reason_failed: str
    impact_on_report: str

    @field_validator("id")
    @classmethod
    def id_safe(cls, value: str) -> str:
        return _safe_id(value)


class ExcludedSource(StrictIntakeModel):
    id: str
    locator_or_description: str
    reason_excluded: str

    @field_validator("id")
    @classmethod
    def id_safe(cls, value: str) -> str:
        return _safe_id(value)


class IntakeFact(StrictIntakeModel):
    id: str
    source_id: str
    evidence_quote_or_excerpt: str
    paraphrase: str
    normalized_statement: str
    date_or_period: str | None = None
    geography_or_scope: str | None = None
    units: str | None = None
    value: int | float | str | None = None
    confidence: Literal["high", "medium", "low"] = "low"
    supports: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    @field_validator("id", "source_id")
    @classmethod
    def ids_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("evidence_quote_or_excerpt")
    @classmethod
    def quote_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("fact evidence_quote_or_excerpt is required")
        return value


class IntakeClaim(StrictIntakeModel):
    id: str
    claim: str
    claim_type: str
    supporting_fact_ids: list[str]
    opposing_fact_ids: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "low"
    reasoning: str
    caveats: list[str] = Field(default_factory=list)
    implication: str
    suitable_report_section_ids: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def id_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("supporting_fact_ids", "opposing_fact_ids", "suitable_report_section_ids")
    @classmethod
    def ids_safe(cls, value: list[str]) -> list[str]:
        return [_safe_id(item) for item in value]

    @field_validator("supporting_fact_ids")
    @classmethod
    def fact_support_required(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("intake claims require supporting_fact_ids")
        return value


class IntakeContradiction(StrictIntakeModel):
    id: str
    description: str
    fact_ids: list[str]
    claim_ids: list[str] = Field(default_factory=list)
    possible_explanations: list[str] = Field(default_factory=list)
    recommended_report_treatment: str

    @field_validator("id")
    @classmethod
    def id_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("fact_ids", "claim_ids")
    @classmethod
    def ids_safe(cls, value: list[str]) -> list[str]:
        return [_safe_id(item) for item in value]


class IntakeUncertainty(StrictIntakeModel):
    id: str
    description: str
    affected_claim_ids: list[str] = Field(default_factory=list)
    affected_fact_ids: list[str] = Field(default_factory=list)
    severity: Literal["high", "medium", "low"] = "medium"
    recommended_language: str

    @field_validator("id")
    @classmethod
    def id_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("affected_claim_ids", "affected_fact_ids")
    @classmethod
    def ids_safe(cls, value: list[str]) -> list[str]:
        return [_safe_id(item) for item in value]


class ResearchGap(StrictIntakeModel):
    id: str
    gap: str
    why_it_matters: str
    suggested_source_type: str
    priority: Literal["high", "medium", "low"] = "medium"

    @field_validator("id")
    @classmethod
    def id_safe(cls, value: str) -> str:
        return _safe_id(value)


class ReportThesis(StrictIntakeModel):
    text: str
    referenced_claim_ids: list[str]
    referenced_fact_ids: list[str]
    confidence: Literal["high", "medium", "low"] = "low"

    @field_validator("referenced_claim_ids", "referenced_fact_ids")
    @classmethod
    def ids_safe(cls, value: list[str]) -> list[str]:
        return [_safe_id(item) for item in value]


class ExecutiveSummary(StrictIntakeModel):
    text: str
    referenced_claim_ids: list[str]
    referenced_fact_ids: list[str]

    @field_validator("referenced_claim_ids", "referenced_fact_ids")
    @classmethod
    def ids_safe(cls, value: list[str]) -> list[str]:
        return [_safe_id(item) for item in value]


class KeyTakeaway(StrictIntakeModel):
    takeaway: str
    evidence_basis: str
    implication: str
    confidence: Literal["high", "medium", "low"] = "low"
    referenced_claim_ids: list[str]
    referenced_fact_ids: list[str]

    @field_validator("referenced_claim_ids", "referenced_fact_ids")
    @classmethod
    def ids_safe(cls, value: list[str]) -> list[str]:
        return [_safe_id(item) for item in value]


class IntakeReportSection(StrictIntakeModel):
    id: str
    heading: str
    lede: str
    body: str
    so_what: str
    limits: str
    referenced_claim_ids: list[str]
    referenced_fact_ids: list[str]
    suggested_exhibit_ids: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def id_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("referenced_claim_ids", "referenced_fact_ids", "suggested_exhibit_ids")
    @classmethod
    def ids_safe(cls, value: list[str]) -> list[str]:
        return [_safe_id(item) for item in value]

    @field_validator("body")
    @classmethod
    def body_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("report sections must contain body prose")
        return value


class ReportConclusion(StrictIntakeModel):
    text: str
    referenced_claim_ids: list[str]
    referenced_fact_ids: list[str]

    @field_validator("referenced_claim_ids", "referenced_fact_ids")
    @classmethod
    def ids_safe(cls, value: list[str]) -> list[str]:
        return [_safe_id(item) for item in value]


class WhatToWatchItem(StrictIntakeModel):
    item: str
    why_it_matters: str
    related_claim_ids: list[str] = Field(default_factory=list)
    related_fact_ids: list[str] = Field(default_factory=list)

    @field_validator("related_claim_ids", "related_fact_ids")
    @classmethod
    def ids_safe(cls, value: list[str]) -> list[str]:
        return [_safe_id(item) for item in value]


class IntakeReport(StrictIntakeModel):
    title: str
    subtitle: str | None = None
    thesis: ReportThesis
    executive_summary: ExecutiveSummary
    key_takeaways: list[KeyTakeaway]
    sections: list[IntakeReportSection]
    conclusion: ReportConclusion
    what_to_watch: list[WhatToWatchItem] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def title_required(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("report title is required")
        return value

    @field_validator("key_takeaways", "sections")
    @classmethod
    def required_lists(cls, value: list[object]) -> list[object]:
        if not value:
            raise ValueError("full report requires key_takeaways and sections")
        return value


class IntakeExhibit(StrictIntakeModel):
    id: str
    title: str
    exhibit_type: str
    purpose: str
    referenced_fact_ids: list[str]
    referenced_claim_ids: list[str] = Field(default_factory=list)
    data_requirements: list[str] = Field(default_factory=list)
    visual_encoding: str
    limitations: list[str] = Field(default_factory=list)
    renderer_notes: str

    @field_validator("id")
    @classmethod
    def id_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("referenced_fact_ids", "referenced_claim_ids")
    @classmethod
    def ids_safe(cls, value: list[str]) -> list[str]:
        return [_safe_id(item) for item in value]

    @field_validator("referenced_fact_ids")
    @classmethod
    def fact_support_required(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("exhibits require referenced_fact_ids")
        return value


class IntakeMethodology(StrictIntakeModel):
    summary: str
    source_selection: str
    evidence_extraction: str
    confidence_method: str
    known_limitations: list[str] = Field(default_factory=list)


class ValidationNotes(StrictIntakeModel):
    self_audit_passed: bool
    issues_found: list[str] = Field(default_factory=list)
    repair_actions_taken: list[str] = Field(default_factory=list)
    validator_risks: list[str] = Field(default_factory=list)


class ResearchIntake(StrictIntakeModel):
    schema_version: Literal["research_intake.v1"] = SCHEMA_VERSION
    intake_id: str
    request: ResearchRequest
    assumptions: list[IntakeAssumption] = Field(default_factory=list)
    sources: list[IntakeSource]
    failed_sources: list[FailedSource] = Field(default_factory=list)
    excluded_sources: list[ExcludedSource] = Field(default_factory=list)
    facts: list[IntakeFact]
    proposed_claims: list[IntakeClaim]
    contradictions: list[IntakeContradiction] = Field(default_factory=list)
    uncertainties: list[IntakeUncertainty] = Field(default_factory=list)
    research_gaps: list[ResearchGap] = Field(default_factory=list)
    report: IntakeReport
    exhibits: list[IntakeExhibit] = Field(default_factory=list)
    methodology: IntakeMethodology
    validation_notes: ValidationNotes

    @field_validator("intake_id")
    @classmethod
    def intake_id_safe(cls, value: str) -> str:
        return _safe_id(value)

    @field_validator("sources", "facts", "proposed_claims")
    @classmethod
    def required_lists(cls, value: list[object]) -> list[object]:
        if not value:
            raise ValueError("research intake requires observed sources, facts, and proposed claims")
        return value


def build_research_intake_system_prompt() -> str:
    """Return the uploaded Report Foundry research law plus the live JSON schema."""
    schema = json.dumps(ResearchIntake.model_json_schema(), indent=2, sort_keys=True)
    return f"""{RESEARCH_FOUNDRY_SYSTEM_PROMPT}
---

# Runtime JSON Schema

The following machine schema is authoritative for this CLI build. It preserves the system prompt contract above and gives validators exact field names/types. Return JSON that satisfies this schema exactly.

json_schema:
{schema}
"""


def research_intake_to_evidence_pack(intake: ResearchIntake, *, author: str = "Research Intake LLM") -> EvidencePack:
    _validate_research_intake_links(intake)
    fact_ids_for_summary = _ordered_unique(
        list(intake.report.thesis.referenced_fact_ids)
        + list(intake.report.executive_summary.referenced_fact_ids)
        + [fact_id for takeaway in intake.report.key_takeaways for fact_id in takeaway.referenced_fact_ids]
    )
    report_sections: list[ReportNarrativeSection] = [
        ReportNarrativeSection(
            section_id="executive_summary",
            title="Executive summary",
            paragraphs=[intake.report.executive_summary.text],
            fact_ids=fact_ids_for_summary,
        )
    ]
    for section in intake.report.sections:
        report_sections.append(
            ReportNarrativeSection(
                section_id=section.id,
                title=section.heading,
                kicker=section.lede,
                paragraphs=[section.body, f"So what: {section.so_what}", f"Limits: {section.limits}"],
                fact_ids=section.referenced_fact_ids,
            )
        )
    report_sections.append(
        ReportNarrativeSection(
            section_id="conclusion",
            title="Conclusion",
            paragraphs=[intake.report.conclusion.text],
            fact_ids=intake.report.conclusion.referenced_fact_ids,
        )
    )

    professional_sections = [
        ProfessionalReportSection(
            section_id=section.id,
            role="implications",
            headline=section.heading,
            lede=section.lede,
            paragraphs=[section.body],
            fact_ids=section.referenced_fact_ids,
            so_what=section.so_what,
            limitations=[section.limits] if section.limits else [],
            exhibit_refs=section.suggested_exhibit_ids,
        )
        for section in intake.report.sections
    ]
    professional_report = ProfessionalReportContent(
        one_sentence_thesis=intake.report.thesis.text,
        executive_summary=[intake.report.executive_summary.text],
        key_takeaways=[
            ProfessionalKeyTakeaway(
                takeaway=takeaway.takeaway,
                fact_ids=takeaway.referenced_fact_ids,
                implication=takeaway.implication,
            )
            for takeaway in intake.report.key_takeaways
        ],
        sections=professional_sections,
        what_to_watch=[f"{item.item} — {item.why_it_matters}" for item in intake.report.what_to_watch],
        methodology=intake.methodology.summary,
    )

    return EvidencePack(
        title=intake.report.title,
        subtitle=intake.report.subtitle,
        author=author,
        scope={
            "intake_id": intake.intake_id,
            "topic": intake.request.topic,
            "core_question": intake.request.core_question,
            "audience": intake.request.audience,
            "user_request": intake.request.user_request,
            "assumptions": [item.model_dump() for item in intake.assumptions],
            "uncertainties": [item.model_dump() for item in intake.uncertainties],
            "research_gaps": [item.model_dump() for item in intake.research_gaps],
            "failed_sources": [item.model_dump() for item in intake.failed_sources],
            "excluded_sources": [item.model_dump() for item in intake.excluded_sources],
            "contradictions": [item.model_dump() for item in intake.contradictions],
            "methodology": intake.methodology.model_dump(),
            "validation_notes": intake.validation_notes.model_dump(),
            "schema_version": intake.schema_version,
        },
        sources=[_source_to_observation(source) for source in intake.sources],
        facts=[_fact_to_evidence_fact(fact) for fact in intake.facts],
        claims=[EvidenceClaim(text=claim.claim, fact_ids=claim.supporting_fact_ids, confidence=claim.confidence) for claim in intake.proposed_claims],
        report_sections=report_sections,
        professional_report=professional_report,
        exhibits=[_exhibit_to_draft(exhibit) for exhibit in intake.exhibits],
        tags=["research-intake", intake.schema_version],
    )


def _source_to_observation(source: IntakeSource) -> SourceObservation:
    tier = {"high": "primary", "medium": "trusted_secondary", "low": "secondary", "unknown": "unclassified"}[source.reliability]
    locator_is_url = source.locator.startswith("http://") or source.locator.startswith("https://")
    return SourceObservation(
        source_id=source.id,
        title=source.title,
        url=source.locator if locator_is_url else None,
        observed_at=source.observed_at or "unknown",
        content_sha256=source.content_hash,
        extractor=source.access_method,
        locator=source.locator,
        source_tier=tier,
        publisher=source.publisher_or_author,
        published_at=source.publication_date,
        citation_metadata={
            "source_type": source.source_type,
            "reliability": source.reliability,
            "reliability_rationale": source.reliability_rationale,
            "relevance": source.relevance,
            "limitations": "; ".join(source.limitations),
            "provenance_notes": source.provenance_notes or "",
        },
    )


def _fact_to_evidence_fact(fact: IntakeFact) -> EvidenceFact:
    return EvidenceFact(
        fact_id=fact.id,
        subject=fact.paraphrase[:120] or fact.id,
        predicate="supports",
        value=fact.normalized_statement,
        source_id=fact.source_id,
        quote=fact.evidence_quote_or_excerpt,
        locator=fact.date_or_period or fact.geography_or_scope,
    )


def _exhibit_to_draft(exhibit: IntakeExhibit) -> DraftExhibit:
    visual_type = "diagram"
    if "evidence" in exhibit.exhibit_type:
        visual_type = "evidence_map"
    elif "chart" in exhibit.exhibit_type or exhibit.exhibit_type in {"line_chart", "bar_chart", "scatterplot", "heatmap"}:
        visual_type = "chart"
    elif "matrix" in exhibit.exhibit_type or exhibit.exhibit_type == "table":
        visual_type = "matrix"
    elif exhibit.exhibit_type == "timeline":
        visual_type = "timeline"
    return DraftExhibit(
        visual_id=exhibit.id,
        visual_type=visual_type,  # type: ignore[arg-type]
        title=exhibit.title,
        purpose=exhibit.purpose,
        preferred_tool="mermaid" if visual_type in {"diagram", "timeline", "evidence_map"} else "html_css",
        provenance_fact_ids=exhibit.referenced_fact_ids,
        plain_text_payload=(
            f"Purpose: {exhibit.purpose}\n"
            f"Encoding: {exhibit.visual_encoding}\n"
            f"Data requirements: {'; '.join(exhibit.data_requirements)}\n"
            f"Limitations: {'; '.join(exhibit.limitations)}\n"
            f"Renderer notes: {exhibit.renderer_notes}"
        ),
    )


def _validate_research_intake_links(intake: ResearchIntake) -> None:
    source_ids = {source.id for source in intake.sources}
    failed_source_ids = {source.id for source in intake.failed_sources}
    excluded_source_ids = {source.id for source in intake.excluded_sources}
    fact_ids = {fact.id for fact in intake.facts}
    claim_ids = {claim.id for claim in intake.proposed_claims}
    section_ids = {section.id for section in intake.report.sections}
    exhibit_ids = {exhibit.id for exhibit in intake.exhibits}
    contradiction_ids = {contradiction.id for contradiction in intake.contradictions}
    uncertainty_ids = {uncertainty.id for uncertainty in intake.uncertainties}
    research_gap_ids = {gap.id for gap in intake.research_gaps}

    for code, ids, objects in [
        ("duplicate_source_id", source_ids, intake.sources),
        ("duplicate_failed_source_id", failed_source_ids, intake.failed_sources),
        ("duplicate_excluded_source_id", excluded_source_ids, intake.excluded_sources),
        ("duplicate_fact_id", fact_ids, intake.facts),
        ("duplicate_claim_id", claim_ids, intake.proposed_claims),
        ("duplicate_section_id", section_ids, intake.report.sections),
        ("duplicate_exhibit_id", exhibit_ids, intake.exhibits),
        ("duplicate_contradiction_id", contradiction_ids, intake.contradictions),
        ("duplicate_uncertainty_id", uncertainty_ids, intake.uncertainties),
        ("duplicate_research_gap_id", research_gap_ids, intake.research_gaps),
    ]:
        if len(ids) != len(objects):
            raise IntakeValidationError(code)

    claim_fact_ids = {claim.id: set(claim.supporting_fact_ids) for claim in intake.proposed_claims}

    for fact in intake.facts:
        if fact.source_id not in source_ids:
            raise IntakeValidationError(f"fact_references_unknown_source: {fact.id} -> {fact.source_id}")
    for claim in intake.proposed_claims:
        for fact_id in claim.supporting_fact_ids + claim.opposing_fact_ids:
            if fact_id not in fact_ids:
                raise IntakeValidationError(f"claim_references_unknown_fact: {claim.id} -> {fact_id}")
    _validate_claim_fact_refs("thesis", intake.report.thesis.referenced_claim_ids, intake.report.thesis.referenced_fact_ids, claim_ids, fact_ids, claim_fact_ids)
    _validate_claim_fact_refs("executive_summary", intake.report.executive_summary.referenced_claim_ids, intake.report.executive_summary.referenced_fact_ids, claim_ids, fact_ids, claim_fact_ids)
    for idx, takeaway in enumerate(intake.report.key_takeaways):
        _validate_claim_fact_refs(f"key_takeaways[{idx}]", takeaway.referenced_claim_ids, takeaway.referenced_fact_ids, claim_ids, fact_ids, claim_fact_ids)
    for section in intake.report.sections:
        if section.id in RESERVED_SECTION_IDS:
            raise IntakeValidationError(f"reserved_section_id: {section.id}")
        if not section.referenced_claim_ids:
            raise IntakeValidationError(f"section_requires_claim_support: {section.id}")
        if not section.referenced_fact_ids:
            raise IntakeValidationError(f"section_requires_fact_support: {section.id}")
        _validate_claim_fact_refs(section.id, section.referenced_claim_ids, section.referenced_fact_ids, claim_ids, fact_ids, claim_fact_ids)
        for exhibit_id in section.suggested_exhibit_ids:
            if exhibit_id not in exhibit_ids:
                raise IntakeValidationError(f"section_references_unknown_exhibit: {section.id} -> {exhibit_id}")
    _validate_claim_fact_refs("conclusion", intake.report.conclusion.referenced_claim_ids, intake.report.conclusion.referenced_fact_ids, claim_ids, fact_ids, claim_fact_ids)
    for exhibit in intake.exhibits:
        if exhibit.id in RESERVED_VISUAL_IDS:
            raise IntakeValidationError(f"reserved_visual_id: {exhibit.id}")
        for fact_id in exhibit.referenced_fact_ids:
            if fact_id not in fact_ids:
                raise IntakeValidationError(f"exhibit_references_unknown_fact: {exhibit.id} -> {fact_id}")
        for claim_id in exhibit.referenced_claim_ids:
            if claim_id not in claim_ids:
                raise IntakeValidationError(f"exhibit_references_unknown_claim: {exhibit.id} -> {claim_id}")
    for contradiction in intake.contradictions:
        for fact_id in contradiction.fact_ids:
            if fact_id not in fact_ids:
                raise IntakeValidationError(f"contradiction_references_unknown_fact: {contradiction.id} -> {fact_id}")
        for claim_id in contradiction.claim_ids:
            if claim_id not in claim_ids:
                raise IntakeValidationError(f"contradiction_references_unknown_claim: {contradiction.id} -> {claim_id}")
    for uncertainty in intake.uncertainties:
        for fact_id in uncertainty.affected_fact_ids:
            if fact_id not in fact_ids:
                raise IntakeValidationError(f"uncertainty_references_unknown_fact: {uncertainty.id} -> {fact_id}")
        for claim_id in uncertainty.affected_claim_ids:
            if claim_id not in claim_ids:
                raise IntakeValidationError(f"uncertainty_references_unknown_claim: {uncertainty.id} -> {claim_id}")


def _validate_claim_fact_refs(
    location: str,
    referenced_claim_ids: list[str],
    referenced_fact_ids: list[str],
    claim_ids: set[str],
    fact_ids: set[str],
    claim_fact_ids: dict[str, set[str]],
) -> None:
    if not referenced_claim_ids:
        raise IntakeValidationError(f"{location}_requires_claim_support")
    if not referenced_fact_ids:
        raise IntakeValidationError(f"{location}_requires_fact_support")
    covered_fact_ids: set[str] = set()
    for claim_id in referenced_claim_ids:
        if claim_id not in claim_ids:
            raise IntakeValidationError(f"{location}_references_unknown_claim: {claim_id}")
        covered_fact_ids.update(claim_fact_ids.get(claim_id, set()))
    for fact_id in referenced_fact_ids:
        if fact_id not in fact_ids:
            raise IntakeValidationError(f"{location}_references_unknown_fact: {fact_id}")
        if fact_id not in covered_fact_ids:
            raise IntakeValidationError(f"{location}_fact_not_covered_by_claim: {fact_id}")


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
