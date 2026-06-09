from glycomass.logging_config import configure_logging, get_logger


def test_configure_logging_json_and_console_and_get_logger():
    configure_logging(json_output=True, level="INFO")
    get_logger("test").info("hello", k=1)  # must not raise
    configure_logging(json_output=False, level="DEBUG")  # console renderer path
    get_logger().info("again")
