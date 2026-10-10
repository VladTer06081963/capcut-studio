import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ErrorCode,
  McpError
} from "@modelcontextprotocol/sdk/types.js";
import { exec } from "child_process";
import { promisify } from "util";
import path from "path";
import fs from "fs";

const execAsync = promisify(exec);

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
                serial: { type: "string", description: "Serial slug (e.g., cyber-heist)" },
                ep: { type: "string", description: "Episode slug (e.g., ep-01-infiltration)" }
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
                serial: { type: "string" },
                ep: { type: "string" }
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
          const { stdout, stderr } = await execAsync(`python3 scripts/assemble_episode.py --serial ${args.serial} --ep ${args.ep}`, { cwd: path.resolve(process.cwd(), "..") });
          return {
            content: [{ type: "text", text: `Output:\n${stdout}\n${stderr}` }]
          };
        } catch (e) {
          return {
            content: [{ type: "text", text: `Error: ${e.message}\n${e.stdout}\n${e.stderr}` }],
            isError: true
          };
        }
      }

      if (name === "open_in_concat") {
        try {
          const draftPath = path.resolve(process.cwd(), "..", "serials", args.serial, args.ep, "rendered", "draft.json");
          if (!fs.existsSync(draftPath)) {
            return {
              content: [{ type: "text", text: `Error: ${draftPath} not found. Run assemble_episode first.` }],
              isError: true
            };
          }
          const projectName = `${args.serial}-${args.ep}`;
          const concatWorkspace = path.join(process.env.HOME, "Desktop", "Concat");
          const projectDir = path.join(concatWorkspace, projectName);
          const concatJsonPath = path.join(projectDir, "concat.json");

          if (!fs.existsSync(projectDir)) {
            fs.mkdirSync(projectDir, { recursive: true });
          }
          await execAsync(`python3 scripts/convert_draft.py "${draftPath}" "${concatJsonPath}"`, { cwd: path.resolve(process.cwd(), "..") });

          const { stdout, stderr } = await execAsync(`open -a Concat.app`);
          return {
            content: [{ type: "text", text: `Converted draft to ${concatJsonPath} and opened Concat.app.\n${stdout}\n${stderr}` }]
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
