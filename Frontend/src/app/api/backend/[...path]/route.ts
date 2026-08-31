export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const REQUEST_HEADERS = [
  "accept",
  "authorization",
  "content-type",
  "cookie",
  "idempotency-key",
  "if-none-match",
  "range",
  "x-request-id",
] as const;

const RESPONSE_HEADERS = [
  "cache-control",
  "content-disposition",
  "content-range",
  "content-type",
  "etag",
  "last-modified",
  "retry-after",
  "x-request-id",
  "x-response-time-ms",
] as const;

const REDIRECT_STATUSES = new Set([301, 302, 303, 307, 308]);
const MAX_BACKEND_REDIRECTS = 5;

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

function backendBaseUrl() {
  const configured = process.env.BACKEND_API_URL?.trim();
  const rawUrl = configured || (process.env.NODE_ENV === "development" ? "http://127.0.0.1:8000" : "");
  if (!rawUrl) return null;

  try {
    const url = new URL(rawUrl);
    if (!new Set(["http:", "https:"]).has(url.protocol) || url.username || url.password) return null;
    url.search = "";
    url.hash = "";
    return url;
  } catch {
    return null;
  }
}

function targetUrl(baseUrl: URL, path: string[], requestUrl: string) {
  const target = new URL(baseUrl);
  const incoming = new URL(requestUrl);
  const basePath = target.pathname.replace(/\/$/, "");
  const encodedPath = path.map(encodeURIComponent).join("/");
  target.pathname = `${basePath}/${encodedPath}`;
  if (incoming.pathname.endsWith("/") && !target.pathname.endsWith("/")) target.pathname += "/";
  target.search = incoming.search;
  return target;
}

async function fetchBackend(
  request: Request,
  baseUrl: URL,
  initialTarget: URL,
  headers: Headers,
  body: ArrayBuffer | undefined,
) {
  let target = initialTarget;
  let method = request.method.toUpperCase();
  let requestBody = body;
  let forwardedHeaders = new Headers(headers);

  for (let redirectCount = 0; redirectCount <= MAX_BACKEND_REDIRECTS; redirectCount += 1) {
    const upstream = await fetch(target, {
      method,
      headers: forwardedHeaders,
      body: requestBody?.slice(0),
      cache: "no-store",
      redirect: "manual",
      signal: request.signal,
    });

    const location = upstream.headers.get("location");
    if (!REDIRECT_STATUSES.has(upstream.status) || !location) return upstream;
    if (redirectCount === MAX_BACKEND_REDIRECTS) throw new Error("The backend returned too many redirects.");

    const redirectedTarget = new URL(location, target);
    if (redirectedTarget.origin !== baseUrl.origin) throw new Error("The backend attempted an external redirect.");
    if (upstream.body) await upstream.body.cancel();

    if (upstream.status === 303 || ((upstream.status === 301 || upstream.status === 302) && method === "POST")) {
      method = "GET";
      requestBody = undefined;
      forwardedHeaders = new Headers(forwardedHeaders);
      forwardedHeaders.delete("content-type");
    }
    target = redirectedTarget;
  }

  throw new Error("The backend redirect could not be resolved.");
}

async function proxy(request: Request, context: RouteContext) {
  const baseUrl = backendBaseUrl();
  if (!baseUrl) {
    return Response.json(
      { detail: "The backend service is not configured. Set BACKEND_API_URL on the frontend deployment." },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }

  const { path } = await context.params;
  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  const forwardedFor = request.headers.get("x-forwarded-for");
  if (forwardedFor) headers.set("x-forwarded-for", forwardedFor);

  const method = request.method.toUpperCase();
  const body = method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer();

  try {
    const upstream = await fetchBackend(request, baseUrl, targetUrl(baseUrl, path, request.url), headers, body);

    const responseHeaders = new Headers();
    for (const name of RESPONSE_HEADERS) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    if (!responseHeaders.has("cache-control")) responseHeaders.set("cache-control", "no-store");

    const upstreamHeaders = upstream.headers as Headers & { getSetCookie?: () => string[] };
    const setCookies = upstreamHeaders.getSetCookie?.() ?? [];
    for (const cookie of setCookies) responseHeaders.append("set-cookie", cookie);
    if (setCookies.length === 0) {
      const cookie = upstream.headers.get("set-cookie");
      if (cookie) responseHeaders.append("set-cookie", cookie);
    }

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch {
    return Response.json(
      { detail: "The backend service is temporarily unavailable." },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }
}

export const GET = proxy;
export const HEAD = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
