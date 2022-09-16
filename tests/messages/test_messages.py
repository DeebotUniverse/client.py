from deebot_client.messages import MESSAGES


def test_all_messages_4_abstract_methods() -> None:
    # Verify that all abstract methods are implemented
    for _, message in MESSAGES.items():
        message()
