import typer

app = typer.Typer(help="Coding Swarm CLI")

@app.command()
def version():
    """Print version."""
    import importlib.metadata as md
    v = md.version("coding-swarm-cli")
    typer.echo(f"Coding Swarm CLI {v}")

# Add more subcommands under app as needed.
