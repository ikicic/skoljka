import { stdin, stdout } from "node:process";
import { renderMarkdown } from "../shared/markdown-render";

let input = "";
stdin.setEncoding("utf8");
stdin.on("data", (chunk) => {
  input += chunk;
});
stdin.on("end", () => {
  const payload = JSON.parse(input || "{}");
  const result = renderMarkdown(payload.source || "", {
    attachmentUrls: payload.attachmentUrls || {},
  });
  stdout.write(JSON.stringify(result));
});
