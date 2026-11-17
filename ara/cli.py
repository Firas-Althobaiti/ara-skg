import typer

from ara import get_logger

app = typer.Typer(help="ARA‑SKG command line interface")


@app.command()
def demo():
    """Run a short end‑to‑end demonstration using mock data."""
    logger = get_logger()
    logger.info("Starting demo")
    # In a real implementation this would invoke the full pipeline.
    print("Demo completed successfully.")
    logger.info("Demo finished")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
