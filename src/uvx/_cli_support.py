import configuraptor


class State(configuraptor.TypedConfig, configuraptor.Singleton):
    """Global cli app state."""

    verbose: bool = False
