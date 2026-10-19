import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError
} from "@modelcontextprotocol/sdk/types.js";
import { execFile } from "child_process";
import { promisify } from "util";
import path from "path";
import fs from "fs";
import os from "os";
import { fileURLToPath } from "url";
import { resolveConcatProjectPaths } from "./lib/concat_paths.js";

const execFileAsync = promisify(execFile);
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const episodeSlugPattern = /^[A-Za-z0-9][A-Za-z0-9_-]*$/;

function getEpisodeArgs(args) {
  const { serial, ep } = args ?? {};
  if (
    typeof serial !== "string" ||
    !episodeSlugPattern.test(serial) ||
    typeof ep !== "string" ||
    !episodeSlugPattern.test(ep)
  ) {
    throw new Error("serial and ep must be simple episode slugs");
  }
  return { serial, ep };
}

class CapcutMcpServer {
  constructor() {
    this.server = new Server({
      name: "capcut-pipeline-mcp",
      version: "1.0.0"
    }, {
      capabilities: {
        tools: {}
      }
    });

    this.setupHandlers();
  }

  setupHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "assemble_episode",
            description: "Assemble an episode and generate draft.json",
            inputSchema: {
              type: "object",
              properties: {
                serial: {
                  type: "string",
                  pattern: "^[A-Za-z0-9][A-Za-z0-9_-]*$",
                  description: "Serial slug (e.g., cyber-heist)"
                },
                ep: {
                  type: "string",
                  pattern: "^[A-Za-z0-9][A-Za-z0-9_-]*$",
                  description: "Episode slug (e.g., ep-01-infiltration)"
                }
              },
              required: ["serial", "ep"]
            }
          },
          {
            name: "open_in_concat",
            description: "Open the generated draft.json in Concat.app via CLI (bypasses Finder association issues)",
            inputSchema: {
              type: "object",
              properties: {
                serial: { type: "string", pattern: "^[A-Za-z0-9][A-Za-z0-9_-]*$" },
                ep: { type: "string", pattern: "^[A-Za-z0-9][A-Za-z0-9_-]*$" }
              },
              required: ["serial", "ep"]
            }
          }
        ]
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      if (name === "assemble_episode") {
        try {
          const { serial, ep } = getEpisodeArgs(args);
          const { stdout, stderr } = await execFileAsync("python3", [
            path.join(repoRoot, "scripts", "assemble_episode.py"),
            "--serial",
            serial,
            "--ep",
            ep
          ], { cwd: repoRoot });
          return {
            content: [{ type: "text", text: `Output:\n${stdout}\n${stderr}` }]
          };
        } catch (e) {
          const details = [e.stdout, e.stderr].filter(Boolean).join("\n");
          return {
            content: [{ type: "text", text: `Error: ${e.message}${details ? `\n${details}` : ""}` }],
            isError: true
          };
        }
      }

      if (name === "open_in_concat") {
        try {
          const { serial, ep } = getEpisodeArgs(args);
          const { draftPath, projectDir, concatJsonPath } = resolveConcatProjectPaths(serial, ep, {
            repoRoot,
            home: os.homedir()
          });
          if (!fs.existsSync(draftPath)) {
            return {
              content: [{ type: "text", text: `Error: ${draftPath} not found. Run assemble_episode first.` }],
              isError: true
            };
          }
          if (fs.existsSync(concatJsonPath)) {
            return {
              content: [{
                type: "text",
                text: `Error: ${concatJsonPath} already exists. Refusing to overwrite; remove the existing Concat project first if you want to regenerate.`
              }],
              isError: true
            };
          }
          if (!fs.existsSync(projectDir)) {
            fs.mkdirSync(projectDir, { recursive: true });
          }
          await execFileAsync("python3", [
            path.join(repoRoot, "scripts", "convert_draft.py"),
            draftPath,
            concatJsonPath
          ], { cwd: repoRoot });

          const { stdout, stderr } = await execFileAsync(
            "open",
            ["-a", "Concat.app", concatJsonPath],
            { cwd: repoRoot }
          );
          return {
            content: [{
              type: "text",
              text: `Converted draft to ${concatJsonPath} and opened Concat.app.\n${stdout}\n${stderr}`
            }]
          };
        } catch (e) {
          return {
            content: [{ type: "text", text: `Error: ${e.message}` }],
            isError: true
          };
        }
      }

      throw new McpError(ErrorCode.MethodNotFound, `Tool not found: ${name}`);
    });
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("Capcut MCP server running on stdio");
  }
}

const server = new CapcutMcpServer();
server.run().catch(console.error);
