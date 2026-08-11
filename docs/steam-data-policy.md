# Steam data policy baseline

Validated against Valve's official documentation on 2026-08-11. Recheck before each release because Valve may change or discontinue the APIs and their terms.

## Application obligations

- Use the current paginated [`IStoreService/GetAppList`](https://partner.steamgames.com/doc/webapi/IStoreService), not deprecated `ISteamApps/GetAppList`. Send its required user Web API key only from the local backend over HTTPS and keep it out of URLs, logs, SQLite, frontend assets, responses, diagnostics, and exports.
- Keep total keyed Steam Web API traffic below 100,000 calls per day. Catalog synchronization uses up to 50,000 results per call, follows `last_appid`, and uses `if_modified_since` for later synchronization.
- Explain what Steam data is retained locally and where, provide deletion controls, and identify the storage country in the release privacy notice. The application retrieves no private Steam-user data.
- Present Steam data as-is, without warranty, and do not imply Valve or Steam endorsement or affiliation.
- Link displayed Steam data back to Steam. Steam links must remain ordinary followable links.
- If Web API use ends, remove retained keyed Steam data. A release procedure must include this cleanup obligation.

The [Steam Web API Terms of Use](https://steamcommunity.com/dev/apiterms) set these obligations and the daily request ceiling. [Steam authentication guidance](https://partner.steamgames.com/doc/webapi_overview/auth) allows a standard user key for keyed public methods and requires keys to be protected.

## Best-effort storefront sources

Valve does not document the public Store `appdetails` and search responses used for optional rich metadata and unkeyed fallback search. Treat them as replaceable, failure-prone sources: use conservative bounded requests, retain source status and missing-field provenance, never let optional failure block direct-AppID review analysis, and never describe their behavior as an API guarantee.
