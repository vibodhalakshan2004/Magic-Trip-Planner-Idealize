export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const MAX_REDIRECTS = 3;
// Wikimedia currently serves a fixed set of thumbnail buckets. 1280px is
// accepted broadly; arbitrary widths such as 1600px return HTTP 400.
const WIKIMEDIA_IMAGE_WIDTH = 1280;
const WIKIMEDIA_SEARCH_URL = "https://commons.wikimedia.org/w/api.php";
const ALLOWED_HOSTS = new Set([
  "upload.wikimedia.org",
  "maps.googleapis.com",
  "lh3.googleusercontent.com",
]);

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const rawUrl = searchParams.get("url");
  const query = searchParams.get("query")?.trim();
  const fallbackQuery = searchParams.get("fallbackQuery")?.trim();
  const label = searchParams.get("label")?.trim() || "Image unavailable";

  let url: URL | null = null;

  if (rawUrl) {
    try {
      url = new URL(rawUrl);
    } catch {
      return placeholder(label);
    }
  } else if (query) {
    url = null;
  } else {
    return placeholder(label);
  }

  if (url && !isAllowedImageUrl(url)) {
    return placeholder(label);
  }

  // Always try a saved source first. This avoids an extra API lookup for the
  // normal case and lets old 3840px Wikimedia URLs use the optimized variant.
  if (url) {
    for (const candidate of uniqueUrls([optimizeWikimediaUrl(url), url])) {
      const response = await proxyImage(candidate);
      if (response) return response;
    }
  }

  // Missing, expired, or unavailable sources use a layered Commons resolver:
  // exact place name first, then a Sri Lanka-specific representative theme.
  for (const lookupQuery of uniqueStrings([query, label, fallbackQuery])) {
    const lookupUrl = await findWikimediaImage(lookupQuery);
    if (!lookupUrl) continue;

    for (const candidate of uniqueUrls([optimizeWikimediaUrl(lookupUrl), lookupUrl])) {
      const response = await proxyImage(candidate);
      if (response) return response;
    }
  }

  return placeholder(label);
}

async function proxyImage(url: URL) {
  try {
    const upstream = await fetchImage(url);
    if (!upstream?.ok || !upstream.body) return null;

    const contentType = upstream.headers.get("content-type") ?? "image/jpeg";
    if (!contentType.startsWith("image/")) return null;

    const declaredLength = Number(upstream.headers.get("content-length") ?? 0);
    if (declaredLength > MAX_IMAGE_BYTES) return null;

    const image = await readWithLimit(upstream.body, MAX_IMAGE_BYTES);
    if (!image) return null;

    return new Response(image, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=43200, stale-while-revalidate=86400",
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return null;
  }
}

async function findWikimediaImage(query: string) {
  try {
    const params = new URLSearchParams({
      action: "query",
      format: "json",
      origin: "*",
      generator: "search",
      gsrsearch: query,
      gsrnamespace: "6",
      gsrlimit: "3",
      prop: "imageinfo",
      iiprop: "url|mime",
      iiurlwidth: "1200",
    });
    const response = await fetch(`${WIKIMEDIA_SEARCH_URL}?${params}`, {
      headers: { "User-Agent": "MagicTripPlanner/1.0 image lookup" },
      signal: AbortSignal.timeout(5_000),
      next: { revalidate: 60 * 60 * 12 },
    });

    if (!response.ok) return null;

    const payload = await response.json() as {
      query?: { pages?: Record<string, { title?: string; imageinfo?: Array<{ mime?: string; thumburl?: string; url?: string }> }> };
    };
    const pages = Object.values(payload.query?.pages ?? {});

    for (const page of pages) {
      if (!isRelevantResult(query, page.title ?? "")) continue;
      const info = page.imageinfo?.[0];
      if (!info?.mime?.startsWith("image/")) continue;
      const source = info.thumburl || info.url;
      if (!source) continue;
      const imageUrl = new URL(source);
      if (isAllowedImageUrl(imageUrl)) return imageUrl;
    }
  } catch {
    return null;
  }

  return null;
}

function isRelevantResult(query: string, title: string) {
  const stopWords = new Set(["file", "hotel", "resort", "guest", "house", "accommodation", "sri", "lanka", "jpg", "jpeg", "png", "webp"]);
  const tokens = (value: string) => new Set(
    value.toLowerCase().match(/[a-z0-9]+/g)?.filter((token) => token.length > 2 && !stopWords.has(token)) ?? [],
  );
  const queryTokens = tokens(query);
  const titleTokens = tokens(title);
  return queryTokens.size > 0 && [...queryTokens].some((token) => titleTokens.has(token));
}

function isAllowedImageUrl(url: URL) {
  const hostname = url.hostname.toLowerCase();
  return (
    url.protocol === "https:" &&
    !url.username &&
    !url.password &&
    !url.port &&
    (ALLOWED_HOSTS.has(hostname) ||
      hostname.endsWith(".wikimedia.org") ||
      hostname.endsWith(".wikipedia.org"))
  );
}

function optimizeWikimediaUrl(url: URL) {
  if (url.hostname.toLowerCase() !== "upload.wikimedia.org") return url;

  const optimized = new URL(url);
  const match = optimized.pathname.match(/\/(\d+)px-([^/]+)$/i);
  if (!match || Number(match[1]) <= WIKIMEDIA_IMAGE_WIDTH) return optimized;

  optimized.pathname = optimized.pathname.replace(
    /\/\d+px-([^/]+)$/i,
    `/${WIKIMEDIA_IMAGE_WIDTH}px-$1`,
  );
  return optimized;
}

function uniqueUrls(urls: URL[]) {
  const seen = new Set<string>();
  return urls.filter((url) => {
    const key = url.toString();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function uniqueStrings(values: Array<string | null | undefined>) {
  const seen = new Set<string>();
  return values.flatMap((value) => {
    const cleaned = value?.trim();
    if (!cleaned) return [];
    const key = cleaned.toLowerCase();
    if (seen.has(key)) return [];
    seen.add(key);
    return [cleaned];
  });
}

async function fetchImage(initialUrl: URL) {
  let url = initialUrl;

  for (let redirects = 0; redirects <= MAX_REDIRECTS; redirects += 1) {
    const response = await fetch(url, {
      headers: {
        "User-Agent": "MagicTripPlanner/1.0 image proxy",
        Accept: "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
      },
      redirect: "manual",
      signal: AbortSignal.timeout(10_000),
      // Keep image bodies out of Next's incremental fetch cache. Large
      // Wikimedia originals can exceed that cache's per-entry limit even
      // though they are safely below this proxy's own 10 MB limit.
      cache: "no-store",
    });

    if (![301, 302, 303, 307, 308].includes(response.status)) {
      return response;
    }

    const location = response.headers.get("location");
    if (!location || redirects === MAX_REDIRECTS) return null;

    url = new URL(location, url);
    if (!isAllowedImageUrl(url)) return null;
  }

  return null;
}

async function readWithLimit(stream: ReadableStream<Uint8Array>, limit: number) {
  const reader = stream.getReader();
  const chunks: Uint8Array[] = [];
  let length = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    length += value.byteLength;
    if (length > limit) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }

  const image = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) {
    image.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return image;
}

function placeholder(label: string) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 520"><rect width="800" height="520" fill="#0f766e"/><path d="M120 360C220 240 300 310 390 210s190-60 290 80v160H120z" fill="#f8fafc" opacity=".24"/><circle cx="610" cy="120" r="46" fill="#f8fafc" opacity=".32"/><text x="56" y="88" fill="#f8fafc" font-family="Arial" font-size="42" font-weight="700">${escapeXml(label)}</text></svg>`;
  return new Response(svg, {
    headers: {
      "Content-Type": "image/svg+xml",
      // A placeholder can be caused by a transient upstream timeout. Never
      // cache it, otherwise the browser keeps showing the fallback even after
      // the real image becomes available.
      "Cache-Control": "no-store",
      "Content-Security-Policy": "default-src 'none'; sandbox",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

function escapeXml(value: string) {
  return value.replace(/[<>&'"]/g, (char) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", "'": "&apos;", "\"": "&quot;" })[char] ?? char);
}
