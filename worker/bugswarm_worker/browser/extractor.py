from __future__ import annotations

from typing import Any

EXTRACT_SCRIPT = """
() => {
  const textOf = (element) => (element.innerText || element.textContent || "").trim().slice(0, 300);
  const labelFor = (element) => {
    if (element.labels && element.labels.length > 0) return textOf(element.labels[0]);
    if (element.getAttribute("aria-label")) return element.getAttribute("aria-label");
    if (element.getAttribute("name")) return element.getAttribute("name");
    if (element.getAttribute("id")) {
      const label = document.querySelector(`label[for="${CSS.escape(element.getAttribute("id"))}"]`);
      if (label) return textOf(label);
    }
    return "";
  };
  const selectorFor = (element) => {
    if (element.id) return `#${CSS.escape(element.id)}`;
    const testId = element.getAttribute("data-testid");
    if (testId) return `[data-testid="${CSS.escape(testId)}"]`;
    const name = element.getAttribute("name");
    if (name) return `${element.tagName.toLowerCase()}[name="${CSS.escape(name)}"]`;
    const href = element.getAttribute("href");
    if (href && element.tagName.toLowerCase() === "a") return `a[href="${CSS.escape(href)}"]`;
    return element.tagName.toLowerCase();
  };
  const visible = (element) => {
    const box = element.getBoundingClientRect();
    const style = window.getComputedStyle(element);
    return box.width > 0 && box.height > 0 && style.visibility !== "hidden" && style.display !== "none";
  };
  const enabled = (element) => !element.disabled && element.getAttribute("aria-disabled") !== "true";
  const boxOf = (element) => {
    const box = element.getBoundingClientRect();
    return { x: box.x, y: box.y, width: box.width, height: box.height };
  };
  const mapElement = (element, type) => ({
    element_type: type,
    selector: selectorFor(element),
    role: element.getAttribute("role") || "",
    label: labelFor(element),
    placeholder: element.getAttribute("placeholder") || "",
    text_content: textOf(element),
    href: element.href || element.getAttribute("href") || "",
    is_visible: visible(element),
    is_enabled: enabled(element),
    bounding_box: boxOf(element),
    metadata: {
      tag: element.tagName.toLowerCase(),
      type: element.getAttribute("type") || "",
      name: element.getAttribute("name") || "",
    },
  });

  const links = Array.from(document.querySelectorAll("a[href]")).slice(0, 80).map((el) => mapElement(el, "link"));
  const buttons = Array.from(document.querySelectorAll("button, [role='button'], input[type='button'], input[type='submit']")).slice(0, 80).map((el) => mapElement(el, "button"));
  const inputs = Array.from(document.querySelectorAll("input, textarea, select")).slice(0, 80).map((el) => mapElement(el, "input"));
  const forms = Array.from(document.querySelectorAll("form")).slice(0, 30).map((form) => ({
    ...mapElement(form, "form"),
    metadata: {
      action: form.action || form.getAttribute("action") || "",
      method: form.method || "get",
      field_count: form.querySelectorAll("input, textarea, select").length,
    },
  }));

  return {
    links,
    buttons,
    inputs,
    forms,
    title: document.title,
    visible_text: (document.body?.innerText || "").trim().slice(0, 2000),
    dom_node_count: document.querySelectorAll("*").length,
  };
}
"""


async def extract_page(page) -> dict[str, Any]:
    return await page.evaluate(EXTRACT_SCRIPT)
