# Game Review Analyzer — Domain Context

## Report lifecycle

- **Create report:** Generate a new immutable Report Version from a selected game and review scope. This applies to both the first report and a later result after refreshing or changing scope.
- **Report Version:** A preserved, immutable result tied to its exact review revisions, scope, metadata snapshot, and analysis configuration.
- **Latest report:** The newest Report Version opened by default.
- **Report history:** Older Report Versions for the selected game.
- **Compare reports:** A future operation that explicitly contrasts reports; it is not a synonym for creating or refreshing one.
