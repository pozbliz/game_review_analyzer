# Domain Glossary

## Review Analysis

**Review Cohort**

A subset of reviews selected by explicit criteria, such as a playtime range, for focused examination.

_Avoid:_ Segment when the selection criteria are not defined

**Evidence Filter**

A temporary restriction applied to an existing analysis that limits visible raw review evidence and recalculates support and sentiment metrics for already discovered themes without discovering new themes.

_Avoid:_ Cohort analysis, reanalysis

**Cohort Analysis**

A saved theme-discovery analysis whose scope is limited to a review cohort, allowing themes specific to that cohort to emerge and remain identifiable by that scope.

_Avoid:_ Filter, filtered view

**Steam Recommendation**

The review author's whole-review verdict of `Recommended` or `Not Recommended` recorded by Steam.

_Avoid:_ Review sentiment, opinion sentiment

**Opinion Sentiment**

The positive, negative, or neutral stance expressed by one opinion point about a specific subject, independent of the review's Steam recommendation.

_Avoid:_ Steam recommendation, whole-review sentiment

**Opinion Point**

A sentence- or clause-level statement that expresses one reviewer's opinion about one subject. A review can contain several Opinion Points with different subjects and sentiments.

_Avoid:_ Review when referring to a single claim, whole-review embedding

**Theme**

A recurring positive or negative player opinion supported by related Opinion Points from multiple distinct reviews. A Theme is more specific than the category used to organize it.

_Avoid:_ Category, topic when the recurring opinion has not been established

**Technical Theme**

A recurring opinion about stability, performance, data integrity, or another technical quality. It follows the Theme evidence contract but appears outside the design taxonomy and headline rankings.

_Avoid:_ Design Theme, technical category

**Game Dataset**

The locally retained Steam review history and source metadata associated with one AppID and reused across analyses and refreshes.

_Avoid:_ Report, analysis result

**Review Revision**

The immutable state of one Steam review observed at a particular acquisition time. A later edit creates another Review Revision rather than changing evidence used by an existing Report Version.

_Avoid:_ Current review when referring to historical evidence, mutable review

**Analysis Job**

A durable unit of review acquisition and processing that records progress until it completes, fails, is cancelled, or is deleted.

_Avoid:_ Report, request

**Report Version**

An immutable analysis result tied to an exact review scope, exact Review Revision membership, Steam metadata snapshot, pipeline configuration, provider and model, and creation time.

_Avoid:_ Live report, mutable report

## Steam Data

**Steam Metadata Snapshot**

The game and storefront information returned by Steam sources at the time a Report Version is created. Later Steam changes do not alter the snapshot stored with an existing report.

_Avoid:_ Current metadata when referring to a historical report

## Data Portability

**Portable Report Archive**

A self-contained export containing a Report Version and the complete source evidence required to restore it on another installation without an existing Game Dataset.

_Avoid:_ Default JSON export, report backup when evidence is omitted
