// Copyright (c) 2026 Helpmefindthejob contributors
// SPDX-License-Identifier: Apache-2.0
//
// /api/docs renderer — fetches /api/openapi.json and lays it out as
// a navigable HTML reference. Same-origin only, no third-party CDN,
// no Swagger UI / Redoc bundle. ~150 lines vs ~500 KB of vendored
// JS. CSP-compliant: external <script src> only.
//
// All DOM building goes through textContent / setAttribute — never
// innerHTML — so spec content can never inject HTML even if the
// spec itself is somehow malformed.

"use strict";

const ROOT = document.getElementById("apiSpecBody");
const LOADING = document.getElementById("apiSpecLoading");
const ERROR_EL = document.getElementById("apiSpecError");
const JUMP_NAV = document.getElementById("apiTagJumpNav");

function tag(name, props = {}, ...children) {
  const el = document.createElement(name);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") el.className = v;
    else el.setAttribute(k, v);
  }
  for (const c of children) {
    if (c == null) continue;
    if (typeof c === "string") el.appendChild(document.createTextNode(c));
    else el.appendChild(c);
  }
  return el;
}

function methodBadge(method) {
  const colors = {
    get: "method-get", post: "method-post", put: "method-put",
    patch: "method-patch", delete: "method-delete",
    head: "method-head", options: "method-options",
  };
  return tag("span", { class: `method-badge ${colors[method] || ""}` }, method.toUpperCase());
}

function renderResponses(responses) {
  if (!responses || Object.keys(responses).length === 0) return null;
  const ul = tag("ul", { class: "api-responses" });
  for (const [code, body] of Object.entries(responses)) {
    ul.appendChild(
      tag("li", {},
        tag("code", { class: `api-response-code api-response-${code[0]}xx` }, code),
        " — ",
        body.description || ""
      )
    );
  }
  return ul;
}

function renderExample(content) {
  if (!content) return null;
  const json = content["application/json"];
  if (!json || !json.example) return null;
  return tag("pre", { class: "api-example" },
    tag("code", {}, JSON.stringify(json.example, null, 2)));
}

function renderRequestBody(rb) {
  if (!rb) return null;
  const wrap = tag("div", { class: "api-request-body" });
  wrap.appendChild(tag("p", { class: "muted small" },
    rb.required ? "Request body (required):" : "Request body (optional):"));
  const example = renderExample(rb.content);
  if (example) wrap.appendChild(example);
  return wrap;
}

function renderParameters(params) {
  if (!params || params.length === 0) return null;
  const wrap = tag("div", { class: "api-parameters" });
  wrap.appendChild(tag("p", { class: "muted small" }, "Query parameters:"));
  const ul = tag("ul");
  for (const p of params) {
    ul.appendChild(
      tag("li", {},
        tag("code", {}, p.name),
        " — ",
        p.description || ""
      )
    );
  }
  wrap.appendChild(ul);
  return wrap;
}

function renderOperation(path, method, op) {
  const card = tag("article", { class: "api-operation" });
  const header = tag("header", { class: "api-operation-header" },
    methodBadge(method),
    tag("code", { class: "api-path" }, path),
  );
  card.appendChild(header);
  if (op.summary) card.appendChild(tag("h4", { class: "api-operation-summary" }, op.summary));
  if (op.description) card.appendChild(tag("p", {}, op.description));
  const params = renderParameters(op.parameters);
  if (params) card.appendChild(params);
  const rb = renderRequestBody(op.requestBody);
  if (rb) card.appendChild(rb);
  const responses = renderResponses(op.responses);
  if (responses) card.appendChild(responses);
  return card;
}

function groupByTag(paths) {
  const groups = new Map();
  for (const [path, methods] of Object.entries(paths)) {
    for (const [method, op] of Object.entries(methods)) {
      if (!["get", "post", "put", "patch", "delete", "head", "options"].includes(method)) continue;
      const tagName = (op.tags && op.tags[0]) || "other";
      if (!groups.has(tagName)) groups.set(tagName, []);
      groups.get(tagName).push({ path, method, op });
    }
  }
  return groups;
}

function renderSkeleton() {
  // UX-D1 (2026-05-23): proper loading skeleton instead of plain
  // "Loading…" text. Three shimmering placeholder cards.
  if (!LOADING) return;
  LOADING.replaceChildren();
  LOADING.className = "api-loading-skeleton";
  LOADING.hidden = false;
  for (let i = 0; i < 3; i += 1) {
    const card = tag("div", { class: "api-skeleton-card" });
    card.appendChild(tag("div", { class: "api-skeleton-line api-skeleton-line-head" }));
    card.appendChild(tag("div", { class: "api-skeleton-line api-skeleton-line-body" }));
    card.appendChild(tag("div", { class: "api-skeleton-line api-skeleton-line-body short" }));
    LOADING.appendChild(card);
  }
}

function showRetry(error) {
  // UX-D2: render a Retry button on fetch failure.
  if (!ERROR_EL) return;
  ERROR_EL.replaceChildren();
  ERROR_EL.hidden = false;
  if (LOADING) LOADING.hidden = true;
  const msg = tag("span", {}, "Couldn't load the spec");
  if (error && error.message) {
    msg.appendChild(document.createTextNode(` (${error.message})`));
  }
  msg.appendChild(document.createTextNode(". "));
  ERROR_EL.appendChild(msg);
  const retry = tag("button", {
    class: "btn btn-ghost",
    type: "button",
    "aria-label": "Retry loading the API spec",
  }, "Retry");
  retry.addEventListener("click", () => {
    ERROR_EL.hidden = true;
    render();
  });
  ERROR_EL.appendChild(retry);
  const fallback = tag("p", { class: "muted small" });
  fallback.appendChild(document.createTextNode("The raw JSON is still available at "));
  fallback.appendChild(tag("a", { href: "/api/openapi.json" }, "/api/openapi.json"));
  fallback.appendChild(document.createTextNode("."));
  ERROR_EL.appendChild(fallback);
}

async function render() {
  renderSkeleton();
  try {
    const resp = await fetch("/api/openapi.json", { cache: "no-store" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const spec = await resp.json();

    LOADING.hidden = true;
    ROOT.hidden = false;
    ROOT.replaceChildren();

    const grouped = groupByTag(spec.paths || {});
    const tagDescriptions = new Map();
    for (const t of (spec.tags || [])) tagDescriptions.set(t.name, t.description);

    // UX-E2: populate the jump-nav with one link per tag group.
    if (JUMP_NAV) {
      JUMP_NAV.replaceChildren();
      const label = document.createElement("span");
      label.className = "api-tag-jump-label";
      label.textContent = "Jump to:";
      JUMP_NAV.appendChild(label);
      for (const tagName of grouped.keys()) {
        const tagId = `tag-${tagName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
        const a = document.createElement("a");
        a.href = `#${tagId}`;
        a.className = "api-tag-jump-link";
        a.textContent = tagName;
        JUMP_NAV.appendChild(a);
      }
      JUMP_NAV.hidden = false;
    }

    for (const [tagName, ops] of grouped) {
      // UX-K3: stable anchor id per tag group so external docs can
      // deep-link to a specific section (e.g. /api/docs#tag-auth).
      const tagId = `tag-${tagName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
      const section = tag("section", { class: "api-tag-section", id: tagId });
      const heading = tag("h3", { class: "api-tag-heading" });
      const anchor = tag("a", {
        class: "api-tag-anchor",
        href: `#${tagId}`,
        "aria-label": `Permalink to ${tagName}`,
      }, "#");
      heading.appendChild(anchor);
      heading.appendChild(document.createTextNode(" " + tagName));
      section.appendChild(heading);
      const desc = tagDescriptions.get(tagName);
      if (desc) section.appendChild(tag("p", { class: "muted" }, desc));
      for (const { path, method, op } of ops) {
        section.appendChild(renderOperation(path, method, op));
      }
      ROOT.appendChild(section);
    }
  } catch (err) {
    showRetry(err);
  }
}

render();
