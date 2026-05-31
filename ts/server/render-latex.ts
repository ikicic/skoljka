import { stdin, stdout } from "node:process";
import { renderLatex } from "../shared/markdown-render";

let input = "";
stdin.setEncoding("utf8");
stdin.on("data", (chunk) => {
  input += chunk;
});
stdin.on("end", () => {
  const payload = JSON.parse(input || "{}");
  const result = renderLatex(payload.source || "", {
    attachmentPaths: payload.attachmentPaths || {},
  });
  stdout.write(JSON.stringify(result));
});
