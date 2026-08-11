import { describe, expect, it } from "vitest";
import html from "../../public/review-labeler.html?raw";

describe("human gold-label review tool", () => {
  it("loads candidates, accepts button corrections, and completes a review round", () => {
    loadLabeler(document);

    button(document, "Try demo").click();
    expect(document.querySelector("[data-review-text]")?.textContent).toContain(
      "The dash feels immediate",
    );
    expect(document.querySelector("[data-progress]")?.textContent).toBe("0 of 3 reviewed");

    button(document, "Negative").click();
    button(document, "Approve & next").click();

    expect(document.querySelector("[data-progress]")?.textContent).toBe("1 of 3 reviewed");
    expect(button(document, "Export reviewed JSON").disabled).toBe(true);

    button(document, "Approve & next").click();
    expect((document.querySelector("[data-technical]") as HTMLInputElement).checked).toBe(true);
    button(document, "Approve & next").click();

    expect(document.querySelector("[data-progress]")?.textContent).toBe("3 of 3 reviewed");
    expect(button(document, "Export reviewed JSON").disabled).toBe(false);
  });

  it("runs button-only quality judgment rounds", () => {
    loadLabeler(document);

    button(document, "Try quality demo").click();

    expect(document.querySelector("[data-question]")?.textContent).toBe(
      "Did the candidates capture every opinion?",
    );
    button(document, "Complete").click();
    expect(document.querySelector("[data-progress]")?.textContent).toBe("1 of 2 reviewed");
    expect(button(document, "Same Theme")).toBeEnabled();
    button(document, "Same Theme").click();

    expect(button(document, "Export reviewed JSON")).toBeEnabled();
  });
});

function loadLabeler(document: Document): void {
  const script = html.match(/<script>([\s\S]*)<\/script>/)?.[1];
  if (!script) throw new Error("Review labeler script not found");
  document.open();
  document.write(html.replace(/<script>[\s\S]*<\/script>/, ""));
  document.close();
  Function(script)();
}

function button(document: Document, name: string): HTMLButtonElement {
  const match = [...document.querySelectorAll("button")].find(
    (candidate) => candidate.textContent?.trim() === name,
  );
  if (!(match instanceof document.defaultView!.HTMLButtonElement)) {
    throw new Error(`Button not found: ${name}`);
  }
  return match;
}
