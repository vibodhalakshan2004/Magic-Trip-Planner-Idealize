export const runtime = "nodejs";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const MAX_REDIRECTS = 3;
const ALLOWED_HOSTS = new Set([
  "upload.wikimedia.org",
  "maps.googleapis.com",
  "lh3.googleusercontent.com",
]);

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const rawUrl = searchParams.get("url");

  if (!rawUrl) {
    return placeholder("Image unavailable");
  }

  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    return placeholder("Image unavailable");
  }

  if (!isAllowedImageUrl(url)) {
    return placeholder("Image unavailable");
  }

  try {
    const upstream = await fetchImage(url);

    if (!upstream?.ok || !upstream.body) {
      return placeholder("Image unavailable");
    }

    const contentType = upstream.headers.get("content-type") ?? "image/jpeg";
    if (!contentType.startsWith("image/")) {
      return placeholder("Image unavailable");
    }

    const declaredLength = Number(upstream.headers.get("content-length") ?? 0);
    if (declaredLength > MAX_IMAGE_BYTES) {
      return placeholder("Image unavailable");
    }

    const image = await readWithLimit(upstream.body, MAX_IMAGE_BYTES);
    if (!image) {
      return placeholder("Image unavailable");
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
    return placeholder("Image unavailable");
  }
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
