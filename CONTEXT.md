# Game Review Analyzer - Domain Context

## Report lifecycle

- **Main Report:** The one current cumulative analysis for a game. A successful extension or replacement atomically replaces it.
- **Test Report:** The one current 50-review provider test for a game. It remains separate from the Main Report.
- **Extend report:** Refresh Steam, add unseen oldest and newest reviews, and replace the Main Report with the cumulative result.
- **Replace report:** Refresh Steam and build a fresh Main Report without reusing prior analysis state.

## Analysis

- **Theme:** A model-generated summary of one recurring positive or negative player opinion.
- **Theme Membership:** An internal link between a Theme and one analyzed Review Revision.
- **Theme Candidate:** Hidden merge state that may become a Theme after later extensions.
- **Oldest cohort:** Reviews selected from the oldest end of the unseen ordered review pool.
- **Newest cohort:** Reviews selected from the newest end of the unseen ordered review pool.
