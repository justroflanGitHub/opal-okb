"""Точка входа ``py -m commands``: роутинг subcommand → CLI / REPL / MCP."""
import sys


def main() -> int:
    argv = sys.argv[1:]
    if argv and argv[0] == "repl":
        from commands.jsonrepl import main as repl_main
        return repl_main()
    if argv and argv[0] == "mcp":
        from commands.mcp import main as mcp_main
        return mcp_main()
    from commands.cli import main as cli_main
    return cli_main(argv)


if __name__ == "__main__":
    sys.exit(main())
