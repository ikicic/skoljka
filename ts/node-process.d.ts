declare module "node:process" {
  interface ReadableStdin {
    setEncoding(encoding: BufferEncoding): void;
    on(event: "data", listener: (chunk: string) => void): void;
    on(event: "end", listener: () => void): void;
  }

  interface WritableStdout {
    write(chunk: string): void;
  }

  type BufferEncoding = "utf8";

  export const stdin: ReadableStdin;
  export const stdout: WritableStdout;
}
