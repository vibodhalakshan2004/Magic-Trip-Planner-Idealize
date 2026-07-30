export const runtime = "nodejs";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const MAX_REDIRECTS = 3;
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
  const label = searchParams.get("label")?.trim() || "Image unavailable";

  let url: URL | null = null;

  if (rawUrl) {
    try {
      url = new URL(rawUrl);
    } catch {
      return placeholder(label);
    }
  } else if (query) {
    url = await findWikimediaImage(query);
  } else {
    return placeholder(label);
  }

  if (!url || !isAllowedImageUrl(url)) {
    return placeholder(label);
  }

  try {
    const upstream = await fetchImage(url);

    if (!upstream?.ok || !upstream.body) {
      return placeholder(label);
    }

    const contentType = upstream.headers.get("content-type") ?? "image/jpeg";
    if (!contentType.startsWith("image/")) {
      return placeholder(label);
    }

    const declaredLength = Number(upstream.headers.get("content-length") ?? 0);
    if (declaredLength > MAX_IMAGE_BYTES) {
      return placeholder(label);
    }

    const image = await readWithLimit(upstream.body, MAX_IMAGE_BYTES);
    if (!image) {
      return placeholder(label);
    }

    return new Response(image, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=43200",
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "X-Content-Type-Options": "nosniff",
      },
    });
  } catch {
    return placeholder(label);
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
      next: { revalidate: 60 * 60 * 12 },
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
      "Cache-Control": "public, max-age=3600",
      "Content-Security-Policy": "default-src 'none'; sandbox",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

function escapeXml(value: string) {
  return value.replace(/[<>&'"]/g, (char) => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", "'": "&apos;", "\"": "&quot;" })[char] ?? char);
}
