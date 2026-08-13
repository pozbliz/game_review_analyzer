import { MouseEvent, useEffect, useRef, useState } from "react";
import { SteamMetadata } from "../../api/shell";

interface StorefrontOverviewProps {
  metadata: SteamMetadata;
}

export default function StorefrontOverview({ metadata }: StorefrontOverviewProps): JSX.Element {
  const store = metadata.storefront;
  const unknown = "Unknown / unavailable";
  const languages: LanguageGroups | null = groupLanguages(store.supported_languages);
  const screenshots: string[] = store.screenshot_urls ?? [];
  const [selectedScreenshot, setSelectedScreenshot] = useState<number | null>(null);
  const lightboxRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const lightbox: HTMLDialogElement | null = lightboxRef.current;
    if (selectedScreenshot === null || !lightbox || lightbox.open) return;
    if (typeof lightbox.showModal === "function") lightbox.showModal();
    else lightbox.setAttribute("open", "");
  }, [selectedScreenshot]);

  function closeLightbox(): void {
    const lightbox: HTMLDialogElement | null = lightboxRef.current;
    if (lightbox && typeof lightbox.close === "function") lightbox.close();
    setSelectedScreenshot(null);
  }

  function closeFromBackdrop(event: MouseEvent<HTMLDialogElement>): void {
    if (event.target === event.currentTarget) closeLightbox();
  }

  function moveScreenshot(offset: number): void {
    setSelectedScreenshot((current: number | null) => current === null
      ? null
      : (current + offset + screenshots.length) % screenshots.length);
  }
  return (
    <section className="storefront-overview" aria-labelledby="storefront-title">
      <header>
        <h2 id="storefront-title">Storefront overview</h2>
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
            <div>
              <dt>Tags</dt>
              <dd>{store.tags ? <ul className="tag-list" aria-label="Tags">{store.tags.map((tag) => <li key={tag}>{tag}</li>)}</ul> : unknown}</dd>
            </div>
            <div><dt>Regional price</dt><dd>{store.price ? `${store.price.final_formatted} · ${store.price.currency} · ${store.price.country_code}` : unknown}</dd></div>
            <div><dt>Platforms</dt><dd>{store.platforms?.join(", ") ?? unknown}</dd></div>
            <div>
              <dt>Languages</dt>
              <dd>{languages ? (
                <div className="language-groups">
                  {languages.fullAudio.length > 0 && <LanguageList label="Full audio" languages={languages.fullAudio} />}
                  {languages.interfaceAndSubtitles.length > 0 && (
                    <LanguageList label="Interface and subtitles" languages={languages.interfaceAndSubtitles} />
                  )}
                </div>
              ) : unknown}</dd>
            </div>
          </dl>
        </section>
        <section>
          <h3>Features</h3>
          {store.features ? (
            <ul className="feature-list" aria-label="Features">{store.features.map((feature) => (
              <li key={`${feature.group}-${feature.name}`}>
                <span>{feature.name}</span>
                <strong className={`feature-state feature-state-${feature.state}`}>{featureState(feature.state)}</strong>
              </li>
            ))}</ul>
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
            {screenshots.map((url: string, index: number) => (
              <button
                className="screenshot-thumbnail"
                key={url}
                type="button"
                aria-label={`Enlarge ${metadata.title} Steam screenshot ${index + 1}`}
                onClick={() => setSelectedScreenshot(index)}
              >
                <img src={url} alt={`${metadata.title} Steam screenshot ${index + 1}`} />
              </button>
            ))}
            {store.trailers?.map((trailer) => (
              <a key={trailer.video_url} href={trailer.video_url} target="_blank" rel="noreferrer">
                <img src={trailer.thumbnail_url} alt="" />
                Play {trailer.name} on Steam
              </a>
            ))}
          </div>
        </section>
      )}
      {selectedScreenshot !== null && (
        <dialog
          className="screenshot-lightbox"
          ref={lightboxRef}
          aria-label={`${metadata.title} screenshot ${selectedScreenshot + 1} of ${screenshots.length}`}
          onCancel={() => setSelectedScreenshot(null)}
          onClick={closeFromBackdrop}
        >
          <div>
            <button type="button" className="lightbox-close" aria-label="Close screenshot" onClick={closeLightbox}>×</button>
            <img src={screenshots[selectedScreenshot]} alt={`${metadata.title} Steam screenshot ${selectedScreenshot + 1}`} />
            {screenshots.length > 1 && (
              <nav aria-label="Screenshot navigation">
                <button type="button" aria-label="Previous screenshot" onClick={() => moveScreenshot(-1)}>←</button>
                <span>{selectedScreenshot + 1} / {screenshots.length}</span>
                <button type="button" aria-label="Next screenshot" onClick={() => moveScreenshot(1)}>→</button>
              </nav>
            )}
            <a href={screenshots[selectedScreenshot]} target="_blank" rel="noreferrer">Open original</a>
          </div>
        </dialog>
      )}
    </section>
  );
}

interface LanguageGroups {
  fullAudio: string[];
  interfaceAndSubtitles: string[];
}

interface LanguageListProps {
  label: string;
  languages: string[];
}

function LanguageList({ label, languages }: LanguageListProps): JSX.Element {
  return (
    <div>
      <strong>{label}</strong>
      <ul className="language-list" aria-label={label}>
        {languages.map((language: string) => <li key={language}>{language}</li>)}
      </ul>
    </div>
  );
}

function groupLanguages(value: string | null): LanguageGroups | null {
  if (!value) return null;
  const entries: string[] = value
    .replace(/\s*languages with full audio support\s*$/i, "")
    .split(",")
    .map((entry: string) => entry.trim())
    .filter(Boolean);
  if (entries.length === 0) return null;

  const normalize = (entry: string): string => entry
    .replace(/\*/g, "")
    .trim()
    .replace(/\s+-\s+(.+)$/, " ($1)");
  return {
    fullAudio: entries.filter((entry: string) => entry.includes("*")).map(normalize),
    interfaceAndSubtitles: entries.filter((entry: string) => !entry.includes("*")).map(normalize),
  };
}

function featureState(state: string): string {
  return state === "supported" ? "Supported"
    : state === "partial" ? "Partial"
      : state === "not_supported" ? "Not supported"
        : "Unknown / unavailable";
}
