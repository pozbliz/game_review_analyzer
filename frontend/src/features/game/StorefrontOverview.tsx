import { SteamMetadata } from "../../api/shell";

interface StorefrontOverviewProps {
  metadata: SteamMetadata;
}

export default function StorefrontOverview({ metadata }: StorefrontOverviewProps): JSX.Element {
  const store = metadata.storefront;
  const unknown = "Unknown / unavailable";
  return (
    <section className="storefront-overview" aria-labelledby="storefront-title">
      <header>
        <div>
          <p className="eyebrow">STEAM SNAPSHOT</p>
          <h2 id="storefront-title">Storefront overview</h2>
        </div>
        <a href={`https://store.steampowered.com/app/${metadata.app_id}`} target="_blank" rel="noreferrer">View on Steam</a>
      </header>
      <p>{store.short_description ?? unknown}</p>
      {store.about_text && <details><summary>About this game</summary><p>{store.about_text}</p></details>}
      <div className="storefront-groups">
        <section>
          <h3>Store facts</h3>
          <dl>
            <div><dt>Publishers</dt><dd>{store.publishers?.join(", ") ?? unknown}</dd></div>
            <div><dt>Genres</dt><dd>{store.genres?.join(", ") ?? unknown}</dd></div>
            <div><dt>Tags</dt><dd>{store.tags?.join(", ") ?? unknown}</dd></div>
            <div><dt>Regional price</dt><dd>{store.price ? `${store.price.final_formatted} · ${store.price.currency} · ${store.price.country_code}` : unknown}</dd></div>
            <div><dt>Platforms</dt><dd>{store.platforms?.join(", ") ?? unknown}</dd></div>
            <div><dt>Languages</dt><dd>{store.supported_languages ?? unknown}</dd></div>
          </dl>
        </section>
        <section>
          <h3>Features</h3>
          {store.features ? (
            <ul>{store.features.map((feature) => <li key={`${feature.group}-${feature.name}`}>{feature.name} · {featureState(feature.state)}</li>)}</ul>
          ) : <p>{unknown}</p>}
        </section>
        <section>
          <h3>DLC, demos, and packages</h3>
          <p>DLC: {store.dlc_names?.join(", ") ?? (store.dlc_app_ids?.length ? store.dlc_app_ids.join(", ") : unknown)}</p>
          <p>Demos: {store.demo_app_ids?.length ? store.demo_app_ids.join(", ") : unknown}</p>
          <p>Packages: {store.package_names?.join(", ") ?? unknown}</p>
        </section>
      </div>
      {(store.screenshot_urls || store.trailers) && (
        <section className="store-media" aria-labelledby="media-title">
          <h3 id="media-title">Steam-hosted media</h3>
          <div>
            {store.screenshot_urls?.map((url, index) => <img key={url} src={url} alt={`${metadata.title} Steam screenshot ${index + 1}`} />)}
            {store.trailers?.map((trailer) => (
              <a key={trailer.video_url} href={trailer.video_url} target="_blank" rel="noreferrer">
                <img src={trailer.thumbnail_url} alt="" />
                Play {trailer.name} on Steam
              </a>
            ))}
          </div>
        </section>
      )}
    </section>
  );
}

function featureState(state: string): string {
  return state === "supported" ? "Supported"
    : state === "partial" ? "Partial"
      : state === "not_supported" ? "Not supported"
        : "Unknown / unavailable";
}
