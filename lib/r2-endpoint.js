// One normalised R2 endpoint for every S3 client in the app.
//
// This exists because a bad R2_ENDPOINT fails as an SSL handshake error —
// "ssl3_read_bytes: tls alert handshake failure, SSL alert number 40" — which
// says nothing about the actual mistake. The SDK addresses buckets virtual-host
// style, so it connects to <bucket>.<endpoint-host>; if the host is wrong, or
// has one label too many, Cloudflare's certificate doesn't cover the name and
// the server drops the connection before any request is sent.
//
// The correct value is the S3 API endpoint:
//     https://<ACCOUNT_ID>.r2.cloudflarestorage.com
// found in Cloudflare → R2 → Overview → S3 API, and stored as `endpoint` in the
// rclone remote.
//
// It is NOT the public bucket URL (https://pub-<hash>.r2.dev). That one serves
// public reads over HTTP and is the easiest thing to paste by mistake, since it
// is the URL that appears in the app's own audio links.

export function r2Endpoint() {
  let raw = (process.env.R2_ENDPOINT || "").trim();
  if (!raw) throw new Error("R2_ENDPOINT is not set");

  // Strip anything that survives a copy-paste: quotes, trailing slashes.
  raw = raw.replace(/^["']|["']$/g, "").replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(raw)) raw = "https://" + raw;

  let url;
  try {
    url = new URL(raw);
  } catch (e) {
    throw new Error("R2_ENDPOINT is not a valid URL: " + raw);
  }

  if (/\.r2\.dev$/i.test(url.hostname)) {
    throw new Error(
      "R2_ENDPOINT is the public bucket URL (" + url.hostname + "). " +
      "The S3 API needs https://<ACCOUNT_ID>.r2.cloudflarestorage.com instead — " +
      "Cloudflare → R2 → Overview → S3 API."
    );
  }

  // A path means the bucket was included. The SDK adds the bucket itself, so
  // leaving it here produces a hostname with an extra label and the handshake
  // fails.
  if (url.pathname && url.pathname !== "/") {
    throw new Error(
      "R2_ENDPOINT should have no path — drop the \"" + url.pathname +
      "\" part, the bucket name is supplied separately."
    );
  }

  return url.origin;
}
